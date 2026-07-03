"""Tests for the task-claim REST endpoint.

mcp-rest-tool-parity: task_claim (atomic task claim, used by the
conductor pattern) was MCP-only. The MCP handler already delegates to
TaskService.claim_task -- this endpoint shares the same service call,
no service-layer duplication.
"""

import tempfile
from pathlib import Path

import pytest

fastapi = pytest.importorskip("fastapi", reason="fastapi not installed")
from fastapi.testclient import TestClient

from pyrite.config import KBConfig, PyriteConfig, Settings
from pyrite.server.api import create_app
from pyrite.services.task_service import TaskService
from pyrite.storage.database import PyriteDB


@pytest.fixture
def task_client():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        tasks_path = tmpdir / "tasks-kb"
        tasks_path.mkdir()
        (tasks_path / "tasks").mkdir()

        kb_config = KBConfig(
            name="test-tasks", path=tasks_path, kb_type="task", description="Test task KB"
        )
        config = PyriteConfig(
            knowledge_bases=[kb_config], settings=Settings(index_path=tmpdir / "index.db")
        )
        db = PyriteDB(config.settings.index_path)
        db.register_kb(
            name="test-tasks", kb_type="task", path=str(tasks_path), description="Test task KB"
        )

        task_svc = TaskService(config, db)
        created = task_svc.create_task(kb_name="test-tasks", title="Claim me via REST")

        app = create_app(config=config)
        app.dependency_overrides[__import__("pyrite.server.api", fromlist=["get_db"]).get_db] = (
            lambda: db
        )
        client = TestClient(app)

        yield {"client": client, "task_id": created["entry_id"], "db": db}
        db.close()


class TestTaskClaimEndpoint:
    def test_claim_open_task_succeeds(self, task_client):
        client = task_client["client"]
        task_id = task_client["task_id"]

        response = client.post(
            f"/api/tasks/{task_id}/claim",
            params={"kb": "test-tasks"},
            json={"assignee": "agent:claimer"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["claimed"] is True
        assert data["assignee"] == "agent:claimer"
        assert data["status"] == "claimed"

    def test_claim_already_claimed_task_returns_conflict_info(self, task_client):
        client = task_client["client"]
        task_id = task_client["task_id"]

        first = client.post(
            f"/api/tasks/{task_id}/claim",
            params={"kb": "test-tasks"},
            json={"assignee": "agent:first"},
        )
        assert first.json()["claimed"] is True

        second = client.post(
            f"/api/tasks/{task_id}/claim",
            params={"kb": "test-tasks"},
            json={"assignee": "agent:second"},
        )
        assert second.status_code == 200
        data = second.json()
        assert data["claimed"] is False
        assert data["current_status"] == "claimed"

    def test_claim_nonexistent_task_returns_not_found_info(self, task_client):
        client = task_client["client"]
        response = client.post(
            "/api/tasks/nonexistent-task/claim",
            params={"kb": "test-tasks"},
            json={"assignee": "agent:x"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["claimed"] is False
        assert "not found" in data["error"]
