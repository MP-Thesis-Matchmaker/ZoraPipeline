# ZoraPipeline

> **Note**: This repository has been refactored and is intended to be merged into `RAG-Thesis-Matchmaker` as a sub-package. 
> 
> See `docs/zora-harvester.md` for complete documentation on the ZORA Harvester module.

## What is this?
This is the data ingestion pipeline for fetching publication metadata from [ZORA](https://www.zora.uzh.ch) (Zurich Open Repository and Archive). It acts as the data source for the RAG-Thesis-Matchmaker application.

## Quick Start (Local)

1. Set your ZORA API token:
   ```bash
   export PERSONAL_API_TOKEN_FILE=/path/to/your/token.secret
   ```
2. Install dependencies:
   ```bash
   pip install -e ".[dev]"
   ```
3. Run a quick smoke test harvest (fetches 5 records):
   ```bash
   python -m thesis_matchmaker.zora.harvest --mode full --limit 5
   ```

For more details on running the scheduler, using Docker, or configuring GitHub Actions, see [docs/zora-harvester.md](docs/zora-harvester.md).
