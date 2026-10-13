from copy import deepcopy

import pytest

from solution_labs.common import ConflictError
from solution_labs.master import Master, fixtures, normalize, pair_key, resolve


def test_identity_precision_and_bounded_candidates(tmp_path):
    master = Master(tmp_path)
    state = master.create("clean")
    truth = {r["source_key"]: r["truth_id"] for r in fixtures()}
    assert len(state["groups"]) == 40
    assert state["candidate_pairs"] < state["all_pairs"] / 10
    assert all(len({truth[key] for key in group}) == 1 for group in state["groups"])
    assert all("truth_id" not in row for row in state["records"])


def test_missing_identity_and_conflicting_specs_do_not_auto_merge(tmp_path):
    state = Master(tmp_path).create("standard")
    assert len(state["quarantine"]) == 1
    assert any(p["status"] == "review" for p in state["pairs"])
    assert any(p["status"] == "blocked" for p in state["pairs"])
    assert all(len(g) == 1 for g in state["groups"] if "NA-CONFLICT" in g)


@pytest.mark.parametrize(
    "field,value",
    [
        ("season", "Unknown"),
        ("size", "wrong"),
        ("speed", "Z"),
        ("load_index", None),
        ("load_index", 999),
    ],
)
def test_invalid_source_contract(field, value):
    row = deepcopy(fixtures()[0])
    row[field] = value
    with pytest.raises(ValueError):
        normalize(row)


def test_cannot_link_applies_to_entire_cluster():
    rows = fixtures()[:3]
    result = resolve(rows, {pair_key(rows[0]["source_key"], rows[2]["source_key"]): "reject"})
    assert max(map(len, result["groups"])) == 2
    assert any(
        p["reason"] == "Cluster-level cannot-link/specification constraint" for p in result["pairs"]
    )


def test_same_specs_different_part_numbers_are_not_identity():
    rows = deepcopy(fixtures()[:3])
    rows[1]["part_number"] = "ANOTHER-PART"
    result = resolve(rows, {})
    assert any(p["status"] == "distinct" for p in result["pairs"])
    assert len(result["groups"]) == 2


def test_low_similarity_and_duplicate_source_rows_are_visible():
    rows = deepcopy(fixtures()[:3])
    rows[1]["part_number"], rows[1]["description"] = "", "Unrelated wording"
    rows.append(dict(rows[0]))
    result = resolve(rows, {})
    assert result["quarantine"][0]["reason"] == "Duplicate source identity"
    assert any(p["status"] == "distinct" for p in result["pairs"])


def test_steward_review_persists_and_revision_is_checked(tmp_path):
    engine = Master(tmp_path)
    state = engine.create("standard")
    pair = next(p["pair_id"] for p in state["pairs"] if p["status"] == "review")
    updated = engine.action(state["run_id"], "steward", state["revision"], "reject", pair)
    assert next(p for p in updated["pairs"] if p["pair_id"] == pair)["status"] == "rejected"
    replay = engine.action(updated["run_id"], "steward", updated["revision"], "replay")
    assert replay["audit"][-1]["decision"] == "reject"
    with pytest.raises(ConflictError):
        engine.action(state["run_id"], "steward", state["revision"], "approve", pair)


def test_viewer_cannot_modify_and_workspace_is_owned(tmp_path):
    engine = Master(tmp_path)
    state = engine.create("clean", "viewer")
    with pytest.raises(PermissionError):
        engine.action(state["run_id"], "viewer", 1, "publish")
    with pytest.raises(LookupError):
        engine.load(state["run_id"], "steward")


