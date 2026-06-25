"""Tests for ``src.arxiv``."""

from unittest.mock import MagicMock, patch

import pytest
import requests

from src.arxiv import clean_text, create_session_with_retries, get_arxiv_papers


def _atom_feed(*entries: str) -> bytes:
    """Build a minimal arXiv-style Atom feed wrapping the given <entry> blocks."""
    joined = "\n".join(entries)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
{joined}
</feed>""".encode()


def _entry(
    *,
    title: str = "A Sample Paper",
    summary: str = "This is the summary.",
    arxiv_id: str = "2305.11288v2",
    authors: tuple[str, ...] = ("Alice Smith", "Bob Jones"),
) -> str:
    authors_xml = "\n".join(
        f"  <author><name>{name}</name></author>" for name in authors
    )
    return f"""<entry>
  <id>http://arxiv.org/abs/{arxiv_id}</id>
  <title>{title}</title>
  <summary>{summary}</summary>
{authors_xml}
</entry>"""


class TestCleanText:
    """Tests for ``clean_text``."""

    def test_replaces_newlines_with_space(self):
        assert clean_text("hello\nworld") == "hello world"

    def test_collapses_multiple_whitespace(self):
        assert clean_text("hello    world\t\there") == "hello world here"

    def test_strips_leading_and_trailing_whitespace(self):
        assert clean_text("   padded   ") == "padded"

    def test_combined_normalization(self):
        text = "  hello\n  world\n\nthere  "
        assert clean_text(text) == "hello world there"

    def test_empty_string_returns_empty(self):
        assert clean_text("") == ""

    def test_only_whitespace_returns_empty(self):
        assert clean_text("   \n\t  ") == ""


class TestCreateSessionWithRetries:
    """Tests for ``create_session_with_retries``."""

    def test_returns_session_instance(self):
        session = create_session_with_retries()
        assert isinstance(session, requests.Session)

    def test_mounts_https_and_http_adapters(self):
        session = create_session_with_retries()
        assert "https://" in session.adapters
        assert "http://" in session.adapters


class TestGetArxivPapers:
    """Tests for ``get_arxiv_papers``."""

    def _mock_response(self, content: bytes) -> MagicMock:
        response = MagicMock()
        response.content = content
        response.raise_for_status = MagicMock()
        return response

    def test_returns_papers_from_atom_feed(self):
        feed = _atom_feed(
            _entry(
                title="Paper One",
                summary="First abstract.",
                arxiv_id="2305.11288v2",
                authors=("Alice", "Bob"),
            )
        )
        with patch("src.arxiv.create_session_with_retries") as mock_factory:
            mock_session = MagicMock()
            mock_session.get.return_value = self._mock_response(feed)
            mock_factory.return_value = mock_session

            papers = get_arxiv_papers("test query")

        assert len(papers) == 1
        paper = papers[0]
        assert paper.title == "Paper One"
        assert paper.abstract == "First abstract."
        assert paper.author == "Alice, Bob"
        # arXiv id should have the version suffix stripped.
        assert str(paper.page) == "http://arxiv.org/abs/2305.11288"
        assert str(paper.pdf) == "http://arxiv.org/pdf/2305.11288.pdf"

    def test_multiple_entries_yield_multiple_papers(self):
        feed = _atom_feed(
            _entry(arxiv_id="1111.00001v1", title="One"),
            _entry(arxiv_id="2222.00002v3", title="Two"),
        )
        with patch("src.arxiv.create_session_with_retries") as mock_factory:
            mock_session = MagicMock()
            mock_session.get.return_value = self._mock_response(feed)
            mock_factory.return_value = mock_session

            papers = get_arxiv_papers("query")

        assert [p.title for p in papers] == ["One", "Two"]
        assert str(papers[0].page) == "http://arxiv.org/abs/1111.00001"
        assert str(papers[1].pdf) == "http://arxiv.org/pdf/2222.00002.pdf"

    def test_empty_feed_returns_empty_list(self):
        feed = _atom_feed()  # no <entry> elements
        with patch("src.arxiv.create_session_with_retries") as mock_factory:
            mock_session = MagicMock()
            mock_session.get.return_value = self._mock_response(feed)
            mock_factory.return_value = mock_session

            assert get_arxiv_papers("query") == []

    def test_normalizes_whitespace_in_title_and_summary(self):
        feed = _atom_feed(
            _entry(
                title="Title\n  with   newlines",
                summary="Summary\n\nwith     gaps",
            )
        )
        with patch("src.arxiv.create_session_with_retries") as mock_factory:
            mock_session = MagicMock()
            mock_session.get.return_value = self._mock_response(feed)
            mock_factory.return_value = mock_session

            papers = get_arxiv_papers("query")

        assert papers[0].title == "Title with newlines"
        assert papers[0].abstract == "Summary with gaps"

    def test_request_failure_raises_value_error(self):
        with patch("src.arxiv.create_session_with_retries") as mock_factory:
            mock_session = MagicMock()
            mock_session.get.side_effect = requests.exceptions.ConnectionError("boom")
            mock_factory.return_value = mock_session

            with pytest.raises(ValueError, match="Failed to get the response"):
                get_arxiv_papers("query")

    def test_http_error_raises_value_error(self):
        response = MagicMock()
        response.raise_for_status.side_effect = requests.exceptions.HTTPError("500")
        with patch("src.arxiv.create_session_with_retries") as mock_factory:
            mock_session = MagicMock()
            mock_session.get.return_value = response
            mock_factory.return_value = mock_session

            with pytest.raises(ValueError, match="Failed to get the response"):
                get_arxiv_papers("query")

    def test_query_and_max_results_are_in_url(self):
        feed = _atom_feed()
        with patch("src.arxiv.create_session_with_retries") as mock_factory:
            mock_session = MagicMock()
            mock_session.get.return_value = self._mock_response(feed)
            mock_factory.return_value = mock_session

            get_arxiv_papers("deep+learning", max_results=5)

        called_url = mock_session.get.call_args[0][0]
        assert "search_query=deep+learning" in called_url
        assert "max_results=5" in called_url
