"""Pytest setup: environment must be set before ``main`` is imported."""
import os

# CI/local tests: avoid real Gemini API calls and key requirements at import time.
os.environ.setdefault("GOOGLE_API_KEY", "test-key-not-for-production")
os.environ.setdefault("SKIP_GEMINI_INIT", "1")
