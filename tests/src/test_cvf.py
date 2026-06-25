"""Tests for ``src.cvf`` (CVPR / ICCV via openaccess.thecvf.com)."""

from unittest.mock import MagicMock, patch

import pytest

from src.cvf import (
    get_paper_page_urls,
    get_papers,
    parse_paper_page,
    validate_conference,
)


# ---------- validate_conference ---------- #
class TestValidateConference:
    @pytest.mark.parametrize("year", [2013, 2020, 2024, 2025, 2026])
    def test_cvpr_supported_years(self, year):
        assert validate_conference("cvpr", year) == f"CVPR{year}"

    @pytest.mark.parametrize("year", [2012, 2027, 1999, 3000])
    def test_cvpr_out_of_range_raises(self, year):
        with pytest.raises(ValueError, match="CVPR conference is held"):
            validate_conference("cvpr", year)

    @pytest.mark.parametrize("year", [2013, 2015, 2021, 2023, 2025])
    def test_iccv_odd_years_supported(self, year):
        assert validate_conference("iccv", year) == f"ICCV{year}"

    @pytest.mark.parametrize("year", [2014, 2020, 2022, 2024])
    def test_iccv_even_years_rejected(self, year):
        with pytest.raises(ValueError, match="ICCV conference is held"):
            validate_conference("iccv", year)

    @pytest.mark.parametrize("year", [2011, 2027])
    def test_iccv_out_of_range_rejected(self, year):
        with pytest.raises(ValueError, match="ICCV conference is held"):
            validate_conference("iccv", year)

    @pytest.mark.parametrize("conf", ["eccv", "neurips", "CVPR", "ICCV", "", "foo"])
    def test_unknown_conference_raises(self, conf):
        with pytest.raises(ValueError, match="does not support the conference"):
            validate_conference(conf, 2024)


# ---------- parse_paper_page ---------- #
def _paper_html(
    *,
    title: str = "Sample Title",
    author: str = "Alice, Bob",
    abstract: str = "We propose a method.",
) -> str:
    return f"""<html><body>
<div id="papertitle">  {title}  </div>
<div id="authors"><b>  {author}  </b></div>
<div id="abstract">  {abstract}  </div>
</body></html>"""


class TestParsePaperPage:
    def test_extracts_fields_and_strips_whitespace(self):
        url = (
            "https://openaccess.thecvf.com/content/CVPR2023/html/"
            "Ci_GFPose_Learning_3D_Human_Pose_Prior_With_Gradient_Fields_CVPR_2023_paper.html"
        )
        with patch("src.cvf.requests.get") as mock_get:
            mock_get.return_value.text = _paper_html(
                title="GFPose", author="Hai Ci", abstract="We propose GFPose."
            )
            paper = parse_paper_page(url)

        assert paper.title == "GFPose"
        assert paper.author == "Hai Ci"
        assert paper.abstract == "We propose GFPose."
        assert str(paper.page) == url
        assert str(paper.pdf) == (
            "https://openaccess.thecvf.com/content/CVPR2023/papers/"
            "Ci_GFPose_Learning_3D_Human_Pose_Prior_With_Gradient_Fields_CVPR_2023_paper.pdf"
        )

    def test_missing_tags_yields_empty_strings_and_invalid_paper(self):
        """When the HTML is missing #papertitle/#authors b/#abstract, the
        extracted strings are empty. ``Paper`` then fails validation because
        URLs are still set, but title/author/abstract being empty strings
        is allowed by the model (they're typed ``str``, not constrained).
        """
        url = (
            "https://openaccess.thecvf.com/content/ICCV2023/html/"
            "Doe_Stub_ICCV_2023_paper.html"
        )
        with patch("src.cvf.requests.get") as mock_get:
            mock_get.return_value.text = "<html><body><p>no fields</p></body></html>"
            paper = parse_paper_page(url)

        assert paper.title == ""
        assert paper.author == ""
        assert paper.abstract == ""
        assert str(paper.page) == url


# ---------- get_paper_page_urls ---------- #
class TestGetPaperPageUrls:
    def test_year_after_2021_uses_single_page_query(self):
        """For year >= 2021 the scraper queries ?day=all once and reads .ptitle > a."""
        html = """<html>
        <a class="ptitle" href="ignored">wrong tag</a>
        <div class="ptitle"><a href="/content/CVPR2023/html/Foo_paper.html">Foo</a></div>
        <div class="ptitle"><a href="/content/CVPR2023/html/Bar_paper.html">Bar</a></div>
        </html>"""
        with patch("src.cvf.requests.get") as mock_get:
            mock_get.return_value.text = html
            urls = get_paper_page_urls("cvpr", 2023)

        mock_get.assert_called_once_with(
            "https://openaccess.thecvf.com/CVPR2023?day=all"
        )
        assert urls == [
            "https://openaccess.thecvf.com/content/CVPR2023/html/Foo_paper.html",
            "https://openaccess.thecvf.com/content/CVPR2023/html/Bar_paper.html",
        ]

    def test_year_2020_uses_two_step_per_day_crawl(self):
        """For year <= 2020 the scraper visits a day-list page first."""
        # First call: page lists day URLs in #content a.
        day_list_html = """<html><div id="content">
        <a href="CVPR2020?day=2020-06-16">Day 1</a>
        <a href="CVPR2020?day=2020-06-17">Day 2</a>
        </div></html>"""

        # Subsequent calls: each day page lists paper URLs in .ptitle > a.
        day_paper_html_1 = """<html>
        <div class="ptitle"><a href="/content_CVPR_2020/html/Foo_paper.html">Foo</a></div>
        </html>"""
        day_paper_html_2 = """<html>
        <div class="ptitle"><a href="/content_CVPR_2020/html/Bar_paper.html">Bar</a></div>
        <div class="ptitle"><a href="/content_CVPR_2020/html/Baz_paper.html">Baz</a></div>
        </html>"""

        responses = [
            MagicMock(text=day_list_html),
            MagicMock(text=day_paper_html_1),
            MagicMock(text=day_paper_html_2),
        ]
        with patch("src.cvf.requests.get", side_effect=responses) as mock_get:
            urls = get_paper_page_urls("cvpr", 2020)

        # 1 root call + one per day.
        assert mock_get.call_count == 3
        # All three paper URLs should be aggregated.
        assert len(urls) == 3
        assert urls[0].endswith("Foo_paper.html")
        assert urls[1].endswith("Bar_paper.html")
        assert urls[2].endswith("Baz_paper.html")

    def test_validation_error_propagates(self):
        with pytest.raises(ValueError):
            get_paper_page_urls("cvpr", 1900)


# ---------- get_papers ---------- #
class TestGetPapers:
    def test_aggregates_pages_into_paper_dicts(self):
        url1 = "https://openaccess.thecvf.com/content/CVPR2023/html/Ci_paper.html"
        url2 = "https://openaccess.thecvf.com/content/CVPR2023/html/Doe_paper.html"
        with (
            patch("src.cvf.get_paper_page_urls", return_value=[url1, url2]),
            patch("src.cvf.requests.get") as mock_get,
        ):
            mock_get.side_effect = [
                MagicMock(text=_paper_html(title="Paper 1")),
                MagicMock(text=_paper_html(title="Paper 2")),
            ]
            papers = get_papers("cvpr", 2023)

        assert len(papers) == 2
        assert papers[0]["title"] == "Paper 1"
        assert papers[1]["title"] == "Paper 2"
        # Each entry is a dict (model_dump output), not a Paper instance.
        assert isinstance(papers[0], dict)
