from src.scraping.common import normalise_url, resolve_url
from src.scraping.newsletters.parse_html import canonical_url
from src.scraping.rss_adapter import _unwrap_google_url


def test_normalise_url_unwraps_outlook_safelinks_and_strips_tracking():
    raw = (
        "https://eur01.safelinks.protection.outlook.com/"
        "?url=https%3A%2F%2FExample.COM%2Fnews%2Fthing%2F%3Futm_source%3Dnl%26mc_cid%3Dabc%26id%3D123"
        "&data=ignored"
    )

    assert normalise_url(raw) == "https://example.com/news/thing?id=123"


def test_google_alert_url_is_unwrapped_and_normalised():
    raw = (
        "https://www.google.co.uk/url?sa=t&url="
        "https%3A%2F%2Fwww.bbc.com%2Fnews%2Farticles%2Fabc%3Fat_medium%3DRSS%26at_campaign%3Drss"
    )

    assert _unwrap_google_url(raw) == "https://www.bbc.com/news/articles/abc"


def test_resolve_url_handles_relative_paths_and_fragments():
    assert resolve_url("/News/Thing/?_locale=en#section", "https://Example.com/list/") == (
        "https://example.com/News/Thing"
    )


def test_resolve_url_keeps_content_query_params():
    assert resolve_url("story?category=schools&utm_campaign=x", "https://example.com/news/") == (
        "https://example.com/news/story?category=schools"
    )


def test_newsletter_canonical_url_uses_shared_normaliser():
    raw = (
        "https://emea01.safelinks.protection.outlook.com/"
        "?url=https%3A%2F%2Fwww.gov.uk%2Fgovernment%2Fnews%2Fexample%2F%3Fdm_i%3Dabc"
    )

    assert canonical_url(raw) == "https://www.gov.uk/government/news/example"
