import ipaddress
import json
import logging
import os
import re
import socket
from email import policy
from email.parser import BytesParser
from io import BytesIO
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import PyPDF2
import google.generativeai as genai
from docx import Document
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from google.api_core import exceptions as google_exceptions

# Configure logging
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

__version__ = "1.0.0"

# Initialize Flask app
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5 MB upload limit to prevent abuse
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", os.urandom(32).hex())

# Initialize rate limiter
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

# Load environment variables from .env if present
load_dotenv()


def _validate_environment() -> None:
    """Validate required environment variables."""
    required_vars = ["GOOGLE_API_KEY"]
    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        raise RuntimeError(
            f"Missing required environment variables: {', '.join(missing)}. "
            "Please set them in your .env file or environment."
        )


# Validate environment variables
_validate_environment()

# Set up the Google API Key from environment
google_api_key = os.getenv("GOOGLE_API_KEY")
if not google_api_key:
    raise RuntimeError("GOOGLE_API_KEY environment variable is not set.")
genai.configure(api_key=google_api_key)

TEMPLATE_NAME = "index.html"
ALLOWED_EXTENSIONS = {"pdf", "txt", "docx", "eml"}
MAX_TEXT_LENGTH = 50000  # Maximum characters for text analysis
MAX_URL_LENGTH = 2048  # Maximum URL length
API_TIMEOUT_SECONDS = 30  # Timeout for Gemini API calls

MODEL_INIT_ERROR = ""

# Private IP ranges for SSRF protection
PRIVATE_IP_RANGES = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
]


def _resolve_model() -> genai.GenerativeModel:
    """Select the best available Gemini model, trying fallbacks if necessary."""
    preferred_model = os.getenv("GEMINI_MODEL")

    # Prefer current models first. Older 2.0 Flash IDs are often blocked for new API keys (404).
    candidate_models = [
        preferred_model,
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
        "gemini-2.5-pro",
        "gemini-1.5-flash",
        "gemini-1.5-flash-8b",
        "gemini-1.5-flash-latest",
        "gemini-1.5-flash-001",
        "gemini-1.5-pro",
        "gemini-1.5-pro-latest",
        "gemini-1.0-pro",
        "gemini-pro",
        # Legacy — may return 404 for new users; try only if nothing above works
        "gemini-2.0-flash-exp",
        "gemini-2.0-flash",
        "gemini-2.0-flash-001",
        "gemini-2.0-flash-lite-latest",
    ]
    errors: list[str] = []

    for candidate in filter(None, candidate_models):
        try:
            logger.info("Attempting to initialize Gemini model '%s'", candidate)
            candidate_model = genai.GenerativeModel(candidate)
            # Lightweight readiness check so we fail fast if the model isn't enabled.
            candidate_model.count_tokens("healthcheck")
            return candidate_model
        except google_exceptions.NotFound as exc:
            logger.warning("Gemini model '%s' not found: %s", candidate, exc)
            errors.append(f"{candidate}: not found")
        except google_exceptions.PermissionDenied as exc:
            logger.warning("Gemini model '%s' permission denied: %s", candidate, exc)
            errors.append(f"{candidate}: permission denied")
        except (google_exceptions.GoogleAPIError, ConnectionError, TimeoutError) as exc:
            logger.warning("Network/API error initializing model '%s': %s", candidate, exc)
            errors.append(f"{candidate}: {type(exc).__name__}")
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("Unexpected error initializing Gemini model '%s'", candidate, exc_info=exc)
            errors.append(f"{candidate}: {type(exc).__name__}: {exc}")

    raise RuntimeError(
        "None of the configured Gemini models could be initialized. "
        "Tried -> " + ", ".join(errors)
    )


def _gemini_init_skipped() -> bool:
    """True when Gemini init is disabled (e.g. CI/tests). Never set in production."""
    return os.getenv("SKIP_GEMINI_INIT", "").strip().lower() in ("1", "true", "yes")


