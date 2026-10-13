"""Product identity resolution with explicit constraints and steward decisions."""

import hashlib
import itertools
import json
import re
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from .common import ConflictError, Store, Trace

VERSION = "master-rules-1.0"


def fixtures() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index in range(40):
        for region, season in [
            ("NA", "All-Season"),
            ("EMEA", "Ganzjahresreifen"),
            ("APAC", "四季"),
        ]:
            rows.append(
                {
                    "source_key": f"{region}-{index:03}",
                    "region": region,
                    "manufacturer": "Aster Mobility",
                    "part_number": f"AX-{index:03}",
                    "description": f"Touring Line {index:03}",
                    "size": ["225/55R17", "205/55R16", "215/60R17", "235/45R18"][index % 4],
                    "load_index": 90 + index % 20,
                    "speed": "H" if index % 2 else "V",
                    "season": season,
                    "truth_id": f"F{index:03}",
                }
            )
    rows[4]["part_number"] = ""
    rows[4]["description"] = "Touringline 001"
    rows.append({**rows[0], "source_key": "NA-CONFLICT", "size": "255/55R17"})
    rows.append({**rows[1], "source_key": "EMEA-INVALID", "load_index": None})
    return rows


def normalize(row: dict[str, Any]) -> dict[str, Any]:
    season = {"allseason": "all-season", "ganzjahresreifen": "all-season", "四季": "all-season"}

    def cleaned(value: Any) -> str:
        return "" if value is None else re.sub(r"[^a-z0-9]", "", str(value).lower())

    load = row.get("load_index")
    if (
        isinstance(load, bool)
        or not isinstance(load, (int, str))
        or not re.fullmatch(r"\d{2,3}", str(load))
    ):
        raise ValueError("Missing/invalid load index")
    load = int(load)
    if not 75 <= load <= 130:
        raise ValueError("Missing/invalid load index")
    if not cleaned(row.get("manufacturer")):
        raise ValueError("Missing manufacturer identity")
    source = row.get("source_key")
    if (
        row.get("region") not in {"NA", "EMEA", "APAC"}
        or not isinstance(source, str)
        or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", source)
    ):
        raise ValueError("Invalid regional source identity")
    if not re.fullmatch(r"\d{3}/\d{2}R\d{2}", str(row.get("size", ""))):
        raise ValueError("Invalid tire size")
    if row.get("speed") not in {"H", "V", "W", "Y"}:
        raise ValueError("Unknown speed symbol")
    raw_season = str(row.get("season", ""))
    canonical_season = season.get(cleaned(raw_season)) or season.get(raw_season)
    if canonical_season is None:
        raise ValueError("Unknown regional season taxonomy")
    return {key: value for key, value in row.items() if key != "truth_id"} | {
        "manufacturer": cleaned(row["manufacturer"]),
        "part_number": cleaned(row.get("part_number")),
        "description_norm": cleaned(row.get("description")),
        "load_index": load,
        "season": canonical_season,
    }


def compatible(left: dict[str, Any], right: dict[str, Any]) -> bool:
    return all(
        left[key] == right[key] for key in ("manufacturer", "size", "load_index", "speed", "season")
    )


def pair_key(left: str, right: str) -> str:
    return "::".join(sorted((left, right)))


def resolve(raw: list[dict[str, Any]], decisions: dict[str, str]) -> dict[str, Any]:
    if len(raw) > 1000:
        raise ValueError("Local batch limit exceeded; use distributed blocking")
    records: list[dict[str, Any]] = []
    quarantine = []
    counts = Counter(row["source_key"] for row in raw if isinstance(row.get("source_key"), str))
    for row in raw:
        try:
            if counts.get(row.get("source_key"), 0) > 1:
                raise ValueError("Duplicate source identity")
            records.append(normalize(row))
        except (ValueError, KeyError, TypeError) as error:
            quarantine.append({"source_key": row.get("source_key"), "reason": str(error)})
    pairs: list[dict[str, Any]] = []
    buckets: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    parts: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in records:
        bucket = tuple(row[k] for k in ("manufacturer", "size", "load_index", "speed", "season"))
        buckets.setdefault(bucket, []).append(row)
        if row["part_number"]:
            parts.setdefault((row["manufacturer"], row["part_number"]), []).append(row)
    candidates: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {}
    for members in list(buckets.values()) + list(parts.values()):
        if len(members) > 100:
            raise ValueError("Candidate bucket is too broad; refine the blocking contract")
        for left, right in itertools.combinations(members, 2):
            candidates[pair_key(left["source_key"], right["source_key"])] = left, right
    for left, right in candidates.values():
        same_part = bool(left["part_number"]) and left["part_number"] == right["part_number"]
        if not compatible(left, right) and not same_part:
            continue
        if left["region"] == right["region"] and not same_part:
            continue
        key = pair_key(left["source_key"], right["source_key"])
        if not compatible(left, right):
            status, score, reason = (
                "blocked",
                0.0,
                "Same part number contradicts hard specifications",
            )
        elif left["part_number"] and right["part_number"] and not same_part:
            status, score, reason = "distinct", 0.0, "Different known manufacturer part numbers"
        else:
            score = round(
                SequenceMatcher(None, left["description_norm"], right["description_norm"]).ratio(),
                3,
            )
            status = "accepted" if same_part else "review" if score >= 0.75 else "distinct"
            reason = (
                "Exact manufacturer part + specifications"
                if same_part
                else "Text similarity is evidence, not proof of identity"
            )
        if status not in {"blocked", "distinct"} and key in decisions:
            status = "accepted" if decisions[key] == "approve" else "rejected"
            reason = "Explicit steward decision"
        pairs.append(
            {
                "pair_id": key,
                "left": left["source_key"],
                "right": right["source_key"],
                "status": status,
                "score": score,
                "reason": reason,
            }
        )
    groups = [{r["source_key"]} for r in records]
    by_id = {r["source_key"]: r for r in records}
    cannot = {p["pair_id"] for p in pairs if p["status"] in {"blocked", "rejected", "distinct"}}
    cannot.update(key for key, decision in decisions.items() if decision == "reject")
    for pair in sorted(pairs, key=lambda p: (-p["score"], p["pair_id"])):
        if pair["status"] != "accepted":
            continue
        left_group = next(g for g in groups if pair["left"] in g)
        right_group = next(g for g in groups if pair["right"] in g)
        if left_group is right_group:
            continue
        proposed = left_group | right_group
        if any(
            pair_key(a, b) in cannot
            or not compatible(by_id[a], by_id[b])
            or (
                bool(by_id[a]["part_number"])
                and bool(by_id[b]["part_number"])
                and by_id[a]["part_number"] != by_id[b]["part_number"]
            )
            for a, b in itertools.combinations(proposed, 2)
        ):
            pair["status"] = "blocked"
            pair["reason"] = "Cluster-level cannot-link/specification constraint"
            continue
        left_group.update(right_group)
        groups.remove(right_group)
    return {
        "records": records,
        "quarantine": quarantine,
        "pairs": pairs,
        "groups": [sorted(g) for g in sorted(groups, key=lambda g: min(g))],
        "candidate_pairs": len(pairs),
        "all_pairs": len(records) * (len(records) - 1) // 2,
    }


