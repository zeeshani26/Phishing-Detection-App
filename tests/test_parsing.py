"""Tests for JSON parsing and score coercion helpers."""
import pytest

from main import _coerce_score, _ensure_list, _parse_model_json, _strip_code_fence


@pytest.mark.parametrize(
    "raw,expected",
    [
        ('{"classification": "scam", "risk_score": 80}', True),
        ("```json\n{\"classification\": \"legitimate\"}\n```", True),
        ("Here is the result: {\"classification\": \"suspicious\"}", True),
        ("not json", False),
        ("", False),
    ],
)
def test_parse_model_json(raw, expected):
    parsed = _parse_model_json(raw)
    if expected:
        assert isinstance(parsed, dict)
        assert "classification" in parsed or "verdict" in parsed or len(parsed) > 0
    else:
        assert parsed is None


def test_strip_code_fence():
    assert "classification" in _strip_code_fence('```json\n{"classification": "x"}\n```')


@pytest.mark.parametrize(
    "value,out",
    [
        (50, 50),
        ("75", 75),
        ("80%", 80),
        (None, None),
        ("bad", None),
        (150, 100),
        (-5, 0),
    ],
)
def test_coerce_score(value, out):
    assert _coerce_score(value) == out


def test_ensure_list():
    assert _ensure_list(["a", "b"]) == ["a", "b"]
    assert _ensure_list("a;b\nc") == ["a", "b", "c"]
    assert _ensure_list(None) == []