if _gemini_init_skipped():
    model = None
    MODEL_INIT_ERROR = (
        "Gemini initialization skipped (SKIP_GEMINI_INIT is set). "
        "Unset this variable in production."
    )
    logger.warning("%s", MODEL_INIT_ERROR)
else:
    try:
        model = _resolve_model()
    except RuntimeError as err:  # pylint: disable=broad-except
        model = None
        MODEL_INIT_ERROR = (
            "Gemini model is unavailable. Update your google-generativeai package "
            "(`pip install -U google-generativeai`), ensure your API key has access, "
            "or set GEMINI_MODEL to a supported model (e.g., gemini-2.5-flash). "
            f"Details: {err}"
        )
        logger.error("Gemini model initialization failed: %s", MODEL_INIT_ERROR)


def render_index(**context):
    """Render the homepage template, injecting any model availability warning."""
    if MODEL_INIT_ERROR:
        context.setdefault("model_error", MODEL_INIT_ERROR)
    return render_template(TEMPLATE_NAME, **context)


def _strip_code_fence(payload: str) -> str:
    cleaned = payload.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()
    return cleaned


def _extract_json_segment(cleaned: str) -> str:
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    return match.group(0) if match else cleaned


def _parse_model_json(raw_text: Optional[str]) -> Optional[Dict[str, Any]]:
    if not raw_text:
        return None
    cleaned = _strip_code_fence(raw_text)
    candidate = _extract_json_segment(cleaned)
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError:
        logger.debug("Failed to parse JSON from model response: %s", raw_text)
        return None
    return parsed if isinstance(parsed, dict) else None


def _coerce_score(value: Any) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, str):
        value = value.replace("%", "").strip()
    try:
        score = float(value)
    except (TypeError, ValueError):
        return None
    try:
        score_int = int(round(score))
    except OverflowError:
        return None
    return max(0, min(100, score_int))


