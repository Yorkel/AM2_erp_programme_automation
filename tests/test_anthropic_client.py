"""Tests for the shared Anthropic client factory.

Covers the proxy-token gating added for the HF Space proxy (incident
2026-06-29): when PROXY_TOKEN is in the environment the client must send it as
the `x-proxy-token` header (so the proxy accepts the request); when it is unset,
no such header is sent.
"""
from src.inference.anthropic_client import make_anthropic_client


def test_proxy_token_sent_as_header_when_env_set(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("PROXY_TOKEN", "secret123")
    client = make_anthropic_client(1)
    assert client.default_headers.get("x-proxy-token") == "secret123"


def test_no_proxy_token_header_when_env_unset(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.delenv("PROXY_TOKEN", raising=False)
    client = make_anthropic_client(1)
    assert "x-proxy-token" not in client.default_headers
