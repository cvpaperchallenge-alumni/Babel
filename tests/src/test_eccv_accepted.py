"""Tests for ``src.eccv_accepted`` (ECCV via the accepted-papers page).

The HTML fixtures below mirror the real structure of
https://eccv.ecva.net/Conferences/2026/AcceptedPapers as observed on 2026-09-04:

- The paper table is ``table.elc-table``; a second ``table.gdpr-statement``
  also exists on the page.
- The first row is a header row containing ``<th>``.
- Each body row holds the title anchor, an optional ``a.elc-project-link``,
  and ``div.indented > i`` with the author list.
- Author names are separated by U+22C5 DOT OPERATOR, **not** the U+00B7
  MIDDLE DOT used by the CVPR accepted-papers page.
- 18 rows are byte-identical duplicates of another row (same title, authors
  and poster href), so 2882 rows correspond to 2864 distinct papers.
"""

from unittest.mock import patch

import pytest

from src.eccv_accepted import get_papers, get_partial_papers
from src.utils import PartialPaper

# U+22C5 DOT OPERATOR, spelled as an escape so it is not confused with U+00B7.
DOT_OPERATOR = "⋅"


def _row(
    *,
    title: str,
    authors: str,
    href: str | None = "/virtual/2026/poster/1",
    project_link_first: bool = False,
    omit_title_anchor: bool = False,
    omit_authors: bool = False,
) -> str:
    """Build a single body ``<tr>`` of the accepted-papers table."""
    project = (
        '<a href="https://example.com/project" '
        'class="elc-project-link">Project Page</a>'
    )
    if omit_title_anchor:
        title_anchor = ""
    elif href is None:
        title_anchor = f"<a>{title}</a>"
    else:
        title_anchor = f'<a href="{href}">{title}</a>'

    anchors = (
        f"{project}{title_anchor}" if project_link_first else f"{title_anchor}{project}"
    )
    author_div = "" if omit_authors else f'<div class="indented"><i>{authors}</i></div>'

    return (
        "<tr>"
        f"<td>{anchors}{author_div}</td>"
        '<td class="elc-keywords">3D Graphics</td>'
        '<td class="elc-where"><span class="elc-where-part">ExHall</span></td>'
        "</tr>"
    )


def _accepted_papers_html(
    rows: list[str],
    *,
    gdpr_table_first: bool = False,
    include_paper_table: bool = True,
) -> str:
    """Wrap body rows in the page structure ``get_partial_papers`` expects."""
    header = (
        '<tr class="elc-head"><th>Title</th><th class="elc-keywords">Keywords</th>'
        '<th class="elc-where">Where and When</th></tr>'
    )
    paper_table = (
        '<table class="elc-table" id="event-list-2026-poster-nodates-filter-vslinks-table">'
        + header
        + "".join(rows)
        + "</table>"
        if include_paper_table
        else ""
    )
    gdpr_table = (
        '<table class="gdpr-statement"><tr><td>ECCV uses cookies.</td></tr></table>'
    )
    body = gdpr_table + paper_table if gdpr_table_first else paper_table + gdpr_table
    return f"<html><body>{body}</body></html>"


