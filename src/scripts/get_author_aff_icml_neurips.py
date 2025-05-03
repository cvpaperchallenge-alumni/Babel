import argparse
import json
import re
import time
from datetime import datetime
from typing import cast

import openreview
from dateutil import parser  # type: ignore[import-untyped]
from tqdm import tqdm

p = argparse.ArgumentParser(
    description="Script to retrieve author affiliation information for ICML and NeurIPS papers"
)
p.add_argument("--year", type=int, default=2024, help="Target year (e.g., 2024)")
p.add_argument(
    "--input",
    type=str,
    default="data/json/icml2024_papers.json",
    help="Path to the input JSON file",
)
p.add_argument(
    "--output",
    type=str,
    default=None,
    help="Path to the output JSON file (defaults to input file with _with_affiliations suffix)",
)
args = p.parse_args()

TARGET_YEAR = args.year
INPUT_FILE = args.input
OUTPUT_FILE = args.output or INPUT_FILE.replace(".json", "_with_affiliations.json")

client = openreview.api.OpenReviewClient(
    baseurl="https://api2.openreview.net",
    # Including username and password will relax rate limits
)


def _safe_date(obj: str | int | None, default: str = "1900-01-01") -> datetime:
    """Convert str/int/None to datetime; on failure, use default.

    Args:
        obj (str | int | None): The object to parse.
        default (str): Default date string to return on failure.

    Returns:
        datetime: The parsed date as a datetime object.
    """
    if obj is None or obj == "":
        obj = default
    if isinstance(obj, int):
        obj = str(obj)
    try:
        return cast(datetime, parser.parse(obj))
    except Exception:
        return cast(datetime, parser.parse(default))


def get_affiliations_for_year(history: list, year: int = TARGET_YEAR) -> list:
    """Return all affiliations held during the specified year.

    * If end is None / "" / "Present", treat as ongoing and assign 9999-12-31
    * start/end can be int or string
    * Remove duplicates and sort by start date (newest first)
    * If no entries match the year:
        1. Use ongoing affiliations
        2. If none, use entry with the most recent start date

    Args:
        history (list): Affiliation history entries.
        year (int): Target year to check for affiliations.

    Returns:
        list: Unique affiliations for the specified year.
    """
    candidates, ongoing = [], []

    for h in history:
        start = _safe_date(h.get("start"))
        end_field = h.get("end")

        # Normalize end field
        if end_field in (None, "Present", "present"):
            ongoing.append(h)
            end = datetime.max  # Equivalent to 9999-12-31
        else:
            end = _safe_date(end_field)

        if start.year <= year <= end.year:
            print("Entry matches target year")
            candidates.append(h)

    # If entries match the target year
    if candidates:
        candidates.sort(key=lambda h: _safe_date(h.get("start")), reverse=True)
        seen, ordered = set(), []
        for h in candidates:
            inst = h.get("institution", {}).get("name")
            if inst and inst not in seen:
                ordered.append(inst)
                seen.add(inst)
        return ordered

    # Fallback 1: ongoing affiliations
    if ongoing:
        ongoing.sort(key=lambda h: _safe_date(h.get("start")), reverse=True)
        return list(
            dict.fromkeys(
                h.get("institution", {}).get("name")
                for h in ongoing
                if h.get("institution", {}).get("name")
            )
        )

    # Fallback 2: most recent start date
    if history:
        print("Returning entry with latest start date")
        latest = max(history, key=lambda h: _safe_date(h.get("start")))
        inst = latest.get("institution", {}).get("name")
        return [inst] if inst else []

    return []


# Load JSON
with open(INPUT_FILE, encoding="utf-8") as f:
    papers = json.load(f)

pattern = re.compile(r"id=([A-Za-z0-9_-]+)")
updated = []

for paper in tqdm(papers):
    m = pattern.search(paper["page"])
    if not m:
        continue
    note = client.get_notes(id=m.group(1))[0]
    author_ids = note.content.get("authorids", {}).get("value") or note.content.get(
        "authorids"
    )

    details = []
    if author_ids:
        profiles = openreview.tools.get_profiles(client, author_ids)
        for prof in profiles:
            name = prof.get_preferred_name(pretty=True)
            history = prof.content.get("history", [])
            affiliation = get_affiliations_for_year(history)
            details.append({name: affiliation or None})
            time.sleep(0.1)
    else:
        # Fallback if authorids is missing
        for n in paper.get("authors", "").split(","):
            details.append({"name": n.strip(), "affiliation": None})

    paper_out = dict(paper, authors_affiliation=details)
    updated.append(paper_out)

# Save to a separate file
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(updated, f, ensure_ascii=False, indent=2)

print(f"✅ Completed: Updated {len(updated)} papers.")
