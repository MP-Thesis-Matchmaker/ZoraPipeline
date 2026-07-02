from src import config
from src.normalize import normalize_item
from .fake_dso import FakeDSO


def test_normalize_single_author_with_orcid():
    dso = FakeDSO(
        handle="20.500.14742/1001",
        uuid="uuid-1",
        fields={
            config.FIELD_TITLE: ["Trade Policy and Growth"],
            config.FIELD_AUTHOR: ["Doe, Jane"],
            config.FIELD_ABSTRACT: ["This paper examines..."],
            config.FIELD_DATE_ISSUED: ["2025-03-01"],
            config.FIELD_TYPE: ["Journal Article"],
            "cris.virtual.orcid": ["https://orcid.org/0000-0002-1111-2222"],
        },
    )

    record = normalize_item(dso)

    assert record["title"] == "Trade Policy and Growth"
    assert record["authors"] == ["Doe, Jane"]
    assert record["author_orcid"] == "0000-0002-1111-2222"  # URL prefix stripped
    assert record["year"] == 2025
    assert record["handle"] == "20.500.14742/1001"


def test_normalize_missing_fields_do_not_crash():
    dso = FakeDSO(handle="h", uuid="u", fields={config.FIELD_TITLE: ["Only a title"]})

    record = normalize_item(dso)

    assert record["title"] == "Only a title"
    assert record["authors"] == []
    assert record["author_orcid"] is None
    assert record["abstract"] is None
    assert record["year"] is None
    assert record["keywords"] == []


def test_normalize_year_extracted_from_full_date():
    dso = FakeDSO(
        handle="h",
        uuid="u",
        fields={config.FIELD_DATE_ISSUED: ["2024-11-15T00:00:00Z"]},
    )

    record = normalize_item(dso)

    assert record["year"] == 2024


def test_orcid_url_prefix_stripped():
    """cris.virtual.orcid stores full URLs — we strip to bare ID."""
    dso = FakeDSO(
        handle="h",
        uuid="u",
        fields={"cris.virtual.orcid": ["https://orcid.org/0000-0003-3333-4444"]},
    )

    record = normalize_item(dso)

    assert record["author_orcid"] == "0000-0003-3333-4444"


def test_orcid_bare_id_preserved():
    """If a future field stores a bare ORCID (no URL), it's kept as-is."""
    dso = FakeDSO(
        handle="h",
        uuid="u",
        fields={"person.identifier.orcid": ["0000-0001-2222-3333"]},
    )

    record = normalize_item(dso)

    assert record["author_orcid"] == "0000-0001-2222-3333"


def test_keywords_merged_from_ddc_and_scopus():
    """Keywords come from dc.subject.ddc + uzh.scopus.subjects, merged."""
    dso = FakeDSO(
        handle="h",
        uuid="u",
        fields={
            config.FIELD_SUBJECT_DDC: ["330 Economics"],
            config.FIELD_SCOPUS_SUBJECTS: ["Economics and Econometrics"],
        },
    )

    record = normalize_item(dso)

    assert record["keywords"] == ["330 Economics", "Economics and Econometrics"]


def test_keywords_deduped_across_fields():
    """If the same value appears in multiple fields, it's kept once."""
    dso = FakeDSO(
        handle="h",
        uuid="u",
        fields={
            config.FIELD_SUBJECT_DDC: ["330 Economics"],
            config.FIELD_SUBJECT: ["330 Economics"],  # duplicate
        },
    )

    record = normalize_item(dso)

    assert record["keywords"] == ["330 Economics"]


def test_keywords_empty_when_no_subject_fields():
    dso = FakeDSO(
        handle="h",
        uuid="u",
        fields={config.FIELD_TITLE: ["A paper without keywords"]},
    )

    record = normalize_item(dso)

    assert record["keywords"] == []


def test_author_field_uses_uzh_namespace():
    """Confirm we read from uzh.contributor.author, not dc.contributor.author."""
    dso = FakeDSO(
        handle="h",
        uuid="u",
        fields={
            "uzh.contributor.author": ["Schmutzler, Armin"],
            "dc.contributor.author": ["WRONG — should not be read"],
        },
    )

    record = normalize_item(dso)

    assert record["authors"] == ["Schmutzler, Armin"]
