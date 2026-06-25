# Babel

[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Typing: mypy](https://img.shields.io/badge/typing-mypy-blue)](https://github.com/python/mypy)

Babel is a tool that scrapes accepted-paper metadata from major Computer Vision / AI conferences (CVPR, ICCV, ECCV, NeurIPS, ICML, and CVPR Workshops) and analyzes keyword trends across years. It is maintained by the [cvpaper.challenge](https://www.cvpaper.challenge) alumni community.

The pipeline has three stages:

1. **Scrape** conference pages → JSON of papers (`data/json/`).
2. **Analyze word frequency** (1〜N-gram) over titles (optionally + abstracts) → CSV (`outputs/raw_frequency/`, then filtered into `outputs/adjusted_frequency/`).
3. **Generate word clouds** from the JSON or filtered CSV → PNG (`outputs/wordcloud/`).

## Project Organization

```
    ├── .github/               <- GitHub settings (CI workflows, PR/issue templates).
    │
    ├── data/                  <- Stopword lists and scraped paper JSON.
    │   ├── json/              <- One JSON per conference-year (e.g. cvpr2025_papers.json).
    │   ├── stopwords.txt              <- Stopwords passed directly to WordCloud.
    │   ├── exact_match_stopwords.txt  <- N-grams removed by exact match in stage 2.
    │   └── partial_match_stopwords.txt<- Tokens removed by partial match in stage 2.
    │
    ├── environments/          <- Dockerfile and per-target docker-compose configs (cpu / ci).
    │
    ├── models/                <- Pretrained and serialized models (gitignored).
    │
    ├── notebooks/             <- Jupyter notebooks.
    │
    ├── outputs/               <- Analysis artifacts.
    │   ├── raw_frequency/     <- N-gram counts with default stopwords only.
    │   ├── adjusted_frequency/<- N-gram counts after custom stopword + min-count filtering.
    │   └── wordcloud/         <- Generated word cloud PNGs.
    │
    ├── src/                   <- Python source code.
    │   ├── cvf.py             <- CVPR / ICCV scraper (CVF Open Access).
    │   ├── cvf_ws.py          <- CVPR Workshops scraper (CVF Open Access).
    │   ├── eccv.py            <- ECCV scraper (ecva.net).
    │   ├── neurips.py         <- NeurIPS scraper (papers.nips.cc).
    │   ├── icml.py            <- ICML scraper (OpenReview API).
    │   ├── cvpr.py            <- CVPR fallback scraper using arXiv lookup
    │   │                          (for years where the official page lacks abstracts).
    │   ├── arxiv.py           <- arXiv API client (used by cvpr.py).
    │   ├── frequencies.py     <- Stopword removal, n-gram counting, sorting.
    │   ├── utils.py           <- Pydantic models (Paper / PartialPaper) and JSON helpers.
    │   └── scripts/           <- CLI entry points (see "Usage" below).
    │
    ├── tests/                 <- Test code.
    │
    ├── Makefile               <- Commands for lint / format / test automation.
    ├── poetry.lock            <- Auto-generated lock file (do not edit manually).
    ├── poetry.toml            <- Poetry configuration.
    ├── pyproject.toml         <- Main project configuration.
    └── README.md              <- This file.
```

## Supported conferences and years

| Conference | Scraper module       | Source                                              | Supported years (validator)    |
| ---------- | -------------------- | --------------------------------------------------- | ------------------------------ |
| CVPR       | `src/cvf.py`         | `openaccess.thecvf.com/CVPR{year}`                  | 2013–2025                      |
| ICCV       | `src/cvf.py`         | `openaccess.thecvf.com/ICCV{year}` (odd years)      | 2013, 2015, …, 2025            |
| ECCV       | `src/eccv.py`        | `ecva.net/papers.php` (filtered by `eccv_{year}`)   | no validator — pass any year   |
| NeurIPS    | `src/neurips.py`     | `papers.nips.cc/paper_files/paper/{year}`           | no enforced validator          |
| ICML       | `src/icml.py`        | OpenReview API (`ICML.cc/{year}/Conference`)        | 2020 onwards                   |
| CVPRW      | `src/cvf_ws.py`      | `openaccess.thecvf.com/CVPR{year}_workshops/menu`   | 2018–2023                      |

> [!NOTE]
> The current set of scraped JSON files lives in `data/json/`. `data/json/papers.md` records the source URL and accepted-paper count for each existing JSON so you can sanity-check a new scrape against the historical baseline.

## Prerequisites

- [Docker](https://www.docker.com/)
- [Docker Compose](https://github.com/docker/compose)

Local Python execution also works if you prefer, but the canonical environment is the Docker container described below — CI runs in the same image.

## Setting up the environment

```bash
# Build the container.
cd environments/cpu
docker compose build

# Start it and exec into a shell.
docker compose up -d
docker compose exec core bash

# Inside the container, install Python deps (skipped at build time by default).
poetry install
```

All commands in the rest of this README assume you are inside the container (or have an equivalent Poetry environment locally).

## Usage

### 1. Scrape a conference page

```bash
poetry run python3 src/scripts/scrape_conference_page.py \
    -c <conference> \
    -y <year> \
    -o ./data/json
```

`-c / --conference` accepts: `cvpr`, `iccv`, `eccv`, `neurips`, `icml`, `cvprw`.
The script writes `./data/json/{conference}{year}_papers.json` containing a list of objects like:

```json
{
    "title": "…",
    "author": "…",      // ICML uses "authors" (a list joined by ", ")
    "abstract": "…",
    "page": "https://…",
    "pdf": "https://…"
}
```

> [!IMPORTANT]
> **Per-venue quirks** — these are important when scraping a new year:
>
> - **CVPR / ICCV (`cvf.py`)** — for `year <= 2020`, the CVF site only paginates per day; for `year >= 2021`, the scraper hits `?day=all`. CVPR validator allows 2013–2025; ICCV is odd years only. **Bump the range in `validate_conference` before scraping a new year**, otherwise it raises immediately.
> - **CVPRW (`cvf_ws.py`)** — 2021–2023 share one HTML format; 2018–2020 use a different `*_w42.py` format. The branch in `get_paper_page_urls` reflects this. Validator range: 2018–2023.
> - **ECCV (`eccv.py`)** — `papers.php` lists every year on one page; filtering is by URL substring. No validator — an unknown year returns an empty list silently.
> - **NeurIPS (`neurips.py`)** — 2022 and 2023 need a different CSS selector than other years. `Abstract` in the URL slug is rewritten to `Paper` for the PDF link.
> - **ICML (`icml.py`)** — uses the OpenReview API v2, not HTML scraping. Output JSON uses the key `authors` (instead of `author`), which differs from the other scrapers — keep this in mind when feeding it into downstream stages.
> - **CVPR fallback (`cvpr.py`)** — when CVF Open Access does not yet have the abstracts, this module scrapes only title+authors from the official accepted-papers page and supplements abstract / page / pdf via arXiv search. It is currently *not* wired into `scrape_conference_page.py` (the relevant lines are commented out); call it directly:
>   ```bash
>   poetry run python3 -c "import pathlib; from src.cvpr import get_papers; get_papers(year=2024, output_path=pathlib.Path('./data/json/cvpr2024_papers.json'))"
>   ```
>   It checkpoints progress incrementally so a re-run resumes where it left off.

### 2. Compute word frequencies

**Single file:**

```bash
poetry run python3 src/scripts/analyze_word_frequency.py \
    -i ./data/json/cvpr2025_papers.json \
    -n 3            # max n-gram size (default 3)
    [--use-abstract]
```

Outputs land in `./outputs/raw_frequency/title_only/` or `…/title_and_abstract/`. Tokens are lowercased and lemmatized (NLTK `WordNetLemmatizer`, POS=NOUN) before counting; the NLTK default English stopword list plus a small set of punctuation/numbers is removed.

**All JSON files in `data/json/` at once** (runs both with and without `--use-abstract`):

```bash
poetry run python3 src/scripts/run_all_analyze_word_frequency.py
```

### 3. Filter the frequency CSVs

The raw output still contains noisy n-grams. This stage removes:

- n-grams that appear fewer than `--minimum-count` times (default 6),
- exact matches of any line in `data/exact_match_stopwords.txt`,
- n-grams containing any token from `data/partial_match_stopwords.txt`.

```bash
poetry run python3 src/scripts/adjust_frequency_analysis_result.py \
    -i ./outputs/raw_frequency/title_only/cvpr2025_papers_title_only_3gram.csv \
    -o ./outputs/adjusted_frequency \
    -m 6
```

**Batch all raw CSVs:**

```bash
poetry run python3 src/scripts/run_all_adjust_frequency_analysis_result.py
```

### 4. Generate word clouds

The generator accepts either input:

- **JSON paper file** — uses the `wordcloud` library's own tokenizer and the stopword set in `data/stopwords.txt`:
  ```bash
  poetry run python3 src/scripts/generate_wordcloud.py \
      -i ./data/json/cvpr2025_papers.json \
      -o ./outputs/wordcloud \
      --seed 42 \
      [--use-abstract]
  ```
- **Adjusted-frequency CSV** — renders directly from precomputed counts (recommended for reproducible output identical to the existing PNGs):
  ```bash
  poetry run python3 src/scripts/generate_wordcloud.py \
      -i ./outputs/adjusted_frequency/title_only/cvpr2025_papers_title_only_3gram_adjusted.csv \
      -o ./outputs/wordcloud \
      --seed 42
  ```

**Batch all adjusted CSVs:**

```bash
poetry run python3 src/scripts/run_all_generate_wordcloud.py
```

### End-to-end for a new conference-year

```bash
# 1. Make sure the validator allows the new year (edit src/{cvf,cvf_ws,icml,…}.py if needed).
# 2. Scrape:
poetry run python3 src/scripts/scrape_conference_page.py -c cvpr -y 2026

# 3. Record source URL + paper count in data/json/papers.md.

# 4. Re-run the analysis pipeline over every JSON:
poetry run python3 src/scripts/run_all_analyze_word_frequency.py
poetry run python3 src/scripts/run_all_adjust_frequency_analysis_result.py
poetry run python3 src/scripts/run_all_generate_wordcloud.py
```

## Development

```bash
make format        # ruff lint --fix + ruff format + mdformat
make lint          # ruff check + ruff format --check + mdformat --check + mypy
make test          # pytest with coverage
make test-all      # lint + test
```

CI (`.github/workflows/lint-and-test.yaml`) runs `make lint` and `make test` inside the same Docker image on every pull request.

## License

[MIT](./LICENSE)
