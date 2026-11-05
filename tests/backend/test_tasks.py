"""
Tests for the task endpoints used by the profile menu task list.
"""


def create_task(client, **overrides):
    payload = {"title": "Review Q4 inventory", "priority": "high", "dueDate": "2025-10-08"}
    payload.update(overrides)
    return client.post("/api/tasks", json=payload)


class TestTaskEndpoints:
    """Tests for /api/tasks"""

    def test_list_empty_initially(self, client):
        """No tasks exist until one is created."""
        response = client.get("/api/tasks")
        assert response.status_code == 200
        assert response.json() == []

    def test_create_task(self, client):
        """A created task starts pending and keeps the camelCase dueDate the client uses."""
        response = create_task(client)
        assert response.status_code == 201
        task = response.json()
        assert task["title"] == "Review Q4 inventory"
        assert task["priority"] == "high"
        assert task["dueDate"] == "2025-10-08"
        assert task["status"] == "pending"
        # Prefixed so it can't collide with the client's numeric mock task ids
        assert task["id"].startswith("task-")

    def test_priority_defaults_to_medium(self, client):
        """Priority is optional and defaults to medium."""
        response = client.post("/api/tasks", json={"title": "Call supplier", "dueDate": "2025-10-09"})
        assert response.status_code == 201
        assert response.json()["priority"] == "medium"

    def test_created_task_is_listed(self, client):
        """Created tasks appear in the list."""
        created = create_task(client).json()
        assert created in client.get("/api/tasks").json()

    def test_toggle_flips_status_both_ways(self, client):
        """PATCH toggles pending to completed and back, returning the full task."""
        task_id = create_task(client).json()["id"]
        first = client.patch(f"/api/tasks/{task_id}")
        assert first.status_code == 200
        assert first.json()["status"] == "completed"
        assert first.json()["title"] == "Review Q4 inventory"
        assert client.patch(f"/api/tasks/{task_id}").json()["status"] == "pending"

    def test_delete_task(self, client):
        """A deleted task is gone from the list."""
        task_id = create_task(client).json()["id"]
        assert client.delete(f"/api/tasks/{task_id}").status_code == 204
        assert client.get("/api/tasks").json() == []

    def test_ids_not_reused_after_delete(self, client):
        """Deleting a task never causes a later task to reuse its id."""
        first = create_task(client).json()["id"]
        second = create_task(client, title="Second").json()["id"]
        client.delete(f"/api/tasks/{first}")
        third = create_task(client, title="Third").json()["id"]
        assert third not in (first, second)

    def test_non_standard_seeded_id_does_not_break_creation(self, client):
        """A hand-seeded task whose id isn't task-<number> is ignored when numbering new tasks."""
        from mock_data import tasks
        tasks.append({"id": "legacy", "title": "Seeded", "priority": "low", "dueDate": "2025-10-01", "status": "pending"})
        response = create_task(client)
        assert response.status_code == 201
        assert response.json()["id"] == "task-1"

    def test_unknown_task_returns_404(self, client):
        """Toggling or deleting a missing task is a 404."""
        for response in (client.patch("/api/tasks/task-999"), client.delete("/api/tasks/task-999")):
            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()

    def test_invalid_payload_returns_422(self, client):
        """Empty title, bad priority and malformed dates fail validation."""
        assert create_task(client, title="").status_code == 422
        assert create_task(client, priority="urgent").status_code == 422
        assert create_task(client, dueDate="10/08/2025").status_code == 422
        assert client.post("/api/tasks", json={"title": "No date"}).status_code == 422
