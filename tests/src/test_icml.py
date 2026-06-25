"""Tests for ``src.icml``."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from src.icml import _validate_conference, get_papers


# ---------- _validate_conference ---------- #
class TestValidateConference:
    @pytest.mark.parametrize("conf", ["icml", "ICML", "Icml", "icml.cc", "ICML.cc"])
    def test_accepts_icml_variations(self, conf):
        assert _validate_conference(conf, 2024) == "ICML.cc/2024/Conference"

    @pytest.mark.parametrize("year", [2020, 2021, 2025, 2030])
    def test_year_2020_or_later_supported(self, year):
        assert _validate_conference("icml", year) == f"ICML.cc/{year}/Conference"

    @pytest.mark.parametrize("year", [2019, 2010, 1999])
    def test_year_before_2020_raises(self, year):
        with pytest.raises(ValueError, match="ICML for the year 2020 or later"):
            _validate_conference("icml", year)

    @pytest.mark.parametrize(
        "conf",
        ["cvpr", "iccv", "eccv", "neurips", "", "foo"],
    )
    def test_unsupported_conference_raises(self, conf):
        with pytest.raises(ValueError, match="Unsupported conference"):
            _validate_conference(conf, 2024)


# ---------- get_papers ---------- #
def _note(
    *,
    note_id: str,
    title: str,
    authors,
    abstract: str,
) -> SimpleNamespace:
    """Build an object shaped like an OpenReview note for testing."""
    return SimpleNamespace(
        id=note_id,
        content={
            "title": {"value": title},
            "authors": {"value": authors},
            "abstract": {"value": abstract},
        },
    )


class TestGetPapers:
    def test_returns_dicts_with_normalized_fields(self):
        notes = [
            _note(
                note_id="abc123",
                title="A Paper",
                authors=["Alice", "Bob", "Carol"],
                abstract="An abstract.",
            ),
            _note(
                note_id="def456",
                title="Another Paper",
                authors="Single String Author",
                abstract="Another abstract.",
            ),
        ]
        mock_client = MagicMock()
        mock_client.get_all_notes.return_value = notes

        with patch(
            "src.icml.openreview.api.OpenReviewClient", return_value=mock_client
        ) as mock_client_cls:
            papers = get_papers("icml", 2024)

        mock_client_cls.assert_called_once_with(baseurl="https://api2.openreview.net")
        mock_client.get_all_notes.assert_called_once_with(
            content={"venueid": "ICML.cc/2024/Conference"}
        )

        assert len(papers) == 2
        # List of authors should be joined with ", ".
        assert papers[0]["authors"] == "Alice, Bob, Carol"
        assert papers[0]["title"] == "A Paper"
        assert papers[0]["abstract"] == "An abstract."
        assert papers[0]["page"] == "https://openreview.net/forum?id=abc123"
        assert papers[0]["pdf"] == "https://openreview.net/pdf?id=abc123"
        # String authors should be passed through.
        assert papers[1]["authors"] == "Single String Author"

    def test_uses_authors_key_not_author(self):
        """ICML's JSON schema deliberately differs from other scrapers — the
        key is ``authors`` (plural), not ``author``. Regression coverage.
        """
        notes = [
            _note(
                note_id="x",
                title="T",
                authors=["A"],
                abstract="abs",
            )
        ]
        mock_client = MagicMock()
        mock_client.get_all_notes.return_value = notes

        with patch(
            "src.icml.openreview.api.OpenReviewClient", return_value=mock_client
        ):
            papers = get_papers("icml", 2024)

        assert "authors" in papers[0]
        assert "author" not in papers[0]

    def test_empty_result_returns_empty_list(self):
        mock_client = MagicMock()
        mock_client.get_all_notes.return_value = []

        with patch(
            "src.icml.openreview.api.OpenReviewClient", return_value=mock_client
        ):
            assert get_papers("icml", 2024) == []

    def test_invalid_conference_propagates_validation_error(self):
        with pytest.raises(ValueError, match="Unsupported conference"):
            get_papers("cvpr", 2024)

    def test_invalid_year_propagates_validation_error(self):
        with pytest.raises(ValueError, match="ICML for the year 2020 or later"):
            get_papers("icml", 2019)
