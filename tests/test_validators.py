"""Tests for URL validation and private-IP checks."""
from unittest.mock import patch

import pytest

from main import _is_private_ip, is_valid_url, normalize_url_input


@pytest.mark.parametrize(
    "raw,normalized",
    [
        ("google.com", "https://google.com"),
        ("www.example.org/path?q=1", "https://www.example.org/path?q=1"),
        ("https://already.com", "https://already.com"),
        ("http://insecure.net", "http://insecure.net"),
        ("//cdn.example.com/x", "https://cdn.example.com/x"),
    ],
)
def test_normalize_url_input(raw, normalized):
    assert normalize_url_input(raw) == normalized


def test_bare_hostname_valid_after_normalize():
    with patch("main.socket.gethostbyname", return_value="93.184.216.34"):
        assert is_valid_url(normalize_url_input("example.com")) is True


@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://example.com/path", True),
        ("http://example.com", True),
        ("ftp://example.com", False),
        ("not a url", False),
        ("", False),
        ("https://127.0.0.1/", False),
        ("https://localhost/foo", False),
    ],
)
def test_is_valid_url_public_and_scheme(url, expected):
    with patch("main.socket.gethostbyname", return_value="93.184.216.34"):
        assert is_valid_url(url) is expected


def test_is_valid_url_blocks_resolved_private_ip():
    with patch("main.socket.gethostbyname", return_value="192.168.1.1"):
        assert is_valid_url("https://evil-looking.example.com/") is False


def test_is_private_ip_detects_private():
    with patch("main.socket.gethostbyname", return_value="10.0.0.1"):
        assert _is_private_ip("anything.resolvable") is True


def test_is_private_ip_public():
    with patch("main.socket.gethostbyname", return_value="8.8.8.8"):
        assert _is_private_ip("dns.google") is False


def test_is_private_ip_dns_failure_is_conservative():
    with patch("main.socket.gethostbyname", side_effect=OSError("nxdomain")):
        assert _is_private_ip("does-not-exist.invalid") is True
