from fastapi.testclient import TestClient

from solution_labs.app import create_app


def test_remote_clients_and_cross_origin_requests_are_denied(tmp_path):
    app = create_app(state_root=tmp_path)
    with TestClient(app, client=("203.0.113.8", 40000)) as client:
        assert client.get("/api/health").status_code == 403
    with TestClient(app) as client:
        assert client.get("/api/health").status_code == 200
        for headers in [
            {"Host": "attacker.example"},
            {"Origin": "https://attacker.example"},
            {"Origin": "null"},
            {"Sec-Fetch-Site": "cross-site"},
        ]:
            assert client.get("/api/health", headers=headers).status_code == 403
        assert client.get("/.env").status_code == 404
        assert client.get("/api/health").headers["cache-control"] == "no-store"
