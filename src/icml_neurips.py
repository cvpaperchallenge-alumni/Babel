"""For ICML and NeurIPS: Retrieve accepted paper metadata (title / authors / abstract / page / pdf).
Dependencies: openreview-py.
"""

from __future__ import annotations

import logging
from typing import Dict, Final, List

import openreview.api  # OpenReview Python client v2

logger: Final = logging.getLogger(__name__)


# ---------- Internal Utilities ---------- #
def _validate_conference(conference: str, year: int) -> str:
    """Construct and validate the VENUE_ID for the specified conference and year.
    Currently supports ICML and NeurIPS from 2020 onwards.

    Args:
        conference (str): The conference name.
        year (int): The year of the conference.

    Returns:
        str: The constructed VENUE_ID.

    Raises:
        ValueError: If the conference is not supported or the year is invalid.
    """
    conf = conference.lower()
    if conf in {"icml", "icml.cc"}:
        if year < 2020:
            raise ValueError("Please specify ICML for the year 2020 or later.")
        return f"ICML.cc/{year}/Conference"
    elif conf in {"neurips_openreview", "neurips.cc"}:
        if year < 2020:
            raise ValueError("Please specify NeurIPS for the year 2020 or later.")
        return f"NeurIPS.cc/{year}/Conference"
    raise ValueError(f"Unsupported conference: {conference}")


# ---------- Main Function ---------- #
def get_papers(conference: str, year: int) -> List[Dict[str, str]]:
    """Return metadata for accepted papers of the specified conference and year.

    Returns a list of dicts with keys: title, authors, abstract, page, pdf.

    Args:
        conference (str): The conference name.
        year (int): The year of the conference.

    Returns:
        List[Dict[str, str]]: A list of dictionaries containing paper metadata.

    Raises:
        ValueError: If the conference is not supported or the year is invalid.
    """
    venue_id = _validate_conference(conference, year)
    client = openreview.api.OpenReviewClient(baseurl="https://api2.openreview.net")

    # Retrieve accepted submissions by filtering on venueid, without using invitations
    logger.info(f"Querying accepted submissions with venueid='{venue_id}'")
    notes = client.get_all_notes(content={"venueid": venue_id})
    logger.info(f"Fetched {len(notes)} accepted submissions")

    papers: List[Dict[str, str]] = []
    for n in notes:
        c = n.content
        title = c.get("title")["value"]
        authors = c.get("authors")["value"]
        if isinstance(authors, list):
            authors = ", ".join(authors)
        abstract = c.get("abstract")["value"]
        page_url = f"https://openreview.net/forum?id={n.id}"
        pdf_url = f"https://openreview.net/pdf?id={n.id}"

        papers.append(
            {
                "title": title,
                "authors": authors,
                "abstract": abstract,
                "page": page_url,
                "pdf": pdf_url,
            }
        )
    return papers


# ---------- Example Usage ---------- #
if __name__ == "__main__":
    icml24 = get_papers("ICML", 2024)
    print(f"First paper metadata:\n{icml24[0]}")
    NeurIPS24 = get_papers("NeurIPS", 2024)
    print(f"First paper metadata:\n{NeurIPS24[0]}")
