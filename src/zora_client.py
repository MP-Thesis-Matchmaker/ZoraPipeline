"""
Thin wrapper around dspace_rest_client.DSpaceClient, scoped to the
Faculty of Economics community.

Auth: DSpaceClient reads a personal access token automatically at
construction time, in this order:
  1. the file path in the PERSONAL_API_TOKEN_FILE env var
  2. .dspace-personal-api-token.secret in the current working directory
  3. .dspace-personal-api-token.secret in the user's home directory
No manual header wiring is needed on our side — just make sure one of
those three is set before this module constructs the client.
"""
import logging
import os

from dspace_rest_client.client import DSpaceClient

from . import config

logger = logging.getLogger(__name__)


def get_client() -> DSpaceClient:
    """Construct and authenticate a DSpaceClient against the ZORA API."""
    endpoint = os.environ.get("DSPACE_API_ENDPOINT", config.DEFAULT_API_ENDPOINT)
    client = DSpaceClient(api_endpoint=endpoint)

    if client.api_token is None:
        raise RuntimeError(
            "No personal API token found. Set PERSONAL_API_TOKEN_FILE to a "
            "file containing the token, or place it at "
            "./.dspace-personal-api-token.secret"
        )

    authenticated = client.authenticate()
    if not authenticated:
        raise RuntimeError(
            "ZORA authentication failed with the provided token. "
            "Token may be expired or invalid — check the ZORA profile page."
        )

    logger.info("Authenticated against %s", endpoint)
    return client


def iter_faculty_items(client: DSpaceClient, since: str | None = None):
    """
    Yield every item in the Faculty of Economics scope.

    @param since: optional ISO date string. If given, only items accessioned
                   on or after this date are returned (incremental mode).
                   If None, every item in scope is returned (full mode).
    """
    query = None
    if since is not None:
        # Matches the range-query pattern Martin's email used for
        # dc.date.accessioned, e.g. dc.date.accessioned:[2025-01-01 TO *]
        query = f"dc.date.accessioned:[{since} TO *]"

    yield from client.search_objects_iter(
        scope=config.FACULTY_SCOPE_UUID,
        dso_type="item",
        query=query,
        sort="dc.date.accessioned,asc",
    )
