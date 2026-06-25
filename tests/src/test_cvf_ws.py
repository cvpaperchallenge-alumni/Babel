"""Tests for ``src.cvf_ws`` (CVPR workshops)."""

from unittest.mock import MagicMock, patch

import pytest

from src.cvf_ws import (
    get_paper_page_urls,
    get_papers,
    parse_paper_page,
    validate_conference,
)


# ---------- validate_conference ---------- #
class TestValidateConference:
    @pytest.mark.parametrize("year", [2018, 2019, 2020, 2021, 2022, 2023])
    def test_supported_years(self, year):
        assert validate_conference("cvprw", year) == f"CVPR{year}"

    @pytest.mark.parametrize("year", [2017, 2024, 1990, 3000])
    def test_out_of_range_raises(self, year):
        with pytest.raises(ValueError, match="CVPRWS conference is held"):
            validate_conference("cvprw", year)

    @pytest.mark.parametrize("conf", ["cvpr", "iccv", "CVPRW", "", "neurips"])
    def test_unknown_conference_raises(self, conf):
        with pytest.raises(ValueError, match="does not support the conference"):
            validate_conference(conf, 2023)


# ---------- parse_paper_page ---------- #
def _paper_html(
    *,
    title: str = "WS Title",
    author: str = "Alice, Bob",
    abstract: str = "A workshop paper.",
) -> str:
    return f"""<html><body>
<div id="papertitle">  {title}  </div>
<div id="authors"><b>  {author}  </b></div>
<div id="abstract">  {abstract}  </div>
</body></html>"""


class TestParsePaperPage:
    def test_extracts_fields_and_builds_pdf_url(self):
        url = (
            "https://openaccess.thecvf.com/content/CVPR2023W/AVA/html/"
            "Doe_Foo_CVPRW_2023_paper.html"
        )
        with patch("src.cvf_ws.requests.get") as mock_get:
            mock_get.return_value.text = _paper_html(title="Foo")
            paper = parse_paper_page(url)

        assert paper.title == "Foo"
        assert str(paper.page) == url
        assert str(paper.pdf) == (
            "https://openaccess.thecvf.com/content/CVPR2023W/AVA/papers/"
            "Doe_Foo_CVPRW_2023_paper.pdf"
        )

    def test_missing_tags_yield_empty_strings(self):
        url = (
            "https://openaccess.thecvf.com/content/CVPR2023W/AVA/html/"
            "Doe_Foo_CVPRW_2023_paper.html"
        )
        with patch("src.cvf_ws.requests.get") as mock_get:
            mock_get.return_value.text = "<html></html>"
            paper = parse_paper_page(url)

        assert paper.title == ""
        assert paper.author == ""
        assert paper.abstract == ""


# ---------- get_paper_page_urls ---------- #
class TestGetPaperPageUrlsModern:
    """2021–2023: workshop menu lists per-WS pages; each WS page lists papers."""

    def test_aggregates_papers_across_workshops(self):
        menu_html = """<html><div id="content">
        <a href="/CVPR2023_workshops/WS1">WS1</a>
        <a href="/CVPR2023_workshops/WS2">WS2</a>
        </div></html>"""
        ws1_html = """<html>
        <div class="ptitle"><a href="/content/CVPR2023W/WS1/html/A_paper.html">A</a></div>
        </html>"""
        ws2_html = """<html>
        <div class="ptitle"><a href="/content/CVPR2023W/WS2/html/B_paper.html">B</a></div>
        <div class="ptitle"><a href="/content/CVPR2023W/WS2/html/C_paper.html">C</a></div>
        </html>"""

        responses = [
            MagicMock(text=menu_html),
            MagicMock(text=ws1_html),
            MagicMock(text=ws2_html),
        ]
        with patch("src.cvf_ws.requests.get", side_effect=responses) as mock_get:
            urls = get_paper_page_urls("cvprw", 2023)

        assert mock_get.call_count == 3
        assert len(urls) == 3
        assert urls[0].endswith("A_paper.html")
        assert urls[-1].endswith("C_paper.html")


class TestGetPaperPageUrlsLegacy:
    """2018–2020: menu links are ``CVPR2020_w42.py``-style with a ``..`` artifact."""

    def test_strips_dotdot_artifact_and_removes_menu_self_link(self):
        # The menu page includes "../menu" (would resolve to a self-link) plus
        # per-WS .py files.
        menu_html = """<html><div id="content">
        <a href="W1.py">W1</a>
        <a href="W2.py">W2</a>
        <a href="../menu">Self</a>
        </div></html>"""
        ws_html_template = """<html>
        <div class="ptitle">
          <a href="../../content_CVPRW_2020/html/{name}_paper.html">{name}</a>
        </div>
        </html>"""

        responses = [
            MagicMock(text=menu_html),
            MagicMock(text=ws_html_template.format(name="A")),
            MagicMock(text=ws_html_template.format(name="B")),
        ]
        with patch("src.cvf_ws.requests.get", side_effect=responses) as mock_get:
            urls = get_paper_page_urls("cvprw", 2020)

        # Only 3 calls (menu + 2 workshops) because the "../menu" entry is removed.
        assert mock_get.call_count == 3
        # All ".." substrings should have been stripped from the resulting URLs.
        for u in urls:
            assert ".." not in u
        assert len(urls) == 2

    def test_validation_error_propagates(self):
        with pytest.raises(ValueError):
            get_paper_page_urls("cvprw", 1990)


# ---------- get_papers ---------- #
class TestGetPapers:
    def test_aggregates_pages_into_paper_dicts(self):
        url = (
            "https://openaccess.thecvf.com/content/CVPR2023W/AVA/html/"
            "Doe_Foo_CVPRW_2023_paper.html"
        )
        with (
            patch("src.cvf_ws.get_paper_page_urls", return_value=[url]),
            patch("src.cvf_ws.requests.get") as mock_get,
        ):
            mock_get.return_value.text = _paper_html(title="Foo")
            papers = get_papers("cvprw", 2023)

        assert len(papers) == 1
        assert papers[0]["title"] == "Foo"
        assert isinstance(papers[0], dict)
