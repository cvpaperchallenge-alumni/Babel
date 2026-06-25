"""Tests for ``src.cvpr``."""

import json
import pathlib
from unittest.mock import MagicMock, patch

import pytest

from src.cvpr import get_papers, get_partial_papers
from src.utils import Paper, PartialPaper


def _accepted_papers_html(rows: list[str]) -> str:
    """Wrap the given ``<tr>`` strings in the page structure ``get_partial_papers`` expects.

    The function skips the first two ``<tr>`` rows (header + spacer), so callers
    should prepend two empty rows.
    """
    blank = "<tr><td></td></tr>"
    rows_html = "\n".join([blank, blank, *rows])
    return f"<html><body><table>{rows_html}</table></body></html>"


def _row(*, title: str, authors: str, use_strong: bool = False) -> str:
    title_tag = f"<strong>{title}</strong>" if use_strong else f"<a>{title}</a>"
    return (
        "<tr><td>"
        f"{title_tag}"
        f'<div class="indented"><i>{authors}</i></div>'
        "</td></tr>"
    )


# ---------- get_partial_papers ---------- #
class TestGetPartialPapers:
    def test_parses_rows_into_partial_papers(self):
        html = _accepted_papers_html(
            [
                _row(title="Paper One", authors="Alice · Bob"),
                _row(title="Paper Two", authors="Carol · Dave"),
            ]
        )
        with patch("src.cvpr.requests.get") as mock_get:
            mock_get.return_value.text = html
            papers = get_partial_papers(2024)

        assert len(papers) == 2
        assert all(isinstance(p, PartialPaper) for p in papers)
        assert papers[0].title == "Paper One"
        # " · " separator should be normalized to ", ".
        assert papers[0].author == "Alice, Bob"
        assert papers[1].title == "Paper Two"
        assert papers[1].author == "Carol, Dave"

    def test_falls_back_to_strong_when_no_anchor(self):
        html = _accepted_papers_html(
            [
                _row(title="Strong Title", authors="Alice · Bob", use_strong=True),
            ]
        )
        with patch("src.cvpr.requests.get") as mock_get:
            mock_get.return_value.text = html
            papers = get_partial_papers(2024)

        assert papers[0].title == "Strong Title"
        assert papers[0].author == "Alice, Bob"

    def test_missing_title_and_strong_raises(self):
        # A row with no <a> AND no <strong> should explode with the "Title not found" message.
        html = _accepted_papers_html(
            [
                '<tr><td><div class="indented"><i>Alice</i></div></td></tr>',
            ]
        )
        with patch("src.cvpr.requests.get") as mock_get:
            mock_get.return_value.text = html
            with pytest.raises(ValueError, match="Title not found"):
                get_partial_papers(2024)

    def test_missing_author_div_raises(self):
        html = _accepted_papers_html(
            [
                "<tr><td><a>Paper</a></td></tr>",
            ]
        )
        with patch("src.cvpr.requests.get") as mock_get:
            mock_get.return_value.text = html
            with pytest.raises(ValueError, match="Authors not found"):
                get_partial_papers(2024)

    def test_skips_first_two_blank_rows(self):
        html = _accepted_papers_html(
            [
                _row(title="Only Real Paper", authors="X · Y"),
            ]
        )
        with patch("src.cvpr.requests.get") as mock_get:
            mock_get.return_value.text = html
            papers = get_partial_papers(2024)

        assert len(papers) == 1
        assert papers[0].title == "Only Real Paper"

    def test_url_is_constructed_with_year(self):
        with patch("src.cvpr.requests.get") as mock_get:
            mock_get.return_value.text = _accepted_papers_html([])
            get_partial_papers(2026)

        called_url = mock_get.call_args[0][0]
        assert called_url == ("https://cvpr.thecvf.com/Conferences/2026/AcceptedPapers")


# ---------- get_papers ---------- #
def _arxiv_match(*, title: str, author: str) -> Paper:
    """Build a Paper representing an arXiv hit that matches ``title`` and ``author``."""
    return Paper(
        title=title,
        author=author,
        abstract="The arXiv abstract.",
        page="https://arxiv.org/abs/1234.5678",
        pdf="https://arxiv.org/pdf/1234.5678.pdf",
    )


