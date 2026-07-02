"""
Central configuration for the ZORA Faculty of Economics harvester.

Every hardcoded value the pipeline depends on lives here, not buried in
logic files. If UZH changes a field name or the scope UUID, this is the
only file that needs to change.
"""
import os

# --- ZORA scope -------------------------------------------------------
# UUID of the "Faculty of Economics" community in ZORA.
# Confirmed against Martin Braendle's email example (there labelled "WWF" —
# Wirtschaftswissenschaftliche Fakultaet — same UUID, same community).
FACULTY_SCOPE_UUID = "9e8a319a-6d8f-4882-bf2a-684e358e6fff"

# --- Human-readable labels -------------------------------------------
# This pipeline is permanently scoped to one faculty (which contains 10
# departments/centers). This is NOT a field extracted from metadata — it's
# a constant stamped on every output record so consumers know what scope
# the data came from without looking up a UUID.
FACULTY = "Faculty of Economics"

# --- API endpoint -------------------------------------------------------
DEFAULT_API_ENDPOINT = "https://www.zora.uzh.ch/server/api"

# --- Dublin Core field names ---------------------------------------------
# These are the DSpace defaults. UZH's DSpace-CRIS install *may* extend or
# rename some of these (especially author-identifier fields). Before trusting
# this list, run `python -m scripts.inspect_fields` against a handful of real
# WWF records and diff the printed field names against what's below.
FIELD_TITLE = "dc.title"
FIELD_AUTHOR = "uzh.contributor.author"  # UZH custom — NOT dc.contributor.author
FIELD_ABSTRACT = "dc.description.abstract"
FIELD_DATE_ISSUED = "dc.date.issued"
FIELD_DATE_ACCESSIONED = "dc.date.accessioned"
FIELD_TYPE = "dc.type"
FIELD_DOI = "dc.identifier.doi"
FIELD_URI = "dc.identifier.uri"

# Keywords / subject fields — UZH doesn't use plain dc.subject. Instead:
# - dc.subject.ddc: Dewey Decimal classification, e.g. "330 Economics"
# - uzh.scopus.subjects: Scopus subject areas, e.g. "Economics and Econometrics"
# Both are useful for topic matching. We merge all available into one list.
FIELD_SUBJECT_DDC = "dc.subject.ddc"
FIELD_SCOPUS_SUBJECTS = "uzh.scopus.subjects"
FIELD_SUBJECT = "dc.subject"  # kept as fallback — may appear on some items

# Candidate fields for author ORCID — UZH uses cris.virtual.orcid with full
# URL format ("https://orcid.org/0000-..."), not a bare ID. The harvester
# tries each candidate in order and takes the first hit, stripping any URL
# prefix to store a bare ORCID.
FIELD_ORCID_CANDIDATES = [
    "cris.virtual.orcid",       # confirmed present on real WWF records
    "person.identifier.orcid",  # kept as fallback
    "dc.contributor.orcid",
    "dc.identifier.orcid",
]

# --- Paths -------------------------------------------------------------
DATA_DIR = os.environ.get("ZORA_DATA_DIR", "data")
RESEARCHERS_PATH = os.path.join(DATA_DIR, "researchers.jsonl")
PUBLICATIONS_PATH = os.path.join(DATA_DIR, "zora_publications.jsonl")
STATE_PATH = os.path.join(DATA_DIR, "state.json")
RAW_DIR = os.path.join(DATA_DIR, "raw")

# --- Safety thresholds ---------------------------------------------------
# If a harvest run returns dramatically fewer publications than the previous
# run recorded, something is probably wrong upstream (auth failure returning
# an empty-but-200 response, scope UUID typo, API outage) rather than the
# faculty genuinely losing most of its publications overnight. Abort instead
# of committing a destructive update.
MIN_RETENTION_RATIO = 0.5  # new total must be >= 50% of previous total
