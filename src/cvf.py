"""This script generate json file which includes all papers information of the selected conference.
The code estimates Computer Vision Foundation(CVF) supported conferences such as CVPR and ICCV.

"""

import logging
from typing import Final

import requests
from bs4 import BeautifulSoup

from src.utils import Paper

logger: Final = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def get_papers(conference: str, year: int) -> list[dict]:
    """Extract paper information from a list of URLs.

    Args:
        conference (str): The conference name.
        year (int): The year of the conference.

    Returns:
        list[Paper]: A list of Paper objects.

    """
    urls: Final[list[str]] = get_paper_page_urls(conference=conference, year=year)

    papers: list[dict] = list()
    for i, url in enumerate(urls):
        logger.info(f"Processing {i+1}/{len(urls)}: {url}")
        paper = parse_paper_page(url)
        papers.append(paper.model_dump())

    return papers


def get_paper_page_urls(conference: str, year: int) -> list[str]:
    """Return a list of CVF page URL.

    The number of accepted papers is different for each conference:
        - CVPR 2023: 2,359 papers
        - ICCV 2023: 2,156 papers

    Args:
        conference (str): The conference name.
        year (int): The year of the conference.

    Returns:
        list[str]: A list of CVF page URL of each paper.
    """
    cvf_root_url: Final[str] = "https://openaccess.thecvf.com"
    conference_name: Final[str] = validate_conference(conference, year)

    # 発表日ごとの表示しか出来ない場合
    if int(year) <= 2020:
        cvf_all_paper_url = cvf_root_url + f"/{conference_name}"

        html = requests.get(cvf_all_paper_url).text
        bs = BeautifulSoup(html, "html.parser")
        parsed_tags = bs.select("#content a")
        day_cvf_url_list = [
            cvf_root_url + f"/{parsed_tag.get("href")}" for parsed_tag in parsed_tags
        ]

        all_day_cvf_url_list = []
        for day_cvf_url in day_cvf_url_list:
            html = requests.get(day_cvf_url).text
            bs = BeautifulSoup(html, "html.parser")
            parsed_tags = bs.select(".ptitle > a")
            all_day_cvf_url_list.extend(
                [
                    cvf_root_url + f"/{parsed_tag.get("href")}"
                    for parsed_tag in parsed_tags
                ]
            )
        return all_day_cvf_url_list

    else:
        cvf_all_paper_url = cvf_root_url + f"/{conference_name}?day=all"

        html = requests.get(cvf_all_paper_url).text
        bs = BeautifulSoup(html, "html.parser")
        parsed_tags = bs.select(".ptitle > a")
        return [cvf_root_url + parsed_tag.get("href") for parsed_tag in parsed_tags]


def validate_conference(conference: str, year: int) -> str:
    """Validate the user specified conference name and year and return
    the unique conference name with year.

    Args:
        conference (str): The conference name.
        year (int): The year of the conference.

    Returns:
        str: The unique conference name with year.
    """
    if conference == "cvpr":
        if year not in range(2013, 2027):
            raise ValueError(
                "CVPR conference is held from 2013 to 2026. \
                Please specify the year in the range."
            )
        return f"CVPR{year}"
    elif conference == "iccv":
        if year not in range(2013, 2026, 2):
            raise ValueError(
                "ICCV conference is held from 2013 to 2023 every two years. \
                Please specify the year in the range."
            )
        return f"ICCV{year}"
    else:
        raise ValueError(
            f"You specified the conference name as {conference}, \
            but our code does not support the conference."
        )


def parse_paper_page(page_url: str) -> Paper:
    """Parse a paper page and return Paper object.

    Args:
        page_url (str): The URL of the paper page. The page url structure is like
            https://openaccess.thecvf.com/content/<conference_name><year>/html/<family_name>_<paper_title>_<conference_name>_<year>_paper.html

    Returns:
        Paper: The Paper object which stores the paper information.
    """
    html: Final[str] = requests.get(page_url).text
    bs: Final = BeautifulSoup(html, "html.parser")

    title: Final[str] = (
        bs.select_one("#papertitle").text.strip()
        if bs.select_one("#papertitle") is not None
        else ""
    )
    author: Final[str] = (
        bs.select_one("#authors b").text.strip()
        if bs.select_one("#authors b") is not None
        else ""
    )
    abstract: Final[str] = (
        bs.select_one("#abstract").text.strip()
        if bs.select_one("#abstract") is not None
        else ""
    )
    page: Final[str] = page_url

    # conference_path is like: https://openaccess.thecvf.com/content/<conference_name><year>
    conference_path: Final[str] = page_url.rsplit("/", 2)[0]
    # paper_name is like: <family_name>_<paper_title>_<conference_name>_<year>_paper
    paper_name: Final[str] = page_url.rsplit("/", 1)[1].removesuffix(".html")
    pdf: Final[str] = conference_path + "/papers/" + paper_name + ".pdf"

    return Paper(
        title=title,
        author=author,
        abstract=abstract,
        page=page,  # type: ignore
        pdf=pdf,  # type: ignore
    )


if __name__ == "__main__":
    paper = parse_paper_page(
        "https://openaccess.thecvf.com/content/CVPR2023/html/Ci_GFPose_Learning_3D_Human_Pose_Prior_With_Gradient_Fields_CVPR_2023_paper.html"
    )
    print(paper.json())
