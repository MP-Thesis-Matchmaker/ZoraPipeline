# ZoraPipeline

Harvests publication metadata from ZORA, scoped to the UZH Faculty of
Economics (community UUID `9e8a319a-6d8f-4882-bf2a-684e358e6fff`), and
outputs flat per-publication records at `data/zora_publications.jsonl` —
the primary input for the RAG retrieval and ranking layers.

Also produces `data/researchers.jsonl` (per-researcher profiles) as a
secondary debugging output.

Runs on a schedule via GitHub Actions with no manual involvement once set
up. Also fully usable as a standalone container outside this repo.

## First-time setup

1. **Add the secret.** Repo → Settings → Secrets and variables → Actions →
   New repository secret → name it `ZORA_API_KEY`, value = your ZORA
   personal access token.

2. **Verify the field-name assumptions against real data — do this before
   trusting anything else.** `src/config.py` assumes standard Dublin Core
   field names, but UZH's DSpace-CRIS install may extend or rename some of
   them (especially author-ORCID linkage). Run this once, locally, with
   your token:

   ```bash
   $env:PERSONAL_API_TOKEN_FILE = "token.secret"
   pip install -r requirements.txt
   python -m scripts.inspect_fields 5
   ```

   This prints every metadata field actually present on 5 real WWF
   records, checks it against what `config.py` assumes, and — importantly —
   checks whether `dc.contributor.author` entries carry a resolvable
   `authority` key (a Person entity UUID). It also checks whether
   `dc.subject` (keywords) is present on real records.

3. **Push to `main`.** This triggers `build-image.yml`, which publishes
   `ghcr.io/<owner>/<repo>:latest`. The scheduled harvest workflows pull
   this image rather than rebuilding from source on every run.

4. **Trigger a first full harvest manually** (Actions tab → "Full harvest
   (weekly rebuild)" → Run workflow). You can set a `since` date to limit
   scope (e.g. `2024-07-01` for ~2 years of data). For a smoke test, run
   locally with `--limit 5` first.

After that, `harvest-incremental.yml` (daily) and `harvest-full.yml`
(weekly) run unattended.

## Output format

Primary output: `data/zora_publications.jsonl` — one JSON object per line,
each representing a single ZORA publication:

```json
{
  "handle": "20.500.14742/1001",
  "doi": "10.1234/example",
  "title": "Trade Policy and Growth",
  "abstract": "This paper examines...",
  "authors": ["Doe, Jane"],
  "year": 2025,
  "publication_type": "Journal Article",
  "keywords": ["International Trade", "Growth Models"],
  "author_orcid": "0000-0002-1111-2222",
  "zora_url": "https://www.zora.uzh.ch/id/eprint/1001",
  "faculty": "Faculty of Economics",
  "source_scope": "9e8a319a-6d8f-4882-bf2a-684e358e6fff",
  "harvested_at": "2026-07-01T12:00:00+00:00"
}
```

To change the output shape, edit `src/output_schema.py` — it's the single
file that defines what goes into the JSONL.

## Why two harvest modes

`dc.date.accessioned` — the field the incremental query filters on —
records when a publication was *added* to ZORA, not when it was last
*edited*. A daily incremental pull will pick up new publications cheaply,
but it will never notice someone correcting a typo in an existing abstract,
because the accession date doesn't change on edit. The weekly full mode
rebuilds the output from scratch and is the only mode that correctly
reflects edits or removals.

## Known limitation: multi-author ORCID attribution

`dc.contributor.author` is a repeatable free-text field. When a
publication has more than one author, there's no reliable way — from the
search API response alone — to know which specific co-author an
item-level ORCID belongs to. See the docstring at the top of
`src/aggregate.py` for the full reasoning.

## Verification needed

The `dc.date.accessioned:[date TO *]` Solr range query (used by
incremental mode and the `--since` flag) has not been tested against the
live ZORA API. Run a manual smoke test before relying on it.

## Running locally

### Without Docker (fastest for development)

```powershell
# Create and activate a venv
python -m venv .venv
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Save your API key to a file (gitignored)
"your-zora-api-key" | Out-File -NoNewline token.secret

# Set the env var
$env:PERSONAL_API_TOKEN_FILE = "token.secret"

# Smoke test — fetch 5 records
python -m src.harvest --mode full --limit 5

# Full 2-year harvest
python -m src.harvest --mode full --since 2024-07-01
```

### With Docker

```bash
# Save token
echo "your-zora-api-key" > token.secret

# Build
docker build -t zora-harvester .

# Smoke test
docker run --rm \
  --user "$(id -u):$(id -g)" \
  -v "$(pwd)/data:/app/data" \
  -v "$(pwd)/token.secret:/app/token.secret:ro" \
  -e PERSONAL_API_TOKEN_FILE=/app/token.secret \
  zora-harvester --mode full --limit 5
```

### Running the published image from anywhere

```bash
docker pull ghcr.io/<owner>/<repo>:latest
docker run --rm \
  -v "$(pwd)/data:/app/data" \
  -v "/path/to/token.secret:/app/token.secret:ro" \
  -e PERSONAL_API_TOKEN_FILE=/app/token.secret \
  ghcr.io/<owner>/<repo>:latest --mode full --since 2024-07-01
```

## Running tests

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

## Repo layout

```
src/
  config.py           # every hardcoded constant — scope UUID, field names, paths
  zora_client.py      # thin wrapper around dspace_rest_client
  normalize.py        # raw DSpace item -> flat publication dict
  aggregate.py        # publications -> per-researcher profiles (secondary output)
  output_schema.py    # THE file to edit when output shape changes
  schema.py           # pydantic contract for researchers.jsonl (secondary)
  state.py            # incremental watermark (data/state.json)
  harvest.py          # orchestrates the above; the Docker ENTRYPOINT
scripts/
  inspect_fields.py   # one-off: diff real ZORA fields against config.py assumptions
schema/
  zora_publication.schema.json  # JSON Schema mirror, for non-Python consumers
  researcher.schema.json        # JSON Schema for secondary output
tests/                # no network needed — fixtures fake the DSpace object shape
data/
  zora_publications.jsonl  # PRIMARY deliverable — created by the first harvest
  researchers.jsonl        # secondary/debug — per-researcher profiles
  state.json               # incremental watermark
  raw/                     # per-run debug dumps, gitignored, kept as Actions artifacts
```

## Safety check

If a harvest run returns fewer total publications than
`MIN_RETENTION_RATIO` (default 50%) of the previous run's total, it aborts
without writing. A sudden drop like that is almost always an auth failure
or misconfigured scope returning an empty-but-200 response, not the
faculty genuinely losing half its publications overnight.
