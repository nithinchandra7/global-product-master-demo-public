"""Reference Snowpark staging adapter; requires a configured sandbox session."""

import json
from typing import Any

from solution_labs.master import resolve
import re

def identifier(name: str) -> str:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
        raise ValueError("Invalid Snowflake identifier")
    return name


def stage(session: Any, database: str, schema: str, batch_id: str) -> dict[str, int]:
    namespace = f"{identifier(database)}.{identifier(schema)}"
    raw = [
        {key.lower(): value for key, value in row.as_dict().items()}
        for row in session.table(f"{namespace}.REGIONAL_SOURCE").limit(1001).collect()
    ]
    if len(raw) > 1000:
        raise ValueError("Reference adapter collection limit exceeded; use distributed blocking")
    history = session.table(f"{namespace}.STEWARD_DECISION").limit(10001).collect()
    if len(history) > 10000:
        raise ValueError("Decision history limit exceeded; select latest revisions in SQL")
    latest: dict[str, tuple[int, str]] = {}
    for row in history:
        pair, revision, decision = row["PAIR_ID"], int(row["DECISION_REVISION"]), row["DECISION"]
        if decision not in {"approve", "reject"}:
            raise ValueError("Unknown steward decision")
        previous = latest.get(pair)
        if previous and previous[0] == revision and previous[1] != decision:
            raise ValueError("Conflicting steward decisions at the same revision")
        if previous is None or revision > previous[0]:
            latest[pair] = revision, decision
    decisions = {pair: value[1] for pair, value in latest.items()}
    result = resolve(raw, decisions)
    normalized = [(batch_id, row["source_key"], json.dumps(row)) for row in result["records"]]
    pairs = [(batch_id, row["pair_id"], json.dumps(row)) for row in result["pairs"]]
    # Dedicated staging only. Batch idempotency/concurrent-load policy is required
    # before using this scaffold in production; final publication is separate DML.
    session.create_dataframe(
        normalized, schema=["BATCH_ID", "SOURCE_KEY", "RECORD_JSON"]
    ).write.mode("append").save_as_table(f"{namespace}.STAGED_NORMALIZED")
    session.create_dataframe(pairs, schema=["BATCH_ID", "PAIR_ID", "EVIDENCE_JSON"]).write.mode(
        "append"
    ).save_as_table(f"{namespace}.STAGED_PAIR")
    return {
        "records": len(normalized),
        "pairs": len(pairs),
        "quarantine": len(result["quarantine"]),
    }
