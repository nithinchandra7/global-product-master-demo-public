import pytest
from fastapi.testclient import TestClient

from solution_labs.app import create_app


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(state_root=tmp_path)) as connection:
        yield connection


def test_master_api_validation_scope_conflicts_and_publication(client):
    headers = {"X-Demo-Identity": "steward"}
    assert client.post("/api/labs/master/runs", json={}).status_code == 401
    assert (
        client.post(
            "/api/labs/master/runs", headers=headers, json={"scenario": "unknown"}
        ).status_code
        == 422
    )
    state = client.post("/api/labs/master/runs", headers=headers, json={"scenario": "clean"}).json()
    url = "/api/labs/master/runs/" + state["run_id"]
    assert client.get(url, headers=headers).status_code == 200
    assert client.get(url, headers={"X-Demo-Identity": "viewer"}).status_code == 404
    assert (
        client.post(
            url + "/actions",
            headers=headers,
            json={"revision": 1, "action": "approve", "pair_id": "bad"},
        ).status_code
        == 422
    )
    assert (
        client.post(
            url + "/actions", headers=headers, json={"revision": 1, "action": "publish"}
        ).json()["publish_version"]
        == 1
    )
    assert (
        client.post(
            url + "/actions", headers=headers, json={"revision": 1, "action": "replay"}
        ).status_code
        == 409
    )
    viewer = client.post(
        "/api/labs/master/runs", headers={"X-Demo-Identity": "viewer"}, json={"scenario": "clean"}
    ).json()
    assert (
        client.post(
            "/api/labs/master/runs/" + viewer["run_id"] + "/actions",
            headers={"X-Demo-Identity": "viewer"},
            json={"revision": 1, "action": "publish"},
        ).status_code
        == 403
    )