# ---------- get_partial_papers ---------- #
class TestGetPartialPapers:
    def test_url_is_constructed_with_year(self):
        with patch("src.eccv_accepted.requests.get") as mock_get:
            mock_get.return_value.text = _accepted_papers_html([])
            get_partial_papers(2026)

        called_url = mock_get.call_args[0][0]
        assert called_url == "https://eccv.ecva.net/Conferences/2026/AcceptedPapers"

    def test_parses_rows_into_partial_papers(self):
        html = _accepted_papers_html(
            [
                _row(
                    title="Paper One",
                    authors=f"Alice {DOT_OPERATOR} Bob",
                    href="/virtual/2026/poster/11",
                ),
                _row(
                    title="Paper Two",
                    authors=f"Carol {DOT_OPERATOR} Dave",
                    href="/virtual/2026/poster/22",
                ),
            ]
        )
        with patch("src.eccv_accepted.requests.get") as mock_get:
            mock_get.return_value.text = html
            papers = get_partial_papers(2026)

        assert len(papers) == 2
        assert all(isinstance(p, PartialPaper) for p in papers)
        assert papers[0].title == "Paper One"
        assert papers[1].title == "Paper Two"

    def test_dot_operator_separator_is_normalized_to_comma(self):
        html = _accepted_papers_html(
            [_row(title="P", authors=f"Alice {DOT_OPERATOR} Bob {DOT_OPERATOR} Carol")]
        )
        with patch("src.eccv_accepted.requests.get") as mock_get:
            mock_get.return_value.text = html
            papers = get_partial_papers(2026)

        assert papers[0].author == "Alice, Bob, Carol"
        assert DOT_OPERATOR not in papers[0].author

    def test_abstract_and_pdf_are_left_unset(self):
        html = _accepted_papers_html([_row(title="P", authors="Alice")])
        with patch("src.eccv_accepted.requests.get") as mock_get:
            mock_get.return_value.text = html
            papers = get_partial_papers(2026)

        assert papers[0].abstract is None
        assert papers[0].pdf is None

    def test_page_is_absolute_poster_url(self):
        html = _accepted_papers_html(
            [_row(title="P", authors="Alice", href="/virtual/2026/poster/3962")]
        )
        with patch("src.eccv_accepted.requests.get") as mock_get:
            mock_get.return_value.text = html
            papers = get_partial_papers(2026)

        assert str(papers[0].page) == "https://eccv.ecva.net/virtual/2026/poster/3962"

    def test_header_row_is_skipped(self):
        html = _accepted_papers_html([_row(title="Only Real Paper", authors="Alice")])
        with patch("src.eccv_accepted.requests.get") as mock_get:
            mock_get.return_value.text = html
            papers = get_partial_papers(2026)

        assert len(papers) == 1
        assert papers[0].title == "Only Real Paper"

    def test_gdpr_table_is_ignored_even_when_it_comes_first(self):
        html = _accepted_papers_html(
            [_row(title="Real Paper", authors="Alice")],
            gdpr_table_first=True,
        )
        with patch("src.eccv_accepted.requests.get") as mock_get:
            mock_get.return_value.text = html
            papers = get_partial_papers(2026)

        assert len(papers) == 1
        assert papers[0].title == "Real Paper"

    def test_duplicate_rows_are_deduplicated_by_poster_href(self):
        duplicated = _row(
            title="Dynamic World Generation Made Efficient",
            authors=f"Fengrui Tian {DOT_OPERATOR} Rene Vidal",
            href="/virtual/2026/poster/3754",
        )
        html = _accepted_papers_html(
            [
                _row(title="First", authors="Alice", href="/virtual/2026/poster/1"),
                duplicated,
                duplicated,
                _row(title="Last", authors="Bob", href="/virtual/2026/poster/2"),
            ]
        )
        with patch("src.eccv_accepted.requests.get") as mock_get:
            mock_get.return_value.text = html
            papers = get_partial_papers(2026)

        # 4 rows -> 3 papers, in first-occurrence order.
        assert [p.title for p in papers] == [
            "First",
            "Dynamic World Generation Made Efficient",
            "Last",
        ]

    def test_distinct_papers_sharing_a_title_are_both_kept(self):
        html = _accepted_papers_html(
            [
                _row(
                    title="Same Title", authors="Alice", href="/virtual/2026/poster/1"
                ),
                _row(title="Same Title", authors="Bob", href="/virtual/2026/poster/2"),
            ]
        )
        with patch("src.eccv_accepted.requests.get") as mock_get:
            mock_get.return_value.text = html
            papers = get_partial_papers(2026)

        assert len(papers) == 2
        assert [p.author for p in papers] == ["Alice", "Bob"]

    def test_project_link_is_not_mistaken_for_the_title(self):
        html = _accepted_papers_html(
            [_row(title="Real Title", authors="Alice", project_link_first=True)]
        )
        with patch("src.eccv_accepted.requests.get") as mock_get:
            mock_get.return_value.text = html
            papers = get_partial_papers(2026)

        assert papers[0].title == "Real Title"

    def test_title_anchor_without_href_keeps_paper_with_no_page(self):
        html = _accepted_papers_html(
            [_row(title="No Href Paper", authors="Alice", href=None)]
        )
        with patch("src.eccv_accepted.requests.get") as mock_get:
            mock_get.return_value.text = html
            papers = get_partial_papers(2026)

        assert len(papers) == 1
        assert papers[0].title == "No Href Paper"
        assert papers[0].page is None

    def test_hrefless_rows_are_deduplicated_by_title_and_author(self):
        row = _row(title="No Href Paper", authors="Alice", href=None)
        html = _accepted_papers_html([row, row])
        with patch("src.eccv_accepted.requests.get") as mock_get:
            mock_get.return_value.text = html
            papers = get_partial_papers(2026)

        assert len(papers) == 1

    def test_missing_paper_table_raises(self):
        html = _accepted_papers_html([], include_paper_table=False)
        with patch("src.eccv_accepted.requests.get") as mock_get:
            mock_get.return_value.text = html
            with pytest.raises(ValueError, match="Accepted papers table not found"):
                get_partial_papers(2026)

    def test_missing_title_raises(self):
        html = _accepted_papers_html(
            [_row(title="X", authors="Alice", omit_title_anchor=True)]
        )
        with patch("src.eccv_accepted.requests.get") as mock_get:
            mock_get.return_value.text = html
            with pytest.raises(ValueError, match="Title not found"):
                get_partial_papers(2026)

    def test_missing_authors_raises(self):
        html = _accepted_papers_html([_row(title="X", authors="", omit_authors=True)])
        with patch("src.eccv_accepted.requests.get") as mock_get:
            mock_get.return_value.text = html
            with pytest.raises(ValueError, match="Authors not found"):
                get_partial_papers(2026)


# ---------- get_papers ---------- #
class TestGetPapers:
    def test_returns_serializable_dicts(self):
        partial = PartialPaper(
            title="A Paper",
            author="Alice, Bob",
            page="https://eccv.ecva.net/virtual/2026/poster/1",
        )
        with patch(
            "src.eccv_accepted.get_partial_papers", return_value=[partial]
        ) as mock_partial:
            papers = get_papers(2026)

        mock_partial.assert_called_once_with(year=2026)
        assert len(papers) == 1
        assert isinstance(papers[0], dict)
        assert papers[0]["title"] == "A Paper"
        assert papers[0]["author"] == "Alice, Bob"
        assert papers[0]["abstract"] is None

    def test_empty_result_is_returned_as_empty_list(self):
        with patch("src.eccv_accepted.get_partial_papers", return_value=[]):
            assert get_papers(2026) == []
