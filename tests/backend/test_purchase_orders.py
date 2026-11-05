"""
Tests for the purchase order endpoints (purchase orders raised against backlog items).
"""


def po_payload(backlog_item_id="1", **overrides):
    payload = {
        "backlog_item_id": backlog_item_id,
        "supplier_name": "Acme Supply",
        "quantity": 350,
        "unit_cost": 4.25,
        "expected_delivery_date": "2025-10-20",
        "notes": "Rush order",
    }
    payload.update(overrides)
    return payload


class TestPurchaseOrderEndpoints:
    """Tests for /api/purchase-orders"""

    def test_list_empty_initially(self, client):
        """No purchase orders exist until one is created."""
        response = client.get("/api/purchase-orders")
        assert response.status_code == 200
        assert response.json() == []

    def test_create_purchase_order(self, client):
        """A valid request creates an Ordered purchase order."""
        response = client.post("/api/purchase-orders", json=po_payload())
        assert response.status_code == 201
        po = response.json()
        assert po["backlog_item_id"] == "1"
        assert po["status"] == "Ordered"
        assert po["supplier_name"] == "Acme Supply"
        assert po["quantity"] == 350
        assert "created_date" in po and "id" in po

    def test_get_by_backlog_item(self, client):
        """The lookup is keyed by backlog item id, not purchase order id."""
        created = client.post("/api/purchase-orders", json=po_payload("2")).json()
        response = client.get("/api/purchase-orders/2")
        assert response.status_code == 200
        assert response.json()["id"] == created["id"]

    def test_get_by_backlog_item_not_found(self, client):
        """A backlog item without a purchase order is a 404."""
        response = client.get("/api/purchase-orders/1")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_create_for_unknown_backlog_item(self, client):
        """Creating a purchase order for a missing backlog item is a 404."""
        response = client.post("/api/purchase-orders", json=po_payload("does-not-exist"))
        assert response.status_code == 404

    def test_duplicate_purchase_order_conflicts(self, client):
        """A backlog item can only have one purchase order."""
        assert client.post("/api/purchase-orders", json=po_payload()).status_code == 201
        assert client.post("/api/purchase-orders", json=po_payload()).status_code == 409

    def test_concurrent_requests_create_only_one_purchase_order(self, client):
        """Simultaneous POSTs for the same backlog item yield exactly one 201 and the rest 409."""
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=8) as pool:
            codes = list(pool.map(lambda _: client.post("/api/purchase-orders", json=po_payload("3")).status_code, range(8)))
        assert codes.count(201) == 1
        assert codes.count(409) == 7
        assert len(client.get("/api/purchase-orders").json()) == 1

    def test_non_positive_quantity_rejected(self, client):
        """A zero quantity is a 400."""
        response = client.post("/api/purchase-orders", json=po_payload(quantity=0))
        assert response.status_code == 400

    def test_invalid_payload_returns_422(self, client):
        """A payload missing required fields fails validation."""
        response = client.post("/api/purchase-orders", json={"backlog_item_id": "1"})
        assert response.status_code == 422

    def test_backlog_reflects_purchase_order(self, client):
        """Creating a purchase order flips has_purchase_order on the backlog item."""
        before = {b["id"]: b["has_purchase_order"] for b in client.get("/api/backlog").json()}
        assert before["1"] is False
        client.post("/api/purchase-orders", json=po_payload("1"))
        after = {b["id"]: b["has_purchase_order"] for b in client.get("/api/backlog").json()}
        assert after["1"] is True
