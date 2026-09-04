"""Tests for ``src.scripts.scrape_conference_page`` source routing."""

import json
from unittest.mock import patch

import pytest

from src.scripts.scrape_conference_page import scrape_conference_page


class TestSourceRouting:
    def test_eccv_defaults_to_the_ecva_proceedings(self, tmp_path):
        with (
            patch("src.eccv.get_papers", return_value=[]) as proceedings,
            patch("src.eccv_accepted.get_papers", return_value=[]) as accepted,
        ):
            scrape_conference_page(output_dir=tmp_path, conference="eccv", year=2024)

        proceedings.assert_called_once_with(year=2024)
        accepted.assert_not_called()

    def test_eccv_accepted_source_uses_the_conference_site(self, tmp_path):
        with (
            patch("src.eccv.get_papers", return_value=[]) as proceedings,
            patch("src.eccv_accepted.get_papers", return_value=[]) as accepted,
        ):
            scrape_conference_page(
                output_dir=tmp_path, conference="eccv", year=2026, source="accepted"
            )

        accepted.assert_called_once_with(year=2026)
        proceedings.assert_not_called()

    def test_accepted_source_is_rejected_for_other_conferences(self, tmp_path):
        with pytest.raises(ValueError, match="only supported for eccv"):
            scrape_conference_page(
                output_dir=tmp_path, conference="cvpr", year=2026, source="accepted"
            )

    def test_unknown_source_raises(self, tmp_path):
        with pytest.raises(ValueError, match="Source unknown is not supported"):
            scrape_conference_page(
                output_dir=tmp_path, conference="eccv", year=2026, source="unknown"
            )

    def test_unknown_conference_still_raises(self, tmp_path):
        with pytest.raises(ValueError, match="Conference wacv is not supported"):
            scrape_conference_page(output_dir=tmp_path, conference="wacv", year=2026)


class TestOutput:
    def test_writes_expected_filename_and_content(self, tmp_path):
        papers = [
            {
                "title": "A Paper",
                "author": "Alice, Bob",
                "abstract": None,
                "page": "https://eccv.ecva.net/virtual/2026/poster/1",
                "pdf": None,
            }
        ]
        with patch("src.eccv_accepted.get_papers", return_value=papers):
            scrape_conference_page(
                output_dir=tmp_path, conference="eccv", year=2026, source="accepted"
            )

        output_path = tmp_path / "eccv2026_papers.json"
        assert output_path.exists()
        assert json.loads(output_path.read_text()) == papers

    def test_serializes_pydantic_url_objects(self, tmp_path):
        from src.utils import PartialPaper

        papers = [
            PartialPaper(
                title="A Paper",
                author="Alice",
                page="https://eccv.ecva.net/virtual/2026/poster/1",
            ).model_dump()
        ]
        with patch("src.eccv_accepted.get_papers", return_value=papers):
            scrape_conference_page(
                output_dir=tmp_path, conference="eccv", year=2026, source="accepted"
            )

        loaded = json.loads((tmp_path / "eccv2026_papers.json").read_text())
        assert loaded[0]["page"] == "https://eccv.ecva.net/virtual/2026/poster/1"

    def test_creates_missing_output_directory(self, tmp_path):
        output_dir = tmp_path / "nested" / "json"
        with patch("src.eccv_accepted.get_papers", return_value=[]):
            scrape_conference_page(
                output_dir=output_dir, conference="eccv", year=2026, source="accepted"
            )

        assert (output_dir / "eccv2026_papers.json").exists()
