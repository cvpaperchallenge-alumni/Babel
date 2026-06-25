"""Shared pytest fixtures for the Babel test suite."""

import nltk
import pytest


@pytest.fixture(scope="session", autouse=True)
def _ensure_nltk_corpora() -> None:
    """Make sure NLTK corpora used by the frequency pipeline are present.

    The production code calls ``nltk.download`` inside the functions, so on a
    fresh machine the first test run will fetch them; subsequent runs are no-ops
    because NLTK caches the corpora under ``~/nltk_data``.
    """
    for corpus in ("stopwords", "punkt", "punkt_tab", "wordnet"):
        nltk.download(corpus, quiet=True)
