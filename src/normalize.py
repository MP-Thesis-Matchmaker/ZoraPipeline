"""
Convert a raw SimpleDSpaceObject (as returned by search_objects_iter) into a
clean, flat publication dict.

Important: DSpaceObject.get_metadata_values(field) returns the RAW metadata
list straight from the DSpace JSON response — a list of dicts shaped like
{"value": "...", "language": ..., "authority": ..., "confidence": ...,
"place": ...} — despite what the library's own docstring claims ("simple
list of strings"). Every extraction below unwraps ["value"] explicitly.
Trusting the docstring here silently stores dicts where strings are
expected — this was caught by reading models.py directly, not assumed.
"""
from typing import Any

from . import config


def _values(dso: Any, field: str) -> list[str]:
    """Extract plain string values for a metadata field, dropping empties."""
    raw = dso.get_metadata_values(field)
    return [entry["value"] for entry in raw if entry.get("value")]


def _first_orcid(dso: Any) -> str | None:
    """Try each candidate ORCID field in order, return the first hit.

    UZH stores ORCIDs as full URLs (https://orcid.org/0000-...); we strip
    the prefix to store a bare ID.
    """
    for field in config.FIELD_ORCID_CANDIDATES:
        values = _values(dso, field)
        if values:
            raw = values[0]
            # Strip URL prefix if present
            if raw.startswith("https://orcid.org/"):
                return raw[len("https://orcid.org/"):]
            if raw.startswith("http://orcid.org/"):
                return raw[len("http://orcid.org/"):]
            return raw
    return None


def normalize_item(dso: Any) -> dict:
    """
    Turn one raw DSpace item into a flat publication record.

    Authors are kept as a list here — aggregation (grouping into researcher
    profiles) happens as a separate step, since one publication has many
    authors and one author has many publications.
    """
    titles = _values(dso, config.FIELD_TITLE)
    years = _values(dso, config.FIELD_DATE_ISSUED)

    return {
        "handle": dso.handle,
        "uuid": dso.uuid,
        "title": titles[0] if titles else None,
        "authors": _values(dso, config.FIELD_AUTHOR),
        "author_orcid": _first_orcid(dso),
        "abstract": next(iter(_values(dso, config.FIELD_ABSTRACT)), None),
        "year": _extract_year(years[0]) if years else None,
        "type": next(iter(_values(dso, config.FIELD_TYPE)), None),
        "doi": next(iter(_values(dso, config.FIELD_DOI)), None),
        "uri": next(iter(_values(dso, config.FIELD_URI)), None),
        "keywords": _collect_keywords(dso),
        "accessioned": next(
            iter(_values(dso, config.FIELD_DATE_ACCESSIONED)), None
        ),
    }


def _extract_year(date_str: str) -> int | None:
    """dc.date.issued can be a full date or just a year — pull the year out."""
    if not date_str:
        return None
    digits = date_str[:4]
    return int(digits) if digits.isdigit() else None


def _collect_keywords(dso: Any) -> list[str]:
    """Merge subject/keyword values from all available fields.

    UZH doesn't populate dc.subject (free-text keywords) on most items.
    Instead it has:
      - dc.subject.ddc: Dewey Decimal e.g. "330 Economics"
      - uzh.scopus.subjects: Scopus areas e.g. "Economics and Econometrics"
    We merge all three (deduped, order preserved) so the output has whatever
    subject metadata is available.
    """
    seen: set[str] = set()
    result: list[str] = []
    for field in (config.FIELD_SUBJECT_DDC, config.FIELD_SCOPUS_SUBJECTS, config.FIELD_SUBJECT):
        for val in _values(dso, field):
            if val not in seen:
                seen.add(val)
                result.append(val)
    return result
