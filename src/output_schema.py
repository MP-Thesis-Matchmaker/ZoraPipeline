"""
The flat publication output contract — the primary deliverable of this
pipeline. Each line of data/zora_publications.jsonl matches this schema.

This is the SINGLE FILE you edit when the output shape needs to change.
The Pydantic model defines what goes out; the to_output() function maps
the internal normalized dict to that shape.

NOTE: This schema is owned by ZoraPipeline and is intentionally independent
of the main repo's contracts. Any mapping between this and the main repo's
ZoraRecord happens in an adapter on whichever side makes sense, not here.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from . import config


class ZoraPublication(BaseModel):
    """One ZORA publication. This is the atomic unit the RAG system works with."""

    # --- Identity (stable across harvests) ---
    handle: str = Field(description="Stable ZORA identifier, used for deduplication")
    doi: str | None = None

    # --- Text content (what gets embedded for RAG) ---
    title: str | None = None
    abstract: str | None = None

    # --- Metadata (for filtering + ranking) ---
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    publication_type: str | None = None
    keywords: list[str] = Field(
        default_factory=list,
        description="Subject keywords from dc.subject, for topic matching",
    )

    # --- Links (for display / citation) ---
    zora_url: str | None = None

    # --- Scope ---
    source_scope: str = config.FACULTY_SCOPE_UUID


def to_output(record: dict) -> dict:
    """Map internal normalized record → output shape.

    Edit this function to change what fields appear in the output.
    """
    return ZoraPublication(
        handle=record["handle"],
        title=record.get("title"),
        abstract=record.get("abstract"),
        authors=record.get("authors", []),
        year=record.get("year"),
        publication_type=record.get("type"),
        keywords=record.get("keywords", []),
        doi=record.get("doi"),
        zora_url=record.get("uri"),
    ).model_dump()


def validate_publications_jsonl(path: str) -> tuple[int, list[str]]:
    """
    Validate every line of zora_publications.jsonl against the schema.
    @return: (number of valid records, list of error strings for invalid ones)
    """
    import json

    valid_count = 0
    errors: list[str] = []

    with open(path, encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                ZoraPublication.model_validate(record)
                valid_count += 1
            except Exception as exc:  # noqa: BLE001 — collect every kind of failure
                errors.append(f"line {line_no}: {exc}")

    return valid_count, errors


if __name__ == "__main__":
    import sys

    target = sys.argv[1] if len(sys.argv) > 1 else config.PUBLICATIONS_PATH
    count, errs = validate_publications_jsonl(target)
    print(f"{count} valid records in {target}")
    if errs:
        print(f"{len(errs)} invalid records:")
        for e in errs[:20]:
            print(f"  {e}")
        sys.exit(1)
