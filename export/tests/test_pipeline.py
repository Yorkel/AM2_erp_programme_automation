"""
Smoke tests for the atlas-ed-data pipeline.

Run with: pytest tests/ -v
"""
import sys
from pathlib import Path

# Add src to path so imports work
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))


# ─── 1. Import tests ───────────────────────────────────────────────

class TestImports:
    """Every scraper module can be imported without error."""

    def test_import_england_scrapers(self):
        from england.dfe import scrape_dfe
        from england.schoolsweek import scrape_schoolsweek
        from england.epi import scrape_epi
        from england.nuffield import scrape_nuffield
        from england.fftlabs import scrape_fft_datalab
        from england.fed import scrape_fed

    def test_import_ireland_scrapers(self):
        from ireland.gov_ie import scrape_gov_ie
        from ireland.esri import scrape_esri
        from ireland.erc import scrape_erc
        from ireland.teaching_council import scrape_teaching_council
        from ireland.education_matters import scrape_education_matters
        from ireland.rte import scrape_rte
        from ireland.thejournal import scrape_thejournal

    def test_import_scotland_scrapers(self):
        from scotland.gov_scot import scrape_gov_scot
        from scotland.sera import scrape_sera
        from scotland.gtcs import scrape_gtcs
        from scotland.ades import scrape_ades
        from scotland.children_in_scotland import scrape_children_in_scotland

    def test_import_run(self):
        import run

    def test_import_seed_supabase(self):
        from seed_supabase import csv_to_records, main


# ─── 2. Schema tests ───────────────────────────────────────────────

class TestSchema:
    """run.py configuration is consistent."""

    def test_all_scrapers_have_source_meta(self):
        import run
        for country_code, scraper_list in run.SCRAPERS.items():
            for source_key, _ in scraper_list:
                assert source_key in run.SOURCE_META, (
                    f"Scraper '{source_key}' in SCRAPERS['{country_code}'] "
                    f"has no entry in SOURCE_META"
                )

    def test_source_meta_has_required_fields(self):
        import run
        required = {"country", "type", "institution_name"}
        for source_key, meta in run.SOURCE_META.items():
            missing = required - set(meta.keys())
            assert not missing, (
                f"SOURCE_META['{source_key}'] is missing fields: {missing}"
            )

    def test_valid_type_values(self):
        import run
        valid_types = {
            "government", "think_tank", "funder", "research_org",
            "prof_body", "ed_media", "civil_society",
        }
        for source_key, meta in run.SOURCE_META.items():
            assert meta["type"] in valid_types, (
                f"SOURCE_META['{source_key}'] has invalid type: '{meta['type']}'. "
                f"Valid types: {valid_types}"
            )

    def test_valid_country_values(self):
        import run
        valid_countries = {"eng", "irl", "sco"}
        for source_key, meta in run.SOURCE_META.items():
            assert meta["country"] in valid_countries, (
                f"SOURCE_META['{source_key}'] has invalid country: '{meta['country']}'"
            )

    def test_all_countries_have_scrapers(self):
        import run
        assert "eng" in run.SCRAPERS, "No England scrapers configured"
        assert "irl" in run.SCRAPERS, "No Ireland scrapers configured"
        assert "sco" in run.SCRAPERS, "No Scotland scrapers configured"


# ─── 3. Supabase connection test ───────────────────────────────────

class TestSupabase:
    """Supabase is reachable and articles_raw table exists."""

    def test_supabase_connection(self):
        """Can connect to Supabase and query articles_raw."""
        import os
        from dotenv import load_dotenv

        load_dotenv(Path(__file__).resolve().parent.parent / ".env")
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_SERVICE_KEY")

        if not url or not key:
            import pytest
            pytest.skip("Supabase credentials not set — skipping")

        from supabase import create_client
        client = create_client(url, key)

        # Check articles_raw table exists by querying it
        result = client.table("articles_raw").select("id").limit(1).execute()
        assert result is not None

    def test_articles_raw_has_data(self):
        """articles_raw table has been seeded."""
        import os
        from dotenv import load_dotenv

        load_dotenv(Path(__file__).resolve().parent.parent / ".env")
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_SERVICE_KEY")

        if not url or not key:
            import pytest
            pytest.skip("Supabase credentials not set — skipping")

        from supabase import create_client
        client = create_client(url, key)

        result = client.table("articles_raw").select("id", count="exact").execute()
        assert result.count > 0, "articles_raw table is empty"
