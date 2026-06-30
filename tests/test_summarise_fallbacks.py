from types import SimpleNamespace

from src.inference.summarise import (
    PLACEHOLDER,
    extractive_fallback_summary,
    summarise_article,
    summarise_article_openai,
)


class FailingClaude:
    class messages:
        @staticmethod
        def create(**kwargs):
            raise RuntimeError("claude down")


class FakeOpenAI:
    def __init__(self, output_text="OpenAI summary text."):
        self.calls = []
        self.output_text = output_text
        self.responses = self

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(output_text=self.output_text)


def test_openai_summary_uses_responses_api_shape():
    client = FakeOpenAI("A concise generated summary.")

    result = summarise_article_openai(
        title="Attendance guidance",
        text="Schools received updated attendance guidance.",
        category="DfE",
        client=client,
    )

    assert result == "A concise generated summary."
    assert client.calls[0]["model"]
    assert "instructions" in client.calls[0]
    assert "Attendance guidance" in client.calls[0]["input"]


def test_summarise_article_tries_openai_after_claude_failure():
    openai_client = FakeOpenAI("OpenAI fallback summary.")

    result = summarise_article(
        title="Teacher recruitment rises",
        text="Teacher recruitment rose this year, according to new figures.",
        client=FailingClaude(),
        openai_client=openai_client,
    )

    assert result == "OpenAI fallback summary."
    assert len(openai_client.calls) == 1


def test_summarise_article_uses_local_fallback_when_providers_fail(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    result = summarise_article(
        title="Schools face new attendance guidance",
        text=(
            "Schools face new attendance guidance "
            "Headteachers said the guidance would need careful handling. "
            "The department said schools would receive support."
        ),
        allow_openai_fallback=False,
    )

    assert result == (
        "Headteachers said the guidance would need careful handling. "
        "The department said schools would receive support."
    )


def test_extractive_fallback_returns_placeholder_without_text():
    assert extractive_fallback_summary(title="Only a title", text="") == PLACEHOLDER
