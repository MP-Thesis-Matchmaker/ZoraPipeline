"""
The researcher profile contract (secondary/debug output). This is the shape
of each line in data/researchers.jsonl — a per-researcher aggregation of
publications, useful for eyeballing whether researcher profiles look correct.

The PRIMARY deliverable is zora_publications.jsonl (see output_schema.py).
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class Publication(BaseModel):
    title: str | None = None
    year: int | None = None
    abstract: str | None = None
    type: str | None = None
    doi: str | None = None
    handle: str = Field(..., description="Stable ZORA identifier, used for de-duplication")
    orcid_hint: str | None = Field(
        default=None,
        description=(
            "ORCID found on this publication but not confidently attributed "
            "to this specific co-author. See aggregate.py docstring."
        ),
    )


class ResearcherProfile(BaseModel):
    researcher_id: str
    orcid: str | None = None
    name: str
    name_variants: list[str] = Field(default_factory=list)
    publications: list[Publication] = Field(default_factory=list)
    publication_count: int
    source_scope: str = "9e8a319a-6d8f-4882-bf2a-684e358e6fff"


def validate_researchers_jsonl(path: str) -> tuple[int, list[str]]:
    """
    Validate every line of a researchers.jsonl file against the schema.
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
                ResearcherProfile.model_validate(record)
                valid_count += 1
            except Exception as exc:  # noqa: BLE001 — we want to collect every kind of failure
                errors.append(f"line {line_no}: {exc}")

    return valid_count, errors


if __name__ == "__main__":
    import sys

    target = sys.argv[1] if len(sys.argv) > 1 else "data/researchers.jsonl"
    count, errs = validate_researchers_jsonl(target)
    print(f"{count} valid records in {target}")
    if errs:
        print(f"{len(errs)} invalid records:")
        for e in errs[:20]:
            print(f"  {e}")
        sys.exit(1)