class Master:
    def __init__(self, root: Path):
        self.store = Store(root)

    def create(self, scenario: str, owner: str = "steward") -> dict[str, Any]:
        raw = fixtures()
        if scenario == "clean":
            raw = raw[:120]
            raw[4]["part_number"] = "AX-001"
        data: dict[str, Any] = {
            "raw": raw,
            "decisions": {},
            "audit": [],
            "publication": None,
            "publish_version": 0,
            "scenario": scenario,
        }
        key, revision = self.store.create("master", owner, data)
        return self.view(key, data, revision)

    def view(self, key: str, data: dict[str, Any], revision: int) -> dict[str, Any]:
        trace = Trace()
        with trace.stage("normalize", "Validate regional schema and normalize taxonomy"):
            result = resolve(data["raw"], data["decisions"])
        result.update(
            {
                "run_id": key,
                "revision": revision,
                "rules_version": VERSION,
                "scenario": data["scenario"],
                "audit": data["audit"],
                "publish_version": data["publish_version"],
                "publication": data["publication"],
                "trace": trace.result(),
                "synthetic": True,
            }
        )
        return result

    def load(self, key: str, owner: str) -> dict[str, Any]:
        data, revision = self.store.load(key, "master", owner)
        return self.view(key, data, revision)

    def action(
        self, key: str, owner: str, revision: int, action: str, pair: str = ""
    ) -> dict[str, Any]:
        data, current = self.store.load(key, "master", owner)
        if current != revision:
            raise ConflictError("Workspace revision is stale")
        if owner != "steward":
            raise PermissionError("Viewer identity cannot review or publish")
        result = resolve(data["raw"], data["decisions"])
        if action in {"approve", "reject"}:
            selected = next((p for p in result["pairs"] if p["pair_id"] == pair), None)
            if selected is None or selected["status"] in {"blocked", "distinct"}:
                raise ValueError("Pair is not eligible for a steward identity decision")
            data["decisions"][pair] = action
            data["audit"].append(
                {
                    "pair_id": pair,
                    "decision": action,
                    "actor": owner,
                    "decision_revision": revision + 1,
                }
            )
        elif action == "publish":
            if any(p["status"] == "review" for p in result["pairs"]):
                raise ValueError("Resolve ambiguous pairs before publishing")
            if any(p["status"] == "blocked" for p in result["pairs"]):
                raise ValueError(
                    "Resolve source/cluster conflicts before publishing; prior version retained"
                )
            snapshot = hashlib.sha256(
                json.dumps(
                    {"raw": data["raw"], "decisions": data["decisions"]}, sort_keys=True
                ).encode()
            ).hexdigest()
            previous = data["publication"]
            if previous and previous["snapshot"] == snapshot:
                return self.view(key, data, current)
            previous_ids = (
                {row["source_key"]: row["global_id"] for row in previous["crosswalk"]}
                if previous
                else {}
            )
            products: list[dict[str, Any]] = []
            crosswalk: list[dict[str, Any]] = []
            emitted: set[str] = set()
            version = data["publish_version"] + 1
            for group in result["groups"]:
                old_ids = {previous_ids[source] for source in group if source in previous_ids}
                if len(old_ids) > 1:
                    raise ValueError(
                        "Merging published identities requires a separate migration policy"
                    )
                gid = (
                    next(iter(old_ids))
                    if old_ids
                    else "G-" + hashlib.sha256(group[0].encode()).hexdigest()[:12]
                )
                if gid in emitted:
                    raise ValueError(
                        "Splitting a published identity requires a separate migration policy"
                    )
                emitted.add(gid)
                products.append({"global_id": gid, "sources": group, "publish_version": version})
                crosswalk.extend(
                    {"source_key": source, "global_id": gid, "publish_version": version}
                    for source in group
                )
            data["publish_version"] = version
            data["publication"] = {
                "products": products,
                "crosswalk": crosswalk,
                "snapshot": snapshot,
                "publish_version": version,
            }
            data["audit"].append(
                {
                    "decision": "publish",
                    "actor": owner,
                    "decision_revision": revision + 1,
                    "publish_version": version,
                }
            )
        elif action != "replay":
            raise ValueError("Unsupported action")
        updated = self.store.save(key, data, current)
        return self.view(key, data, updated)
