"""Tests for output_schema.py — the flat publication output contract."""
from src.output_schema import ZoraPublication, to_output


def _record(**overrides):
    """Build a normalized record dict (as produced by normalize.normalize_item)."""
    base = {
        "handle": "20.500.14742/1001",
        "uuid": "uuid-1",
        "title": "Trade Policy and Growth",
        "authors": ["Doe, Jane"],
        "author_orcid": "0000-0002-1111-2222",
        "abstract": "This paper examines...",
        "year": 2025,
        "type": "Journal Article",
        "doi": "10.1234/example",
        "uri": "https://www.zora.uzh.ch/id/eprint/1001",
        "keywords": ["International Trade", "Growth"],
        "accessioned": "2026-01-01T00:00:00Z",
    }
    base.update(overrides)
    return base


def test_to_output_maps_all_fields():
    record = _record()
    out = to_output(record, harvested_at="2026-07-01T12:00:00Z")

    assert out["handle"] == "20.500.14742/1001"
    assert out["title"] == "Trade Policy and Growth"
    assert out["abstract"] == "This paper examines..."
    assert out["authors"] == ["Doe, Jane"]
    assert out["year"] == 2025
    assert out["publication_type"] == "Journal Article"
    assert out["keywords"] == ["International Trade", "Growth"]
    assert out["author_orcid"] == "0000-0002-1111-2222"
    assert out["doi"] == "10.1234/example"
    assert out["zora_url"] == "https://www.zora.uzh.ch/id/eprint/1001"
    assert out["faculty"] == "Faculty of Economics"
    assert out["source_scope"] == "9e8a319a-6d8f-4882-bf2a-684e358e6fff"
    assert out["harvested_at"] == "2026-07-01T12:00:00Z"


def test_to_output_handles_missing_optional_fields():
    record = _record(
        title=None,
        abstract=None,
        authors=[],
        author_orcid=None,
        year=None,
        type=None,
        doi=None,
        uri=None,
        keywords=[],
    )
    out = to_output(record, harvested_at="2026-07-01T12:00:00Z")

    assert out["handle"] == "20.500.14742/1001"
    assert out["title"] is None
    assert out["abstract"] is None
    assert out["authors"] == []
    assert out["keywords"] == []
    assert out["faculty"] == "Faculty of Economics"


def test_to_output_does_not_include_internal_fields():
    """Fields like uuid and accessioned are internal — they should not leak into the output."""
    record = _record()
    out = to_output(record, harvested_at="2026-07-01T12:00:00Z")

    assert "uuid" not in out
    assert "accessioned" not in out
    assert "uri" not in out  # mapped to zora_url instead
    assert "type" not in out  # mapped to publication_type instead


def test_zora_publication_validates_valid_record():
    """Confirm a well-formed dict passes Pydantic validation."""
    record = _record()
    out = to_output(record, harvested_at="2026-07-01T12:00:00Z")

    validated = ZoraPublication.model_validate(out)
    assert validated.handle == "20.500.14742/1001"
    assert validated.faculty == "Faculty of Economics"


def test_faculty_is_always_faculty_of_economics():
    """Faculty is a hardcoded constant, not extracted from metadata."""
    record = _record()
    out = to_output(record, harvested_at="2026-07-01T12:00:00Z")

    assert out["faculty"] == "Faculty of Economics"
