"""Tests for ``src.eccv`` (ECCV via ecva.net)."""

from unittest.mock import patch

from src.eccv import get_paper_page_urls, get_papers, parse_paper_page


# ---------- get_paper_page_urls ---------- #
def _papers_index_html() -> str:
    """ECVA index page listing papers across multiple years."""
    return """<html><body>
    <dt class="ptitle"><a href="papers/eccv_2022/papers_ECCV/html/1_paper.php">P1</a></dt>
    <dt class="ptitle"><a href="papers/eccv_2022/papers_ECCV/html/2_paper.php">P2</a></dt>
    <dt class="ptitle"><a href="papers/eccv_2020/papers_ECCV/html/3_paper.php">P3</a></dt>
    <dt class="ptitle"><a href="papers/eccv_2018/papers_ECCV/html/4_paper.php">P4</a></dt>
    </body></html>"""


class TestGetPaperPageUrls:
    def test_filters_to_requested_year_only(self):
        with patch("src.eccv.requests.get") as mock_get:
            mock_get.return_value.text = _papers_index_html()
            urls = get_paper_page_urls(2022)

        assert len(urls) == 2
        for u in urls:
            assert "eccv_2022" in u
            assert u.startswith("https://www.ecva.net/")

    def test_unknown_year_returns_empty_list(self):
        with patch("src.eccv.requests.get") as mock_get:
            mock_get.return_value.text = _papers_index_html()
            assert get_paper_page_urls(2099) == []

    def test_ignores_links_without_href(self):
        html = """<html>
        <dt class="ptitle"><a>no href</a></dt>
        <dt class="ptitle"><a href="papers/eccv_2022/papers_ECCV/html/1_paper.php">P1</a></dt>
        </html>"""
        with patch("src.eccv.requests.get") as mock_get:
            mock_get.return_value.text = html
            urls = get_paper_page_urls(2022)

        assert len(urls) == 1
        assert urls[0].endswith("1_paper.php")


# ---------- parse_paper_page ---------- #
def _paper_html(
    *,
    title: str = "ECCV Paper",
    authors: str = "Alice; Bob; Carol",
    abstract: str = '"  We propose a method.  "',
    pdf_subpath: str = "../../../../papers/eccv_2022/papers_ECCV/papers/1_paper.pdf",
) -> str:
    return f"""<html><body>
<div id="papertitle">  {title}  </div>
<div id="authors">{authors}</div>
<div id="abstract">{abstract}</div>
<a href="{pdf_subpath}">pdf</a>
</body></html>"""


class TestParsePaperPage:
    def test_extracts_and_normalizes_fields(self):
        url = "https://www.ecva.net/papers/eccv_2022/papers_ECCV/html/1_paper.php"
        with patch("src.eccv.requests.get") as mock_get:
            mock_get.return_value.text = _paper_html(
                title="ECCV Paper",
                authors="Alice; Bob; Carol",
                abstract='"We propose a method."',
            )
            paper = parse_paper_page(url)

        assert paper.title == "ECCV Paper"
        # Semicolons are stripped.
        assert ";" not in paper.author
        assert paper.author == "Alice Bob Carol"
        # Surrounding double quotes are stripped from the abstract.
        assert paper.abstract == "We propose a method."
        assert str(paper.page) == url
        assert str(paper.pdf) == (
            "https://www.ecva.net/papers/eccv_2022/papers_ECCV/papers/1_paper.pdf"
        )

    def test_pdf_url_dotdot_prefix_removed(self):
        url = "https://www.ecva.net/papers/eccv_2020/papers_ECCV/html/x_paper.php"
        with patch("src.eccv.requests.get") as mock_get:
            mock_get.return_value.text = _paper_html(
                pdf_subpath="../../../../papers/eccv_2020/papers_ECCV/papers/x.pdf"
            )
            paper = parse_paper_page(url)

        assert str(paper.pdf).startswith("https://www.ecva.net/papers/eccv_2020/")
        assert "../" not in str(paper.pdf)


# ---------- get_papers ---------- #
class TestGetPapers:
    def test_returns_dicts_for_each_url(self):
        url = "https://www.ecva.net/papers/eccv_2022/papers_ECCV/html/1_paper.php"
        with (
            patch("src.eccv.get_paper_page_urls", return_value=[url]),
            patch("src.eccv.requests.get") as mock_get,
        ):
            mock_get.return_value.text = _paper_html()
            papers = get_papers(2022)

        assert len(papers) == 1
        assert isinstance(papers[0], dict)
        assert papers[0]["title"] == "ECCV Paper"
