"""
A minimal stand-in for dspace_rest_client's SimpleDSpaceObject, faithful to
its real metadata shape: get_metadata_values(field) returns a list of
{"value": ..., "language": ..., "authority": ..., "confidence": ...,
"place": ...} dicts, not plain strings. Tests build fixtures with this class
specifically so they'd catch a regression if normalize.py ever went back to
trusting the library's misleading docstring.
"""


class FakeDSO:
    def __init__(self, handle: str, uuid: str, fields: dict[str, list[str]]):
        self.handle = handle
        self.uuid = uuid
        self.metadata = {
            field: [
                {"value": v, "language": None, "authority": None, "confidence": -1, "place": i}
                for i, v in enumerate(values)
            ]
            for field, values in fields.items()
        }

    def get_metadata_values(self, field: str) -> list[dict]:
        return self.metadata.get(field, [])
