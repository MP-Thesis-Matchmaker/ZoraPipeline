# ZoraPipeline

## What This Is

This pipeline is part of the **Thesis Matchmaker** project at the University of
Zurich. The goal: help students find the right supervisor for their thesis by
matching their research interests against real publication data.

When a student asks something like *"I want to do a master's thesis in NLP
related to retrieval-augmented generation"*, the system searches a vector
database of publications, groups results by researcher, and recommends
supervisors whose work best matches the query.

**This repository is the data layer.** It harvests publication metadata from
[ZORA](https://www.zora.uzh.ch) (UZH's institutional repository), scoped to the
Faculty of Economics, and outputs clean, structured records that feed into the
downstream retrieval and ranking pipeline.

## How Publications Are Used

1. **Harvest** — This pipeline fetches metadata (title, abstract, authors,
   department, keywords, etc.) for every publication in the Faculty of Economics.
2. **Index** — A separate component embeds each publication's title and abstract
   into a vector database (ChromaDB) for semantic search.
3. **Retrieve** — When a student queries the system, the vector database returns
   the most relevant publications, filtered by department or other metadata.
4. **Rank** — Publications are grouped by researcher to produce supervisor
   recommendations, with evidence links back to the original ZORA records.

## Output Format

The sole deliverable is `data/publications.jsonl` — one JSON object per line,
each representing a single ZORA publication:

```json
{
  "id": "20.500.14742/31317",
  "title": "Small scale entry versus acquisitions...",
  "abstract": "We consider a reduced form model...",
  "authors": ["Aydemir, Zava", "Schmutzler, Armin"],
  "uzh_authors": ["Schmutzler, Armin"],
  "author_authority_map": {
    "Aydemir, Zava": null,
    "Schmutzler, Armin": "f45b3ec1-cf2a-43ae-85d4-528afff07a40"
  },
  "year": 2008,
  "publication_type": "article",
  "department": "Department of Economics",
  "language": "eng",
  "keywords": ["330 Economics", "Economics and Econometrics"],
  "doi": "10.1016/j.jebo.2004.11.017",
  "url": "https://www.zora.uzh.ch/handle/20.500.14742/31317"
}
```

Key fields for the RAG system:
- **`title` + `abstract`** — embedded for semantic search (the main matching signal)
- **`department`** — enables filtering by department (e.g. "Department of Informatics")
- **`uzh_authors`** — only UZH-affiliated researchers, used to identify potential supervisors
- **`author_authority_map`** — maps each author to their CRIS Person UUID (or `null` for external co-authors)
- **`keywords`** — coarse-grained subject categories (DDC codes and Scopus areas)
- **`language`** — language code (e.g. `eng`, `deu`), useful for embedding quality

To change the output shape, edit `src/output_schema.py` — it's the single
file that defines what goes into the JSONL.

## First-time Setup

1. **Add the secret.** Repo → Settings → Secrets and variables → Actions →
   New repository secret → name it `ZORA_API_KEY`, value = your ZORA
   personal access token.

2. **Verify the field-name assumptions against real data — do this before
   trusting anything else.** `src/config.py` assumes standard Dublin Core
   field names, but UZH's DSpace-CRIS install may extend or rename some of
   them. Run this once, locally, with your token:

   ```bash
   $env:PERSONAL_API_TOKEN_FILE = "token.secret"
   pip install -r requirements.txt
   python -m scripts.inspect_fields 5
   ```

3. **Push to `main`.** This triggers `build-image.yml`, which publishes
   `ghcr.io/<owner>/<repo>:latest`. The scheduled harvest workflows pull
   this image rather than rebuilding from source on every run.

4. **Trigger a first full harvest manually** (Actions tab → "Full harvest
   (weekly rebuild)" → Run workflow). You can set a `since` date to limit
   scope (e.g. `2024-07-01`). For a smoke test, run locally with `--limit 5`
   first.

After that, `harvest-incremental.yml` (daily) and `harvest-full.yml`
(weekly) run unattended.

## Why Two Harvest Modes

`dc.date.accessioned` — the field the incremental query filters on —
records when a publication was *added* to ZORA, not when it was last
*edited*. A daily incremental pull will pick up new publications cheaply,
but it will never notice someone correcting a typo in an existing abstract.
The weekly full mode rebuilds the output from scratch and is the only mode
that correctly reflects edits or removals.

## MongoDB Ingestion (Optional)

To load the harvested publications into MongoDB:

```bash
pip install pymongo
python -m scripts.ingest_to_mongodb \
    --uri "mongodb://localhost:27017" \
    --db thesis_matchmaker \
    --collection publications
```

This is decoupled from the harvester — a MongoDB outage never breaks the
harvest pipeline. The script performs a bulk upsert keyed by publication `id`.

## Running Locally

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

## Running Tests

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

## Repo Layout

```
src/
  config.py           # every hardcoded constant — scope UUID, field names, paths,
                      #   department mapping (collection UUID → department name)
  zora_client.py      # thin wrapper around dspace_rest_client
  normalize.py        # raw DSpace item → flat publication dict
  output_schema.py    # THE file to edit when output shape changes
  state.py            # incremental watermark (data/state.json)
  harvest.py          # orchestrates the above; the Docker ENTRYPOINT
scripts/
  inspect_fields.py   # one-off: diff real ZORA fields against config.py assumptions
  ingest_to_mongodb.py # optional: load publications.jsonl into MongoDB
schema/
  zora_publication.schema.json  # JSON Schema mirror, for non-Python consumers
tests/                # no network needed — fixtures fake the DSpace object shape
data/
  publications.jsonl       # sole deliverable — created by the first harvest
  state.json               # incremental watermark
  raw/                     # per-run debug dumps, gitignored, kept as Actions artifacts
```

## Safety Check

If a harvest run returns fewer total publications than
`MIN_RETENTION_RATIO` (default 50%) of the previous run's total, it aborts
without writing. A sudden drop like that is almost always an auth failure
or misconfigured scope returning an empty-but-200 response, not the
faculty genuinely losing half its publications overnight.

## Known Limitation: Multi-author ORCID Attribution

`dc.contributor.author` is a repeatable free-text field. When a
publication has more than one author, there's no reliable way — from the
search API response alone — to know which specific co-author an
item-level ORCID belongs to. See the docstring at the top of
`src/normalize.py` for the full reasoning. The `uzh_authors` and
`author_authority_map` fields mitigate this by using the CRIS authority
key to reliably identify UZH-affiliated authors.
