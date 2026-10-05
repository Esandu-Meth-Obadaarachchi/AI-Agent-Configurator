from __future__ import annotations

from app.tools.web_fetch import html_to_text


def test_strips_scripts_and_keeps_text() -> None:
    html = "<html><head><title>T</title><script>x()</script></head><body><p>Hello</p><p>World</p></body></html>"
    out = html_to_text(html)
    assert out.startswith("T")
    assert "Hello" in out and "x()" not in out
