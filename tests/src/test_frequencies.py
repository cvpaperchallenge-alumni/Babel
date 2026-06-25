"""Tests for ``src.frequencies``."""

import pytest

from src.frequencies import get_ngrams, remove_stopwords, sort_frequency_dict


class TestRemoveStopwords:
    """Tests for ``remove_stopwords``."""

    def test_removes_default_english_stopwords(self):
        tokens = ["the", "model", "is", "a", "transformer"]
        result = remove_stopwords(tokens)
        # "the", "is", "a" are nltk English stopwords.
        assert result == ["model", "transformer"]

    def test_stopword_match_is_case_insensitive(self):
        tokens = ["The", "Model", "IS", "transformer"]
        result = remove_stopwords(tokens)
        assert result == ["Model", "transformer"]

    @pytest.mark.parametrize(
        "symbol",
        [
            "~",
            "`",
            "!",
            "@",
            "#",
            "$",
            "%",
            "^",
            "&",
            "*",
            "(",
            ")",
            "_",
            "+",
            "-",
            "=",
            "{",
            "}",
            "[",
            "]",
            "|",
            ":",
            ";",
            "<",
            ">",
            ",",
            ".",
            "...",
            "?",
            "/",
            "//",
            '"',
        ],
    )
    def test_removes_custom_symbol_stopwords(self, symbol):
        assert remove_stopwords(["valid", symbol]) == ["valid"]

    def test_removes_pure_number_tokens(self):
        tokens = ["paper", "2024", "model", "42"]
        assert remove_stopwords(tokens) == ["paper", "model"]

    def test_keeps_alphanumeric_tokens(self):
        # Tokens that contain digits but are not purely numeric should remain.
        tokens = ["v2", "covid19", "3d", "h264"]
        assert remove_stopwords(tokens) == tokens

    def test_strips_http_substring_to_empty_and_drops(self):
        tokens = ["paper", "http://example.com/foo", "model"]
        # The URL regex replaces the URL with "" then the empty token is dropped.
        assert remove_stopwords(tokens) == ["paper", "model"]

    def test_strips_www_and_github_prefixes(self):
        tokens = ["paper", "www.example.com", "github.com/foo", "model"]
        assert remove_stopwords(tokens) == ["paper", "model"]

    def test_strips_backslash_artifact(self):
        tokens = ["paper", "\\geq2", "model"]
        assert remove_stopwords(tokens) == ["paper", "model"]

    def test_drops_empty_and_whitespace_only_tokens(self):
        tokens = ["", "  ", "\t", "paper"]
        assert remove_stopwords(tokens) == ["paper"]

    def test_empty_input_returns_empty_list(self):
        assert remove_stopwords([]) == []

    def test_all_stopwords_returns_empty_list(self):
        assert remove_stopwords(["the", "and", "of", "a"]) == []


class TestGetNgrams:
    """Tests for ``get_ngrams``."""

    def test_unigram_counts(self):
        tokens = ["model", "model", "data", "model", "loss"]
        result = get_ngrams(tokens, 1)
        assert result == {"model": 3, "data": 1, "loss": 1}

    def test_bigram_counts(self):
        tokens = ["a", "b", "a", "b", "c"]
        result = get_ngrams(tokens, 2)
        assert result == {"a b": 2, "b a": 1, "b c": 1}

    def test_trigram_counts(self):
        tokens = ["a", "b", "c", "a", "b", "c"]
        result = get_ngrams(tokens, 3)
        assert result == {"a b c": 2, "b c a": 1, "c a b": 1}

    def test_n_larger_than_tokens_returns_empty(self):
        assert get_ngrams(["a", "b"], 3) == {}

    def test_n_equal_to_tokens_returns_single_ngram(self):
        assert get_ngrams(["a", "b", "c"], 3) == {"a b c": 1}

    def test_empty_tokens_returns_empty(self):
        assert get_ngrams([], 1) == {}


class TestSortFrequencyDict:
    """Tests for ``sort_frequency_dict``."""

    def test_sorts_by_value_descending(self):
        d = {"a": 1, "b": 5, "c": 3}
        sorted_d = sort_frequency_dict(d)
        assert list(sorted_d.items()) == [("b", 5), ("c", 3), ("a", 1)]

    def test_ties_broken_by_key_ascending(self):
        d = {"banana": 2, "apple": 2, "cherry": 2}
        sorted_d = sort_frequency_dict(d)
        assert list(sorted_d.keys()) == ["apple", "banana", "cherry"]

    def test_mixed_ordering(self):
        d = {"z": 1, "a": 3, "m": 3, "b": 1}
        sorted_d = sort_frequency_dict(d)
        assert list(sorted_d.items()) == [("a", 3), ("m", 3), ("b", 1), ("z", 1)]

    def test_empty_dict_returns_empty_dict(self):
        assert sort_frequency_dict({}) == {}

    def test_single_entry(self):
        assert sort_frequency_dict({"only": 7}) == {"only": 7}
