"""
Group normalized publication records into per-researcher profiles.

Author identity is the genuinely hard part here, so this is explicit about
the limitation rather than quietly guessing: dc.contributor.author is a
repeatable free-text field. When an item has more than one author, there is
no reliable way from the search API response alone to know which specific
author an item-level ORCID hit belongs to. That would require matching each
metadata value's `authority` key (a Person entity UUID, only present if UZH
has entities/authority control switched on for this field) or a per-author
custom field positionally aligned with dc.contributor.author. Neither is
confirmed yet — check with scripts/inspect_fields.py once you have a token.

So, for now:
  - Single-author items: the item's ORCID (if present) is attached directly
    to that one author.
  - Multi-author items: the ORCID is kept at the publication level only
    (orcid_hint), not attributed to a specific co-author.

Grouping key precedence: ORCID match > exact normalized-name match. Name
matching alone cannot distinguish two different people who share a name —
this is a known, common limitation of author disambiguation, not something
this script claims to solve.
"""
from __future__ import annotations

import re
from typing import Iterable


def _normalize_name(name: str) -> str:
    """Collapse whitespace/case so 'Jane   Doe' and 'jane doe' merge."""
    return re.sub(r"\s+", " ", name.strip().lower())


def _researcher_key(orcid: str | None, name: str) -> str:
    return f"orcid:{orcid}" if orcid else f"name:{_normalize_name(name)}"


def build_researcher_profiles(publications: Iterable[dict]) -> dict[str, dict]:
    """
    @param publications: iterable of normalize.normalize_item() output dicts
    @return: dict keyed by researcher_key -> profile dict
    """
    profiles: dict[str, dict] = {}

    for pub in publications:
        authors = pub.get("authors") or []
        single_author_orcid = pub.get("author_orcid") if len(authors) == 1 else None

        for author_name in authors:
            if not author_name:
                continue
            orcid = single_author_orcid
            key = _researcher_key(orcid, author_name)

            profile = profiles.setdefault(
                key,
                {
                    "researcher_id": key,
                    "orcid": orcid,
                    "name": author_name,
                    "name_variants": set(),
                    "publications": [],
                },
            )
            profile["name_variants"].add(author_name)
            if orcid and not profile.get("orcid"):
                profile["orcid"] = orcid

            profile["publications"].append(
                {
                    "title": pub.get("title"),
                    "year": pub.get("year"),
                    "abstract": pub.get("abstract"),
                    "type": pub.get("type"),
                    "doi": pub.get("doi"),
                    "handle": pub.get("handle"),
                    "orcid_hint": pub.get("author_orcid") if len(authors) > 1 else None,
                }
            )

    for profile in profiles.values():
        profile["name_variants"] = sorted(profile["name_variants"])
        profile["publication_count"] = len(profile["publications"])

    return profiles


def merge_profiles(existing: dict[str, dict], new: dict[str, dict]) -> dict[str, dict]:
    """
    Merge freshly-harvested profiles into the existing researchers dataset
    (both keyed by researcher_id). Publications are appended and
    de-duplicated by handle; ORCID and name_variants are unioned rather
    than overwritten, so incremental runs never lose prior information.
    """
    merged = dict(existing)

    for key, new_profile in new.items():
        if key not in merged:
            merged[key] = new_profile
            continue

        existing_profile = merged[key]
        seen_handles = {p["handle"] for p in existing_profile["publications"]}
        for pub in new_profile["publications"]:
            if pub["handle"] not in seen_handles:
                existing_profile["publications"].append(pub)
                seen_handles.add(pub["handle"])

        existing_profile["name_variants"] = sorted(
            set(existing_profile["name_variants"]) | set(new_profile["name_variants"])
        )
        if not existing_profile.get("orcid") and new_profile.get("orcid"):
            existing_profile["orcid"] = new_profile["orcid"]

        existing_profile["publication_count"] = len(existing_profile["publications"])

    return merged
