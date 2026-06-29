"""Shared Anthropic client factory that forces IPv4.

The GitHub Actions runner fails with `APIConnectionError: Connection error` when
calling api.anthropic.com, while reaching every other host (HF Space, Supabase,
the web) fine. That asymmetry is the classic signature of a broken IPv6 route on
the runner: it resolves Anthropic to an AAAA (IPv6) address it can't reach.

Binding the HTTP client to an IPv4 local address (`0.0.0.0`) forces IPv4 and
sidesteps that. Where IPv4 already works (dev container, Render, Streamlit Cloud)
this is a harmless no-op, so it's safe to use everywhere.

Usage:  client = make_anthropic_client(max_retries=5)
"""
from __future__ import annotations

import httpx
from anthropic import Anthropic


def make_anthropic_client(max_retries: int = 5) -> Anthropic:
    """Anthropic client pinned to IPv4 (works around the GitHub-runner IPv6
    connection failure). Picks up ANTHROPIC_API_KEY from the environment."""
    http_client = httpx.Client(
        # local_address forces the socket to bind IPv4, so the connection can't
        # try an unreachable IPv6 route. retries handles transient connect drops.
        transport=httpx.HTTPTransport(local_address="0.0.0.0", retries=2),
        timeout=httpx.Timeout(60.0, connect=15.0),
    )
    return Anthropic(max_retries=max_retries, http_client=http_client)
