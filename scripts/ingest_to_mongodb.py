"""
Ingest publications.jsonl into a MongoDB collection.

Decoupled from the harvester — reads the JSONL output and performs a bulk
upsert. A MongoDB outage never breaks the harvest pipeline.

Usage:
    python -m scripts.ingest_to_mongodb \\
        --uri "mongodb://localhost:27017" \\
        --db thesis_matchmaker \\
        --collection publications

Requires: pymongo  (pip install pymongo)
"""
from __future__ import annotations

import argparse
import json
import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def load_jsonl(path: str) -> list[dict]:
    """Read a JSONL file and return a list of dicts."""
    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def ingest(uri: str, db_name: str, collection_name: str, records: list[dict]) -> int:
    """Bulk upsert records into MongoDB, keyed by 'id'. Returns upserted count."""
    try:
        from pymongo import MongoClient, ReplaceOne
    except ImportError:
        logger.error(
            "pymongo is not installed. Run: pip install pymongo"
        )
        sys.exit(1)

    client = MongoClient(uri)
    db = client[db_name]
    collection = db[collection_name]

    operations = [
        ReplaceOne({"id": record["id"]}, record, upsert=True)
        for record in records
    ]

    if not operations:
        logger.info("No records to ingest.")
        return 0

    result = collection.bulk_write(operations)
    return result.upserted_count + result.modified_count


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--uri",
        default="mongodb://localhost:27017",
        help="MongoDB connection URI (default: mongodb://localhost:27017)",
    )
    parser.add_argument(
        "--db",
        default="thesis_matchmaker",
        help="Database name (default: thesis_matchmaker)",
    )
    parser.add_argument(
        "--collection",
        default="publications",
        help="Collection name (default: publications)",
    )
    parser.add_argument(
        "--input",
        default="data/publications.jsonl",
        help="Path to the JSONL file to ingest (default: data/publications.jsonl)",
    )
    args = parser.parse_args()

    logger.info("Loading records from %s", args.input)
    records = load_jsonl(args.input)
    logger.info("Loaded %d records", len(records))

    logger.info("Ingesting into %s/%s at %s", args.db, args.collection, args.uri)
    count = ingest(args.uri, args.db, args.collection, records)
    logger.info("Done. %d records upserted/modified.", count)


if __name__ == "__main__":
    main()