def test_publication_is_consistent_idempotent_and_preserves_ids(tmp_path):
    engine = Master(tmp_path)
    state = engine.create("clean")
    published = engine.action(state["run_id"], "steward", 1, "publish")
    snapshot = published["publication"]
    assert len(snapshot["products"]) == 40 and len(snapshot["crosswalk"]) == 120
    assert {r["publish_version"] for r in snapshot["crosswalk"] + snapshot["products"]} == {1}
    replay = engine.action(state["run_id"], "steward", 2, "publish")
    assert replay["revision"] == 2 and replay["publish_version"] == 1
    data, revision = engine.store.load(state["run_id"], "master", "steward")
    data["raw"].append({**data["raw"][0], "source_key": "APAC-NEW"})
    new_revision = engine.store.save(state["run_id"], data, revision)
    result = engine.action(state["run_id"], "steward", new_revision, "publish")
    old = {r["source_key"]: r["global_id"] for r in snapshot["crosswalk"]}
    new = {r["source_key"]: r["global_id"] for r in result["publication"]["crosswalk"]}
    assert all(new[key] == value for key, value in old.items())


def test_failed_publication_does_not_replace_previous(tmp_path):
    engine = Master(tmp_path)
    state = engine.create("clean")
    engine.action(state["run_id"], "steward", 1, "publish")
    data, revision = engine.store.load(state["run_id"], "master", "steward")
    data["raw"].append({**data["raw"][0], "source_key": "NEW-CONFLICT", "size": "255/55R17"})
    revision = engine.store.save(state["run_id"], data, revision)
    with pytest.raises(ValueError, match="conflicts"):
        engine.action(state["run_id"], "steward", revision, "publish")
    assert engine.load(state["run_id"], "steward")["publish_version"] == 1


def test_ambiguous_publish_and_invalid_actions_fail(tmp_path):
    engine = Master(tmp_path)
    state = engine.create("standard")
    with pytest.raises(ValueError, match="ambiguous"):
        engine.action(state["run_id"], "steward", 1, "publish")
    for action, pair in [
        ("approve", "unknown"),
        ("approve", next(p["pair_id"] for p in state["pairs"] if p["status"] == "blocked")),
        ("unknown", ""),
    ]:
        with pytest.raises(ValueError):
            engine.action(state["run_id"], "steward", 1, action, pair)


def test_store_stale_update_is_rejected(tmp_path):
    engine = Master(tmp_path)
    state = engine.create("clean")
    data, revision = engine.store.load(state["run_id"], "master", "steward")
    engine.store.save(state["run_id"], data, revision)
    with pytest.raises(ConflictError):
        engine.store.save(state["run_id"], data, revision)


def test_unknown_bridge_cannot_merge_known_parts_or_bypass_reject():
    rows = deepcopy(fixtures()[:3])
    rows[1]["part_number"] = None
    rows[2]["region"], rows[2]["part_number"] = "NA", "OTHER-PART"
    decisions = {
        pair_key(rows[0]["source_key"], rows[1]["source_key"]): "approve",
        pair_key(rows[1]["source_key"], rows[2]["source_key"]): "approve",
        pair_key(rows[0]["source_key"], rows[2]["source_key"]): "reject",
    }
    result = resolve(rows, decisions)
    assert max(map(len, result["groups"])) == 2


def test_null_parts_are_unknown_and_numeric_strings_are_canonical():
    rows = deepcopy(fixtures()[:3])
    for row in rows:
        row["part_number"] = None
    result = resolve(rows, {})
    assert not any(p["status"] == "accepted" for p in result["pairs"])
    assert all(row["part_number"] == "" for row in result["records"])
    rows[0]["load_index"] = "90"
    assert normalize(rows[0])["load_index"] == 90


@pytest.mark.parametrize(
    "field,value",
    [
        ("manufacturer", None),
        ("source_key", None),
        ("region", "OTHER"),
        ("load_index", 90.5),
        ("load_index", True),
    ],
)
def test_malformed_identity_is_rejected(field, value):
    row = deepcopy(fixtures()[0])
    row[field] = value
    with pytest.raises(ValueError):
        normalize(row)


def test_candidate_limits_and_duplicate_ambiguity_are_enforced():
    with pytest.raises(ValueError, match="batch limit"):
        resolve([fixtures()[0]] * 1001, {})
    rows = [{**fixtures()[0], "source_key": f"SOURCE-{i}"} for i in range(101)]
    with pytest.raises(ValueError, match="too broad"):
        resolve(rows, {})
    result = resolve([fixtures()[0], fixtures()[0]], {})
    assert result["records"] == [] and len(result["quarantine"]) == 2
