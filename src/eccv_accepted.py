"""This is module to parse the ECCV specific accepted papers page.

The ECVA open access repository (``https://www.ecva.net/papers.php``, handled
by :mod:`src.eccv`) only publishes a year once the proceedings are out. Until
then the conference site lists the accepted papers with titles and authors but
without abstracts, so this module produces
:class:`~src.utils.PartialPaper` records that can be replaced by the full
records later.
"""

import logging
from typing import Final

import requests
from bs4 import BeautifulSoup
from bs4.element import Tag

from src.utils import PartialPaper

logger: Final = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

ROOT_URL: Final[str] = "https://eccv.ecva.net"

# The accepted papers table separates author names with U+22C5 DOT OPERATOR,
# unlike the CVPR accepted papers page which uses U+00B7 MIDDLE DOT.
AUTHOR_SEPARATOR: Final[str] = " ⋅ "

# Class of the "project page" anchor that may sit next to the title anchor in
# the same cell. It must not be mistaken for the title.
PROJECT_LINK_CLASS: Final[str] = "elc-project-link"


def get_papers(year: int) -> list[dict]:
    """Extract paper information from the accepted papers page.

    Args:
        year (int): The year of the conference.

    Returns:
        list[dict]: A list of serialized PartialPaper objects. The ``abstract``
            and ``pdf`` fields are always ``None`` because the accepted papers
            page does not publish them.

    """
    papers: Final[list[PartialPaper]] = get_partial_papers(year=year)

    return [paper.model_dump() for paper in papers]


def get_partial_papers(year: int) -> list[PartialPaper]:
    """Get partial papers from the ECCV accepted papers page.

    Rows that share a poster URL are duplicates of each other in the upstream
    HTML, so only the first occurrence of each paper is kept.

    Args:
        year (int): The year of the conference.

    Returns:
        list[PartialPaper]: A list of PartialPaper objects in page order.

    Raises:
        ValueError: If the paper table, a title or an author list is missing.

    """
    url: Final[str] = f"{ROOT_URL}/Conferences/{year}/AcceptedPapers"

    html: Final[str] = requests.get(url).text
    bs: Final = BeautifulSoup(html, "html.parser")

    # The page also contains a `table.gdpr-statement`, so the paper table is
    # selected by its own class instead of by document order.
    table = bs.select_one("table.elc-table")
    if not table:
        raise ValueError("Accepted papers table not found.")

    partial_papers: list[PartialPaper] = []
    seen_keys: set[tuple[str, ...]] = set()
    for row in table.find_all("tr"):
        # Skip the header row.
        if row.find("th"):
            continue

        title, page = _parse_title_cell(row)

        # Find author.
        author_tag = row.find("div", class_="indented")
        if not author_tag or not author_tag.find("i"):
            raise ValueError("Authors not found.")
        author = author_tag.find("i").text.strip()
        author = author.replace(AUTHOR_SEPARATOR, ", ")

        # Prefer the poster URL as the identity of a paper. Distinct papers may
        # share a title, so fall back to title and author when it is missing.
        key = (page,) if page else (title, author)
        if key in seen_keys:
            logger.info(f"Skipping duplicated row: {title}")
            continue
        seen_keys.add(key)

        partial_papers.append(
            PartialPaper(
                title=title,
                author=author,
                page=page,  # type: ignore[arg-type]
            )
        )

    return partial_papers


def _parse_title_cell(row: Tag) -> tuple[str, str | None]:
    """Return the title and the absolute poster URL of a table row.

    Args:
        row (Tag): A ``<tr>`` element of the accepted papers table.

    Returns:
        tuple[str, str | None]: The paper title and its poster page URL. The
            URL is ``None`` when the title anchor carries no ``href``.

    Raises:
        ValueError: If the row holds no title anchor.

    """
    title_tag = None
    for anchor in row.find_all("a"):
        if PROJECT_LINK_CLASS in (anchor.get("class") or []):
            continue
        title_tag = anchor
        break

    if not title_tag:
        raise ValueError("Title not found.")

    title = title_tag.text.strip()

    sub_page_url = title_tag.get("href")
    page = ROOT_URL + sub_page_url if sub_page_url else None

    return title, page


if __name__ == "__main__":
    papers = get_papers(year=2026)
    print(f"{len(papers)} papers found.")
