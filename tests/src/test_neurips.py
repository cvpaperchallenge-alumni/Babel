"""Tests for ``src.neurips``."""

from unittest.mock import patch

import pytest

from src.neurips import (
    get_paper_page_urls,
    get_papers,
    parse_paper_page,
    validate_conference,
)


# ---------- validate_conference ---------- #
class TestValidateConference:
    """The function is dead code (not called from ``get_papers``), but is
    still exposed in the module and should behave consistently with its
    quirks documented (the conference key is the typo ``neurlips``).
    """

    @pytest.mark.parametrize("year", [2018, 2019, 2020, 2021, 2022])
    def test_supported_years_with_typo_key(self, year):
        # Note: the actual key in the source is "neurlips" (typo).
        assert validate_conference("neurlips", year) == f"NeurIPS{year}"

    @pytest.mark.parametrize("year", [2017, 2023, 2030])
    def test_out_of_range_raises(self, year):
        with pytest.raises(ValueError, match="NeurIPS conference is held"):
            validate_conference("neurlips", year)

    @pytest.mark.parametrize("conf", ["neurips", "NeurIPS", "cvpr", ""])
    def test_other_keys_rejected(self, conf):
        with pytest.raises(ValueError, match="does not support the conference"):
            validate_conference(conf, 2020)


# ---------- parse_paper_page ---------- #
def _paper_html(
    *,
    title: str = "NeurIPS Paper",
    author: str = "Alice, Bob",
    abstract: str = "A NeurIPS abstract.",
) -> str:
    return f"""<html><body>
<div class="container-fluid"><div class="col">
  <h4>  {title}  </h4>
  <p><i>  {author}  </i></p>
  <h4>Abstract</h4>
  <p>  {abstract}  </p>
</div></div>
</body></html>"""


class TestParsePaperPage:
    def test_rewrites_abstract_to_paper_in_pdf_url(self):
        url = (
            "https://papers.nips.cc/paper_files/paper/2023/hash/"
            "0001ca33ba34ce0351e4612b744b3936-Abstract-Conference.html"
        )
        with patch("src.neurips.requests.get") as mock_get:
            mock_get.return_value.text = _paper_html(title="Foo")
            paper = parse_paper_page(url)

        assert paper.title == "Foo"
        assert paper.author == "Alice, Bob"
        assert paper.abstract == "A NeurIPS abstract."
        assert str(paper.page) == url
        # /hash/ becomes /file/ in PDF URL, and "Abstract" becomes "Paper".
        assert str(paper.pdf) == (
            "https://papers.nips.cc/paper_files/paper/2023/file/"
            "0001ca33ba34ce0351e4612b744b3936-Paper-Conference.pdf"
        )

    def test_datasets_and_benchmarks_url_rewrites_correctly(self):
        url = (
            "https://papers.nips.cc/paper_files/paper/2023/hash/"
            "01726ae05d72ddba3ac784a5944fa1ef-Abstract-Datasets_and_Benchmarks.html"
        )
        with patch("src.neurips.requests.get") as mock_get:
            mock_get.return_value.text = _paper_html()
            paper = parse_paper_page(url)

        assert str(paper.pdf).endswith(
            "/file/01726ae05d72ddba3ac784a5944fa1ef-Paper-Datasets_and_Benchmarks.pdf"
        )

    def test_missing_tags_yield_empty_strings(self):
        url = (
            "https://papers.nips.cc/paper_files/paper/2023/hash/"
            "0001ca33ba34ce0351e4612b744b3936-Abstract-Conference.html"
        )
        with patch("src.neurips.requests.get") as mock_get:
            mock_get.return_value.text = "<html></html>"
            paper = parse_paper_page(url)

        assert paper.title == ""
        assert paper.author == ""
        assert paper.abstract == ""


# ---------- get_paper_page_urls ---------- #
class TestGetPaperPageUrls:
    def _list_html(self, hrefs: list[str], *, conference_class: bool) -> str:
        # The 2022/2023 selector path requires <li class="conference">.
        li_class = ' class="conference"' if conference_class else ""
        items = "\n".join(
            f'    <li{li_class}><a href="{href}">link</a></li>' for href in hrefs
        )
        return f"""<html><body>
<div class="container-fluid"><div class="col">
  <ul class="paper-list">
{items}
  </ul>
</div></div>
</body></html>"""

    @pytest.mark.parametrize("year", [2022, 2023])
    def test_2022_and_2023_use_conference_selector(self, year):
        html_with_class = self._list_html(
            ["/paper_files/paper/x/hash/a-Abstract-Conference.html"],
            conference_class=True,
        )
        html_without_class = self._list_html(
            ["/paper_files/paper/x/hash/a-Abstract-Conference.html"],
            conference_class=False,
        )

        with patch("src.neurips.requests.get") as mock_get:
            mock_get.return_value.text = html_with_class
            assert len(get_paper_page_urls("neurips", year)) == 1

        with patch("src.neurips.requests.get") as mock_get:
            mock_get.return_value.text = html_without_class
            # Without the conference class on <li>, the selector finds nothing.
            assert get_paper_page_urls("neurips", year) == []

    @pytest.mark.parametrize("year", [2019, 2020, 2021])
    def test_other_years_use_generic_li_selector(self, year):
        html = self._list_html(
            ["/paper_files/paper/y/hash/b-Abstract-Conference.html"],
            conference_class=False,
        )
        with patch("src.neurips.requests.get") as mock_get:
            mock_get.return_value.text = html
            urls = get_paper_page_urls("neurips", year)

        assert urls == [
            "https://papers.nips.cc/paper_files/paper/y/hash/b-Abstract-Conference.html"
        ]


# ---------- get_papers ---------- #
class TestGetPapers:
    def test_aggregates_pages_into_paper_dicts(self):
        url = (
            "https://papers.nips.cc/paper_files/paper/2023/hash/"
            "deadbeefcafe-Abstract-Conference.html"
        )
        with (
            patch("src.neurips.get_paper_page_urls", return_value=[url]),
            patch("src.neurips.requests.get") as mock_get,
        ):
            mock_get.return_value.text = _paper_html(title="Foo")
            papers = get_papers("neurips", 2023)

        assert len(papers) == 1
        assert papers[0]["title"] == "Foo"
        assert isinstance(papers[0], dict)
