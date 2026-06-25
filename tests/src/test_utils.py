"""Tests for ``src.utils``."""

import json

import pytest
from pydantic import ValidationError
from pydantic_core import Url

from src.utils import Paper, PartialPaper, serialize_for_json_dump


class TestPaper:
    """Tests for the ``Paper`` pydantic model."""

    def _payload(self, **overrides):
        base = {
            "title": "GFPose: Learning 3D Human Pose Prior With Gradient Fields",
            "author": "Hai Ci, Mingdong Wu, Wentao Zhu, Xiaoxuan Ma",
            "abstract": "We propose GFPose...",
            "page": "https://openaccess.thecvf.com/content/CVPR2023/html/Ci_GFPose_paper.html",
            "pdf": "https://openaccess.thecvf.com/content/CVPR2023/papers/Ci_GFPose_paper.pdf",
        }
        base.update(overrides)
        return base

    def test_accepts_valid_payload(self):
        paper = Paper(**self._payload())
        assert paper.title.startswith("GFPose")
        # HttpUrl normalizes to Url instance.
        assert isinstance(paper.page, Url)
        assert isinstance(paper.pdf, Url)
        assert str(paper.page).endswith("paper.html")

    @pytest.mark.parametrize("missing", ["title", "author", "abstract", "page", "pdf"])
    def test_missing_required_field_raises(self, missing):
        payload = self._payload()
        payload.pop(missing)
        with pytest.raises(ValidationError):
            Paper(**payload)

    @pytest.mark.parametrize(
        "field",
        ["page", "pdf"],
    )
    def test_invalid_url_raises(self, field):
        payload = self._payload(**{field: "not-a-url"})
        with pytest.raises(ValidationError):
            Paper(**payload)

    def test_non_http_scheme_rejected(self):
        # HttpUrl only accepts http/https.
        payload = self._payload(page="ftp://example.com/foo")
        with pytest.raises(ValidationError):
            Paper(**payload)


class TestPartialPaper:
    """Tests for the ``PartialPaper`` pydantic model."""

    def test_only_title_and_author_required(self):
        partial = PartialPaper(title="Some Title", author="Some Author")
        assert partial.title == "Some Title"
        assert partial.author == "Some Author"
        assert partial.abstract is None
        assert partial.page is None
        assert partial.pdf is None

    @pytest.mark.parametrize("missing", ["title", "author"])
    def test_missing_required_field_raises(self, missing):
        payload = {"title": "t", "author": "a"}
        payload.pop(missing)
        with pytest.raises(ValidationError):
            PartialPaper(**payload)

    def test_accepts_full_payload(self):
        partial = PartialPaper(
            title="t",
            author="a",
            abstract="abs",
            page="https://example.com/p",
            pdf="https://example.com/p.pdf",
        )
        assert partial.abstract == "abs"
        assert isinstance(partial.page, Url)
        assert isinstance(partial.pdf, Url)

    def test_explicit_none_keeps_optional_fields_none(self):
        partial = PartialPaper(
            title="t",
            author="a",
            abstract=None,
            page=None,
            pdf=None,
        )
        assert partial.page is None
        assert partial.pdf is None

    def test_invalid_url_in_optional_field_raises(self):
        with pytest.raises(ValidationError):
            PartialPaper(title="t", author="a", page="not-a-url")


class TestSerializeForJsonDump:
    """Tests for ``serialize_for_json_dump``."""

    def test_serializes_url_to_str(self):
        url = Url("https://example.com/foo")
        assert serialize_for_json_dump(url) == str(url)

    @pytest.mark.parametrize(
        "value",
        [123, 1.5, "plain string", b"bytes", object()],
    )
    def test_unsupported_type_raises_type_error(self, value):
        with pytest.raises(TypeError, match="not JSON serializable"):
            serialize_for_json_dump(value)

    def test_works_as_json_dumps_default(self):
        """End-to-end: a PartialPaper dump round-trips through ``json.dumps``."""
        paper = PartialPaper(
            title="t",
            author="a",
            page="https://example.com/p",
            pdf="https://example.com/p.pdf",
        )
        encoded = json.dumps(paper.model_dump(), default=serialize_for_json_dump)
        loaded = json.loads(encoded)
        assert loaded["page"] == "https://example.com/p"
        assert loaded["pdf"] == "https://example.com/p.pdf"
