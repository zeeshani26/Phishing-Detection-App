# ThreatGuard AI - Phishing Detection Application

A modern web application that uses Google's Gemini AI to detect phishing emails and malicious URLs. Upload suspicious files or analyze URLs to get real-time threat intelligence with risk scores, confidence levels, and actionable recommendations.

## 🌐 Live Deployment

**🔗 [Try it now: https://phishing-detection-app-y2vz.onrender.com/](https://phishing-detection-app-y2vz.onrender.com/)**

> **Note**: This application is deployed on Render's free tier. If the service hasn't been used recently, it may take 30-60 seconds to spin up on the first request. This is normal behavior for free tier services that spin down after inactivity.

## 🎯 Features

- **Multi-Format File Analysis**: Upload and analyze PDF, TXT, DOCX, and EML (email) files
- **URL Threat Detection**: Analyze any URL for phishing, malware, or suspicious activity
- **AI-Powered Analysis**: Powered by Google Gemini AI with intelligent model fallback
- **Detailed Reports**: Get risk scores, confidence levels, key indicators, and recommended actions
- **Modern UI**: Beautiful glassmorphism interface with responsive design
- **Real-time Processing**: Instant analysis with visual feedback

## 📋 Prerequisites

- **Python 3.9 or newer**
- **Google AI Studio account** with billing enabled
- **Gemini API key** from [Google AI Studio](https://makersuite.google.com/app/apikey)

## 🚀 Quick Start

### Local Development

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd Phishing-Detection-App
   ```

2. **Create virtual environment**:
   ```bash
   python -m venv .venv
   # Windows
   .venv\Scripts\Activate.ps1
   # Linux/Mac
   source .venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**:
   Create a `.env` file:
   ```
   GOOGLE_API_KEY=your-actual-api-key-here
   FLASK_DEBUG=false
   ```

5. **Run the application**:
   ```bash
   python main.py
   ```
   Open `http://127.0.0.1:5000` in your browser.

## 📖 Usage

### Analyzing Files
1. Click "File Sentiment Radar"
2. Upload a PDF, TXT, DOCX, or EML file
3. Click "Initiate Deep Scan"
4. Review the analysis results

### Analyzing URLs
1. Click "Quantum URL Firewall"
2. Enter a URL (must include `http://` or `https://`)
3. Click "Classify Vector"
4. Review the threat analysis

## ⚙️ Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GOOGLE_API_KEY` | Yes | Your Gemini API key from Google AI Studio |
| `GEMINI_MODEL` | No | Override default model (e.g., `gemini-1.5-pro`) |
| `FLASK_DEBUG` | No | Debug mode (default: `false`) |
| `PORT` | No | Port number (default: `5000`) |
| `LOG_LEVEL` | No | Logging level: DEBUG, INFO, WARNING, ERROR (default: `INFO`) |

### Model Selection

The application automatically selects the best available Gemini model with intelligent fallback. To use a specific model, set `GEMINI_MODEL` in your environment variables.

## 🔒 Security Features

- **Rate Limiting**: 200 requests/day, 50/hour, 10 file uploads/minute, 20 URL analyses/minute
- **SSRF Protection**: Blocks localhost and private IP addresses
- **File Size Limits**: Maximum 5MB upload size
- **Input Validation**: URL format validation, text length limits (50,000 chars)
- **Environment Variables**: All sensitive data via environment variables

## 🚢 Deployment

### Render.com

1. Connect your GitHub repository
2. Set environment variables in Render dashboard:
   - `GOOGLE_API_KEY` (required)
   - `FLASK_DEBUG=false` (recommended)
3. Build command: `pip install -r requirements.txt`
4. Start command: `gunicorn main:app`

**Note**: On Render's free tier, services spin down after 15 minutes of inactivity. The first request after spin-down may take 30-60 seconds to respond while the service starts up.

### Other Platforms

The application can be deployed on any platform that supports Python and WSGI (Heroku, Railway, Fly.io, etc.). Use `gunicorn main:app` as the start command.

## 🏗️ Project Structure

```
Phishing-Detection-App/
├── main.py              # Main Flask application
├── requirements.txt     # Python dependencies
├── Procfile             # Deployment configuration
├── templates/
│   └── index.html      # Web UI template
└── README.md           # This file
```

## 🐛 Troubleshooting

### "Model unavailable" Error
- Update SDK: `pip install -U google-generativeai`
- Verify API key and billing status in Google AI Studio

### File Upload Issues
- Maximum file size: 5MB
- Supported formats: PDF, TXT, DOCX, EML

### URL Analysis Issues
- URLs must include `http://` or `https://`
- Localhost and private IPs are blocked for security

## 📝 License

This project is proprietary software. All rights reserved.

## 👤 Author

**Zeeshan Ilahi™**

---

**⚠️ Disclaimer**: This tool is for educational and security research purposes. Always verify results through multiple sources and use professional security tools for critical decisions.
