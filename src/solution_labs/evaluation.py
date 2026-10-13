"""Executed independent synthetic evaluation; never measures client outcomes."""

import hashlib
import os
import statistics
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

from .master import Master, pair_key, resolve
from .master import fixtures as master_fixtures

ROOT = Path(os.getenv("SOLUTION_DEMO_ROOT", Path.cwd())).resolve()


def fingerprint() -> str:
    digest = hashlib.sha256()
    for file in sorted((ROOT / "src/solution_labs").glob("*.py")):
        if file.name in {"evaluation.py"}:
            continue
        digest.update(file.name.encode())
        digest.update(file.read_bytes())
    return digest.hexdigest()


def evaluation(project: str) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(dir=ROOT / ".tools") as directory:
        root = Path(directory)
        engine = Master(root)

        def run(scenario: str) -> dict[str, Any]:
            state = engine.create("clean" if scenario in {"publication", "replay"} else "standard")
            if scenario in {"publication", "replay"}:
                state = engine.action(state["run_id"], "steward", state["revision"], "publish")
                if scenario == "replay":
                    state = engine.action(state["run_id"], "steward", state["revision"], "publish")
                passed = (
                    state["publish_version"] == 1 and len(state["publication"]["products"]) == 40
                )
            elif scenario == "cannot_link":
                raw = master_fixtures()[:3]
                decisions = {pair_key(raw[0]["source_key"], raw[2]["source_key"]): "reject"}
                result = resolve(raw, decisions)
                passed = max(map(len, result["groups"])) == 2
                state = result
            else:
                passed = (
                    bool(state["quarantine"])
                    and any(p["status"] == "review" for p in state["pairs"])
                    and any(p["status"] == "blocked" for p in state["pairs"])
                )
            return {"passed": passed, "output": state}

        scenarios = ["publication", "ambiguity_conflict", "cannot_link", "replay"]
        results = []
        for scenario in scenarios:
            times = []
            result = None
            for _ in range(10):
                start = time.perf_counter()
                result = run(scenario)
                times.append((time.perf_counter() - start) * 1000)
            assert result is not None
            results.append(
                {
                    "scenario": scenario,
                    "runs": 10,
                    "passed": result["passed"],
                    "p50_ms": round(statistics.median(times), 3),
                    "p95_ms": round(max(times), 3),
                    "output": result["output"],
                }
            )
    return {
        "project": project,
        "implementation_fingerprint": fingerprint(),
        "passed": all(r["passed"] for r in results),
        "environment": {
            "python": sys.version.split()[0],
            "backend": "SQLite",
            "cloud_verified": False,
        },
        "method": "Ten sequential fresh-workspace runs per case. Timing includes workspace creation and scenario execution; nearest-rank p95 is the maximum of ten. Local synthetic measurement only.",
        "scenarios": results,
    }
