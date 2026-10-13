import json
import sqlite3
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any


class ConflictError(ValueError):
    pass


class Store:
    def __init__(self, root: Path):
        self.root = root
        self.path = root / "runtime/solution-labs.sqlite"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS runs "
                "(id TEXT PRIMARY KEY,kind TEXT,owner TEXT,payload TEXT,revision INTEGER)"
            )

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def create(self, kind: str, owner: str, payload: dict[str, Any]) -> tuple[str, int]:
        key = uuid.uuid4().hex
        with self.connection() as connection:
            connection.execute(
                "INSERT INTO runs VALUES (?,?,?,?,1)", (key, kind, owner, json.dumps(payload))
            )
        return key, 1

    def load(self, key: str, kind: str, owner: str) -> tuple[dict[str, Any], int]:
        with self.connection() as connection:
            row = connection.execute(
                "SELECT * FROM runs WHERE id=? AND kind=? AND owner=?", (key, kind, owner)
            ).fetchone()
        if row is None:
            raise LookupError("Workspace not found for this simulated identity")
        return json.loads(row["payload"]), int(row["revision"])

    def save(self, key: str, payload: dict[str, Any], revision: int) -> int:
        with self.connection() as connection:
            result = connection.execute(
                "UPDATE runs SET payload=?,revision=revision+1 WHERE id=? AND revision=?",
                (json.dumps(payload), key, revision),
            )
            if result.rowcount != 1:
                raise ConflictError("Workspace changed; reload before applying the action")
        return revision + 1


class Trace:
    def __init__(self) -> None:
        self.start = time.perf_counter()
        self.stages: list[dict[str, Any]] = []

    @contextmanager
    def stage(self, component: str, label: str) -> Iterator[None]:
        start = time.perf_counter()
        yield
        self.stages.append(
            {
                "component": component,
                "label": label,
                "duration_ms": round((time.perf_counter() - start) * 1000, 3),
            }
        )

    def result(self) -> dict[str, Any]:
        return {
            "request_id": uuid.uuid4().hex,
            "stages": self.stages,
            "total_ms": round((time.perf_counter() - self.start) * 1000, 3),
        }
