# ThreatGuard AI - Phishing Detection Application

A modern web application that uses Google's Gemini AI to detect phishing emails and malicious URLs. Upload suspicious files or analyze URLs to get real-time threat intelligence with risk scores, confidence levels, and actionable recommendations.

## 🎯 Features

- **Multi-Format File Analysis**: Upload and analyze PDF, TXT, DOCX, and EML (email) files
- **URL Threat Detection**: Analyze any URL for phishing, malware, or suspicious activity
- **AI-Powered Analysis**: Powered by Google Gemini AI with intelligent model fallback
- **Detailed Reports**: Get risk scores, confidence levels, key indicators, and recommended actions
- **Modern UI**: Beautiful glassmorphism interface with responsive design
- **Real-time Processing**: Instant analysis with visual feedback

## 📋 Prerequisites

Before you begin, ensure you have:

- **Python 3.9 or newer** installed on your system
- A **Google AI Studio account** with billing enabled
- A **Gemini API key** from [Google AI Studio](https://makersuite.google.com/app/apikey)

## 🚀 Quick Start

### Step 1: Clone the Repository

```bash
git clone <repository-url>
cd Phishing-Detection-App
```

### Step 2: Set Up Virtual Environment (Recommended)

**Windows (PowerShell):**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

**Linux/Mac:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables

Create a `.env` file in the project root:

**Windows (PowerShell):**
```powershell
@"
GOOGLE_API_KEY=your-actual-api-key-here
"@ | Out-File -FilePath .env -Encoding utf8 -Force
```

**Linux/Mac:**
```bash
echo "GOOGLE_API_KEY=your-actual-api-key-here" > .env
```

**⚠️ Important**: Replace `your-actual-api-key-here` with your actual Gemini API key from Google AI Studio.

### Step 5: Run the Application

```bash
python main.py
```

The application will start on `http://127.0.0.1:5000`. Open this URL in your browser to access the web interface.

## 📖 Usage Guide

### Analyzing Files

1. Click on the **"File Sentiment Radar"** section
2. Click **"Choose File"** and select a PDF, TXT, DOCX, or EML file
3. Click **"Initiate Deep Scan"**
4. Review the analysis results including:
   - Classification (scam, legitimate, suspicious)
   - Risk score (0-100)
   - Confidence level
   - Key findings
   - Recommended actions

### Analyzing URLs

1. Click on the **"Quantum URL Firewall"** section
2. Enter a URL in the text field (must include `http://` or `https://`)
3. Click **"Classify Vector"**
4. Review the threat analysis including:
   - Classification (benign, phishing, malware, suspicious)
   - Risk score
   - Threat signals
   - Recommended actions

## ⚙️ Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GOOGLE_API_KEY` | Yes | Your Gemini API key from Google AI Studio |
| `GEMINI_MODEL` | No | Override default model selection (e.g., `gemini-1.5-pro`) |
| `FLASK_DEBUG` | No | Set to `true` for debug mode (default: `false`) |
| `PORT` | No | Port to run the application (default: `5000`) |
| `LOG_LEVEL` | No | Logging level: DEBUG, INFO, WARNING, ERROR (default: `INFO`) |
| `SECRET_KEY` | No | Flask secret key for sessions (auto-generated if not set) |

### Model Selection

The application automatically selects the best available Gemini model. It tries models in this order:

1. `GEMINI_MODEL` (if set in environment)
2. `gemini-2.0-flash-exp`
3. `gemini-2.0-flash`
4. `gemini-2.0-flash-001`
5. `gemini-2.0-flash-lite-latest`
6. `gemini-1.5-flash-latest`
7. `gemini-1.5-flash`
8. `gemini-1.5-flash-001`
9. `gemini-1.0-pro`
10. `gemini-pro`

To use a specific model, set `GEMINI_MODEL` in your `.env` file:
```
GEMINI_MODEL=gemini-1.5-pro
```

## 🏗️ Project Structure

```
Phishing-Detection-App/
├── main.py              # Main Flask application
├── requirements.txt     # Python dependencies
├── Procfile             # Heroku deployment configuration
├── .gitignore          # Git ignore rules
├── templates/
│   └── index.html      # Web UI template
└── README.md           # This file
```

## 🔒 Security Features

- **Rate Limiting**: 200 requests/day, 50/hour (default), 10 file uploads/minute, 20 URL analyses/minute
- **SSRF Protection**: Blocks localhost and private IP addresses
- **File Size Limits**: Maximum 5MB upload size
- **Input Validation**: URL format validation, text length limits (50,000 chars)
- **Environment Variables**: All sensitive data via environment variables
- **Secure Headers**: Production-ready Flask configuration

## 🚢 Deployment

### Heroku

The project includes a `Procfile` for Heroku deployment:

1. Create a Heroku app: `heroku create your-app-name`
2. Set environment variables: `heroku config:set GOOGLE_API_KEY=your-key`
3. Deploy: `git push heroku main`

### Docker (Example)

```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["gunicorn", "main:app"]
```

### Production Checklist

- [x] Debug mode disabled (controlled by `FLASK_DEBUG` env var)
- [x] Rate limiting configured
- [x] Logging configured
- [x] Security features enabled (SSRF protection, input validation)
- [ ] Configure HTTPS/SSL certificates
- [ ] Use a production WSGI server (gunicorn, uWSGI)
- [ ] Set up monitoring and error tracking
- [ ] Configure environment variables securely
- [ ] Set up log rotation for `app.log`

## 🐛 Troubleshooting

### "Model unavailable" Error

1. **Update the SDK**: `pip install -U google-generativeai`
2. **Check API key**: Ensure your `GOOGLE_API_KEY` is correct
3. **Verify billing**: Ensure billing is enabled in Google AI Studio
4. **Check model access**: Some models require special access

### File Upload Issues

- **File too large**: Maximum file size is 5MB
- **Unsupported format**: Only PDF, TXT, DOCX, and EML files are supported
- **Empty file**: Ensure the file contains extractable text

### URL Analysis Issues

- **Invalid URL format**: URLs must include `http://` or `https://`
- **Network errors**: Check your internet connection
- **API errors**: Verify your API key and billing status

## 📝 License

This project is proprietary software. All rights reserved.

## 👤 Author

**Zeeshan Ilahi™**

---

**⚠️ Disclaimer**: This tool is for educational and security research purposes. Always verify results through multiple sources and use professional security tools for critical decisions.