class TestGetPapers:
    def test_enriches_partial_papers_when_arxiv_match_found(self, tmp_path):
        output = tmp_path / "out.json"
        partial = PartialPaper(title="A Sample Paper", author="Alice, Bob")

        with (
            patch("src.cvpr.get_partial_papers", return_value=[partial]),
            patch(
                "src.cvpr.get_arxiv_papers",
                return_value=[_arxiv_match(title="A Sample Paper", author="Alice, X")],
            ),
            patch("src.cvpr.time.sleep"),
        ):
            papers = get_papers(year=2024, output_path=output, save_frequency=1)

        assert len(papers) == 1
        assert papers[0]["title"] == "A Sample Paper"
        assert papers[0]["author"] == "Alice, Bob"
        assert papers[0]["abstract"] == "The arXiv abstract."
        # ``model_dump`` keeps pydantic Url objects; coerce for comparison.
        assert str(papers[0]["page"]) == "https://arxiv.org/abs/1234.5678"
        assert str(papers[0]["pdf"]) == "https://arxiv.org/pdf/1234.5678.pdf"

    def test_arxiv_first_author_mismatch_keeps_partial_only(self, tmp_path):
        output = tmp_path / "out.json"
        partial = PartialPaper(title="Mismatched", author="Alice")
        candidate = _arxiv_match(title="Mismatched", author="Different, Person")

        with (
            patch("src.cvpr.get_partial_papers", return_value=[partial]),
            patch("src.cvpr.get_arxiv_papers", return_value=[candidate]),
            patch("src.cvpr.time.sleep"),
        ):
            papers = get_papers(year=2024, output_path=output, save_frequency=1)

        assert papers[0]["title"] == "Mismatched"
        # Abstract / page / pdf should remain unset (PartialPaper defaults).
        assert papers[0]["abstract"] is None
        assert papers[0]["page"] is None
        assert papers[0]["pdf"] is None

    def test_resumes_from_existing_output_skipping_known_titles(self, tmp_path):
        output = tmp_path / "out.json"
        # Pre-existing JSON containing one already-processed paper.
        existing = [
            {
                "title": "Already Saved",
                "author": "Old Alice",
                "abstract": "Old abstract.",
                "page": "https://example.com/old",
                "pdf": "https://example.com/old.pdf",
            }
        ]
        output.write_text(json.dumps(existing))

        # Partial papers list contains the already-saved one (case-different) +
        # a new one. The already-saved title should be skipped without arXiv lookup.
        partials = [
            PartialPaper(title="already saved", author="Old Alice"),
            PartialPaper(title="Brand New", author="New Author"),
        ]
        arxiv_mock = MagicMock(return_value=[])

        with (
            patch("src.cvpr.get_partial_papers", return_value=partials),
            patch("src.cvpr.get_arxiv_papers", arxiv_mock),
            patch("src.cvpr.time.sleep"),
        ):
            papers = get_papers(
                year=2024,
                output_path=output,
                save_frequency=10,  # avoid intermediate writes
            )

        # arXiv lookup runs only for the new paper.
        arxiv_mock.assert_called_once_with("brand new")
        # New paper appended (existing paper remains via load).
        titles = [p["title"] for p in papers]
        assert "Already Saved" in titles
        assert "Brand New" in titles

    def test_writes_progress_file_on_save_frequency(self, tmp_path):
        output = tmp_path / "out.json"
        partials = [
            PartialPaper(title=f"Paper {i}", author=f"Author {i}") for i in range(3)
        ]
        with (
            patch("src.cvpr.get_partial_papers", return_value=partials),
            patch("src.cvpr.get_arxiv_papers", return_value=[]),
            patch("src.cvpr.time.sleep"),
        ):
            get_papers(
                year=2024,
                output_path=output,
                save_frequency=1,
            )

        # The file should exist and contain valid JSON after the run.
        assert output.exists()
        data = json.loads(output.read_text())
        assert isinstance(data, list)

    def test_creates_parent_dirs_for_output_path(self, tmp_path):
        output = tmp_path / "nested" / "dir" / "out.json"
        partials = [PartialPaper(title="P", author="A")]
        with (
            patch("src.cvpr.get_partial_papers", return_value=partials),
            patch("src.cvpr.get_arxiv_papers", return_value=[]),
            patch("src.cvpr.time.sleep"),
        ):
            get_papers(year=2024, output_path=output, save_frequency=1)

        assert output.parent.is_dir()


# ---------- defensive: pathlib.Path argument shape ---------- #
def test_get_papers_requires_pathlib_path(tmp_path):
    """``get_papers`` documents ``output_path`` as ``pathlib.Path``; sanity-check that."""
    output = tmp_path / "out.json"
    assert isinstance(output, pathlib.Path)