def _ensure_list(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        parts = re.split(r"[;\n]+", value)
        return [part.strip() for part in parts if part.strip()]
    return []


def _build_email_analysis(raw_text: str) -> Optional[Dict[str, Any]]:
    parsed = _parse_model_json(raw_text)
    if not parsed:
        return None

    classification = str(
        parsed.get("classification")
        or parsed.get("verdict")
        or parsed.get("label")
        or ""
    ).strip()
    if not classification:
        return None

    risk_score = _coerce_score(parsed.get("risk_score") or parsed.get("risk"))
    confidence = _coerce_score(parsed.get("confidence"))
    summary = parsed.get("summary") or parsed.get("highlight") or parsed.get("rationale")
    indicators = (
        parsed.get("key_findings")
        or parsed.get("indicators")
        or parsed.get("signals")
    )
    recommendations = parsed.get("recommended_actions") or parsed.get("actions")

    return {
        "classification": classification.lower(),
        "display_classification": classification,
        "risk_score": risk_score,
        "confidence": confidence,
        "summary": summary.strip() if isinstance(summary, str) else "",
        "indicators": _ensure_list(indicators),
        "recommendations": _ensure_list(recommendations),
        "raw": raw_text,
    }


def _build_url_analysis(raw_text: str) -> Optional[Dict[str, Any]]:
    parsed = _parse_model_json(raw_text)
    if not parsed:
        return None

    classification = str(
        parsed.get("classification")
        or parsed.get("category")
        or parsed.get("label")
        or ""
    ).strip()
    if not classification:
        return None

    risk_score = _coerce_score(parsed.get("risk_score") or parsed.get("risk"))
    confidence = _coerce_score(parsed.get("confidence"))
    summary = parsed.get("verdict_reasoning") or parsed.get("summary") or parsed.get("explanation")
    indicators = parsed.get("signals") or parsed.get("indicators") or parsed.get("evidence")
    recommendations = parsed.get("recommended_actions") or parsed.get("actions")

    return {
        "classification": classification.lower(),
        "display_classification": classification,
        "risk_score": risk_score,
        "confidence": confidence,
        "summary": summary.strip() if isinstance(summary, str) else "",
        "indicators": _ensure_list(indicators),
        "recommendations": _ensure_list(recommendations),
        "raw": raw_text,
    }


def predict_fake_or_real_email_content(text: str) -> str:
    """Classify the supplied email text as real or scam using the Gemini model."""
    if not text.strip():
        return "Unable to classify empty text. Please provide content to analyze."

    # Validate text length
    if len(text) > MAX_TEXT_LENGTH:
        return f"Text is too long. Maximum length is {MAX_TEXT_LENGTH:,} characters. Please provide a shorter excerpt."

    if model is None:
        return MODEL_INIT_ERROR

    prompt = f"""
    You are an expert in fraud analysis. Evaluate the email or message content below and respond in JSON with this exact shape:
    {{
      "classification": "scam" | "legitimate" | "suspicious",
      "risk_score": 0-100 (integer, 100 = most risky),
      "confidence": 0-100 (integer confidence in your verdict),
      "summary": "one-sentence insight about why you chose this verdict",
      "key_findings": ["bullet highlighting evidence", "..."],
      "recommended_actions": ["next step for user", "..."]
    }}

    Requirements:
    - Always fill every field. If unsure, choose your best estimate.
    - The response must be valid JSON without extra commentary.

    Content to evaluate:
    ---
    {text}
    ---
    """

    try:
        # API call with timeout handling (library handles timeouts internally)
        response = model.generate_content(prompt)
    except google_exceptions.DeadlineExceeded:
        logger.error("Gemini API call timed out after %d seconds", API_TIMEOUT_SECONDS)
        return "Classification request timed out. The service may be busy. Please try again in a moment."
    except google_exceptions.GoogleAPIError as exc:
        logger.error("Gemini API error during classification: %s", exc)
        return f"API error occurred: {str(exc)}. Please check your API key and billing status."
    except (ConnectionError, TimeoutError) as exc:
        logger.error("Network error during classification: %s", exc)
        return "Network error occurred. Please check your internet connection and try again."
    except Exception as exc:  # pylint: disable=broad-except
        logger.exception("Unexpected error during email classification: %s", exc, exc_info=True)
        return f"Classification failed due to an unexpected error: {type(exc).__name__}. Please try again."

    raw_text = response.text if response else ""
    analysis = _build_email_analysis(raw_text or "")
    if analysis:
        return analysis
    return raw_text.strip() if raw_text else "Classification failed. The model response was empty or invalid."


def url_detection(url: str) -> str:
    """Classify the supplied URL into threat categories using the Gemini model."""
    if model is None:
        return MODEL_INIT_ERROR

    # Validate URL length
    if len(url) > MAX_URL_LENGTH:
        return f"URL is too long. Maximum length is {MAX_URL_LENGTH:,} characters."

    prompt = f"""
    You are an advanced URL threat analyst. Evaluate the URL below and respond in JSON with:
    {{
      "classification": "benign" | "phishing" | "malware" | "defacement" | "suspicious",
      "risk_score": 0-100,
      "confidence": 0-100,
      "verdict_reasoning": "one-sentence explanation",
      "signals": ["indicator 1", "indicator 2"],
      "recommended_actions": ["step 1", "step 2"]
    }}

    Rules:
    - Always produce valid JSON only.
    - Risk score should align with the confidence and classification (higher = more dangerous).

    URL to evaluate: {url}
    """

    try:
        # API call with timeout handling (library handles timeouts internally)
        response = model.generate_content(prompt)
    except google_exceptions.DeadlineExceeded:
        logger.error("Gemini API call timed out after %d seconds", API_TIMEOUT_SECONDS)
        return "URL analysis request timed out. The service may be busy. Please try again in a moment."
    except google_exceptions.GoogleAPIError as exc:
        logger.error("Gemini API error during URL detection: %s", exc)
        return f"API error occurred: {str(exc)}. Please check your API key and billing status."
    except (ConnectionError, TimeoutError) as exc:
        logger.error("Network error during URL detection: %s", exc)
        return "Network error occurred. Please check your internet connection and try again."
    except Exception as exc:  # pylint: disable=broad-except
        logger.exception("Unexpected error during URL detection: %s", exc, exc_info=True)
        return f"Detection failed due to an unexpected error: {type(exc).__name__}. Please try again."

    raw_text = response.text if response else ""
    analysis = _build_url_analysis(raw_text or "")
    if analysis:
        return analysis
    return raw_text.strip() if raw_text else "Detection failed. The model response was empty or invalid."


def _strip_html(html: str) -> str:
    return re.sub(r"<[^>]+>", " ", html)


def _extract_eml_text(raw_bytes: bytes) -> str:
    message = BytesParser(policy=policy.default).parsebytes(raw_bytes)
    texts: List[str] = []

    for part in message.walk():
        content_type = part.get_content_type()
        if content_type == "text/plain":
            texts.append(part.get_content())
    if not texts:
        for part in message.walk():
            if part.get_content_type() == "text/html":
                texts.append(_strip_html(part.get_content()))
    flattened = "\n".join(texts)
    return flattened.strip()


def extract_text_from_upload(file_storage) -> tuple[str, str]:
    """Extract text content from an uploaded PDF or TXT file."""
    filename = file_storage.filename or ""
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    raw_bytes = file_storage.read()
    file_storage.seek(0)  # Reset file pointer for potential re-reading

    if not raw_bytes:
        return "", "Uploaded file is empty."

    if extension == "pdf":
        try:
            pdf_reader = PyPDF2.PdfReader(BytesIO(raw_bytes))
            extracted = " ".join(page.extract_text() or "" for page in pdf_reader.pages).strip()
            if extracted:
                return extracted, ""
            return "", "Unable to extract text from the PDF."
        except PyPDF2.errors.PdfReadError as exc:
            logger.error("PDF read error: %s", exc)
            return "", "Unable to read the PDF file. The file may be corrupted or encrypted. Please try another document."
        except ValueError as exc:
            logger.error("PDF value error: %s", exc)
            return "", "Invalid PDF file format. Please ensure the file is a valid PDF document."
    if extension == "txt":
        try:
            extracted = raw_bytes.decode("utf-8", errors="ignore").strip()
            if extracted:
                return extracted, ""
            return "", "Unable to extract text from the text file."
        except UnicodeDecodeError as exc:
            logger.error("Text file decode error: %s", exc)
            return "", "Unable to decode the text file. Please ensure it is UTF-8 encoded or try a different file."
    if extension == "docx":
        try:
            document = Document(BytesIO(raw_bytes))
            extracted = "\n".join(p.text for p in document.paragraphs if p.text).strip()
            if extracted:
                return extracted, ""
            return "", "Unable to extract text from the DOCX file."
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("DOCX read error: %s", exc, exc_info=True)
            error_type = type(exc).__name__
            return "", f"Unable to read the DOCX file ({error_type}). Please upload a standard Word document (.docx format)."
    if extension == "eml":
        try:
            extracted = _extract_eml_text(raw_bytes)
            if extracted:
                return extracted, ""
            return "", "Unable to extract text from the EML file."
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("EML parse error: %s", exc, exc_info=True)
            error_type = type(exc).__name__
            return "", f"Unable to parse the email file ({error_type}). Please ensure it is a valid .eml email message file."

    return "", "Invalid file type. Please upload a PDF, TXT, DOCX, or EML file."


def is_supported_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def _is_private_ip(hostname: str) -> bool:
    """Check if hostname resolves to a private IP address."""
    try:
        # Resolve hostname to IP
        ip_addr = socket.gethostbyname(hostname)
        ip_obj = ipaddress.ip_address(ip_addr)
        
        # Check against private IP ranges
        for private_range in PRIVATE_IP_RANGES:
            if ip_obj in private_range:
                return True
        return False
    except (OSError, ValueError):
        # DNS / resolution failures (incl. socket.gaierror) — block conservatively
        return True


def normalize_url_input(raw: str) -> str:
    """
    Turn bare domains (e.g. example.com, www.example.com/path) into https URLs
    so users are not required to type a scheme. Protocol-relative // URLs become https.
    """
    s = raw.strip()
    if not s:
        return s
    lower = s.lower()
    if lower.startswith("http://") or lower.startswith("https://"):
        return s
    if lower.startswith("//"):
        return "https:" + s
    return "https://" + s


def is_valid_url(url: str) -> bool:
    """Validate URL format and check for SSRF risks."""
    if not url or len(url) > MAX_URL_LENGTH:
        return False
    
    parsed = urlparse(url)
    
    # Only allow http and https protocols
    if parsed.scheme not in ("http", "https"):
        return False
    
    # Must have a netloc (domain)
    if not parsed.netloc:
        return False
    
    # Block localhost and private IPs
    hostname = parsed.hostname or ""
    if not hostname:
        return False
    
    # Block common localhost variations
    localhost_variants = ["localhost", "127.0.0.1", "0.0.0.0", "::1", "0:0:0:0:0:0:0:1"]
    if hostname.lower() in localhost_variants:
        return False
    
    # Check for private IP ranges
    if _is_private_ip(hostname):
        return False
    
    return True


# Routes
@app.route("/")
def home():
    """Homepage route."""
    return render_index()


@app.route("/health")
def health():
    """Health check endpoint for monitoring and load balancers."""
    return jsonify({
        "status": "healthy",
        "version": __version__,
        "model_available": model is not None,
        "model_error": MODEL_INIT_ERROR if not model else None
    }), 200


@app.route("/scam/", methods=["POST"])
@limiter.limit("10 per minute")  # Rate limit: 10 file uploads per minute
def detect_scam():
    """Analyze uploaded file for phishing/scam content."""
    uploaded_file = request.files.get("file")
    if not uploaded_file or not uploaded_file.filename:
        return render_index(file_message="No file uploaded. Please select a file to analyze.")

    if not is_supported_file(uploaded_file.filename):
        return render_index(
            file_message="Unsupported file type. Please upload PDF, TXT, DOCX, or EML files."
        )

    extracted_text, error_message = extract_text_from_upload(uploaded_file)
    if error_message:
        return render_index(file_message=error_message)

    # Validate extracted text length
    if len(extracted_text) > MAX_TEXT_LENGTH:
        return render_index(
            file_message=f"Extracted text is too long ({len(extracted_text):,} characters). "
            f"Maximum length is {MAX_TEXT_LENGTH:,} characters. Please use a smaller file."
        )

    message = predict_fake_or_real_email_content(extracted_text)
    if isinstance(message, dict):
        return render_index(file_analysis=message)
    return render_index(file_message=message)


@app.route("/predict", methods=["POST"])
@limiter.limit("20 per minute")  # Rate limit: 20 URL analyses per minute
def predict_url():
    """Analyze URL for phishing/malware threats."""
    raw_url = request.form.get("url", "").strip()
    url = normalize_url_input(raw_url)

    if not url:
        return render_index(url_message="Please provide a URL to classify.")

    # Validate URL length before parsing
    if len(url) > MAX_URL_LENGTH:
        return render_index(
            url_message=f"URL is too long. Maximum length is {MAX_URL_LENGTH:,} characters.",
            input_url=raw_url
        )

    if not is_valid_url(url):
        return render_index(
            url_message="Invalid URL or security risk. Use a public website (http(s):// or just "
            "example.com). Localhost and private network addresses are not allowed.",
            input_url=raw_url
        )

    classification = url_detection(url)
    if isinstance(classification, dict):
        return render_index(input_url=url, url_analysis=classification)
    return render_index(input_url=url, url_message=classification)


if __name__ == "__main__":
    debug_mode = os.getenv("FLASK_DEBUG", "False").lower() == "true"
    port = int(os.getenv("PORT", 5000))
    app.run(debug=debug_mode, host="0.0.0.0", port=port)
