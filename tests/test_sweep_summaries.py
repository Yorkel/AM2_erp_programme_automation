from src.scraping import sweep_summaries as sweep
from src.inference.summarise import FALLBACK_SUMMARY_MAX_WORDS


def test_fallback_summary_strips_duplicated_title_from_text_clean():
    row = {
        "title": "Schools face new attendance guidance",
        "text": "",
        "text_clean": (
            "Schools face new attendance guidance "
            "Headteachers said the guidance would need careful handling. "
            "The department said schools would receive support."
        ),
    }

    assert sweep._fallback_summary(row) == (
        "Headteachers said the guidance would need careful handling. "
        "The department said schools would receive support."
    )


def test_fallback_summary_clips_long_source_text():
    text = " ".join(f"word{i}" for i in range(80))

    summary = sweep._fallback_summary({"title": "", "text": text, "text_clean": ""})

    assert summary.endswith("...")
    assert len(summary.split()) == FALLBACK_SUMMARY_MAX_WORDS



def test_needs_summary_includes_blank_rows_without_text_for_placeholder_write():
    assert sweep._needs_summary({"summary": None, "text": "", "text_clean": ""})


def test_needs_summary_does_not_retry_placeholder_without_text():
    assert not sweep._needs_summary({
        "summary": sweep.PLACEHOLDER,
        "text": "",
        "text_clean": "",
    })


def test_apply_fallback_summaries_updates_articles_by_id():
    class FakeClient:
        def __init__(self):
            self.table_name = None
            self.updates = []
            self.filters = []

        def table(self, name):
            self.table_name = name
            return self

        def update(self, payload):
            self.updates.append(payload)
            return self

        def eq(self, column, value):
            self.filters.append((column, value))
            return self

        def execute(self):
            return None

    client = FakeClient()
    row = {
        "id": 42,
        "title": "Teacher recruitment rises",
        "text": (
            "Teacher recruitment rose this year, according to new figures. "
            "School leaders said shortages remained acute in some subjects."
        ),
        "text_clean": "",
    }

    ok, fail = sweep._apply_fallback_summaries(client, [row])

    assert (ok, fail) == (1, 0)
    assert client.table_name == "articles"
    assert client.filters == [("id", 42)]
    assert client.updates[0]["summary"] == (
        "Teacher recruitment rose this year, according to new figures. "
        "School leaders said shortages remained acute in some subjects."
    )
    assert "summary_generated_at" in client.updates[0]
