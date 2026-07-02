from src.aggregate import build_researcher_profiles, merge_profiles


def _pub(handle, title, authors, orcid=None, year=2025):
    return {
        "handle": handle,
        "title": title,
        "authors": authors,
        "author_orcid": orcid,
        "abstract": "abstract text",
        "year": year,
        "type": "Journal Article",
        "doi": None,
        "uri": None,
        "keywords": [],
        "accessioned": "2026-01-01T00:00:00Z",
    }


def test_single_author_orcid_is_attributed_directly():
    pubs = [_pub("h1", "Paper A", ["Doe, Jane"], orcid="0000-0001-1111-1111")]

    profiles = build_researcher_profiles(pubs)

    assert len(profiles) == 1
    profile = next(iter(profiles.values()))
    assert profile["orcid"] == "0000-0001-1111-1111"
    assert profile["researcher_id"] == "orcid:0000-0001-1111-1111"
    assert profile["publication_count"] == 1


def test_multi_author_orcid_is_not_attributed_to_a_specific_coauthor():
    pubs = [_pub("h1", "Paper B", ["Doe, Jane", "Smith, John"], orcid="0000-0001-1111-1111")]

    profiles = build_researcher_profiles(pubs)

    # Neither co-author profile should claim the item-level ORCID as their own
    for profile in profiles.values():
        assert profile["orcid"] is None
        # but it's preserved as a hint on the publication itself
        assert profile["publications"][0]["orcid_hint"] == "0000-0001-1111-1111"

    assert len(profiles) == 2


def test_same_author_across_publications_merges_into_one_profile():
    pubs = [
        _pub("h1", "Paper A", ["Doe, Jane"], orcid="0000-0001-1111-1111"),
        _pub("h2", "Paper B", ["Doe, Jane"], orcid="0000-0001-1111-1111"),
    ]

    profiles = build_researcher_profiles(pubs)

    assert len(profiles) == 1
    profile = next(iter(profiles.values()))
    assert profile["publication_count"] == 2


def test_name_only_matching_when_no_orcid():
    pubs = [
        _pub("h1", "Paper A", ["Müller, Anna"]),
        _pub("h2", "Paper B", ["müller,  anna"]),  # different case/spacing
    ]

    profiles = build_researcher_profiles(pubs)

    assert len(profiles) == 1
    profile = next(iter(profiles.values()))
    assert profile["publication_count"] == 2
    assert len(profile["name_variants"]) == 2


def test_merge_profiles_deduplicates_by_handle():
    existing = build_researcher_profiles([_pub("h1", "Paper A", ["Doe, Jane"], orcid="0000-0001")])
    new = build_researcher_profiles([_pub("h1", "Paper A", ["Doe, Jane"], orcid="0000-0001")])

    merged = merge_profiles(existing, new)

    assert len(merged) == 1
    profile = next(iter(merged.values()))
    assert profile["publication_count"] == 1  # not duplicated


def test_merge_profiles_adds_new_publications_without_losing_old():
    existing = build_researcher_profiles([_pub("h1", "Paper A", ["Doe, Jane"], orcid="0000-0001")])
    new = build_researcher_profiles([_pub("h2", "Paper B", ["Doe, Jane"], orcid="0000-0001")])

    merged = merge_profiles(existing, new)

    assert len(merged) == 1
    profile = next(iter(merged.values()))
    assert profile["publication_count"] == 2
    handles = {p["handle"] for p in profile["publications"]}
    assert handles == {"h1", "h2"}
