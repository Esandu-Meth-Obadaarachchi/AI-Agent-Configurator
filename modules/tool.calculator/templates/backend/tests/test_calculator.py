from __future__ import annotations

import math

import pytest

from app.tools.calculator import calculator, evaluate


def test_arithmetic() -> None:
    assert evaluate("(1250 * 0.2) / 4") == 62.5
    assert evaluate("2 ^ 10") == 1024
    assert math.isclose(evaluate("sqrt(2) * pi"), math.sqrt(2) * math.pi)


def test_rejects_code() -> None:
    with pytest.raises(ValueError):
        evaluate("__import__('os').system('ls')")


def test_tool_reports_errors() -> None:
    assert calculator.invoke({"expression": "1/0"}).startswith("Error")
