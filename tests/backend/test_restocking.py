"""
Tests for the restocking recommendation and restock order endpoints.
"""
import pytest


class TestRestockRecommendations:
    """Tests for GET /api/restocking/recommendations"""

    def test_zero_budget_recommends_nothing(self, client):
        """A zero budget buys nothing but still reports the slider maximum."""
        response = client.get("/api/restocking/recommendations?budget=0")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total_cost"] == 0
        assert data["lead_time_days"] == 0
        assert data["max_budget"] > 0

    def test_default_budget_is_zero(self, client):
        """Omitting the budget behaves like a zero budget."""
        response = client.get("/api/restocking/recommendations")
        assert response.status_code == 200
        assert response.json()["items"] == []

    def test_negative_budget_rejected(self, client):
        """A negative budget fails validation."""
        response = client.get("/api/restocking/recommendations?budget=-1")
        assert response.status_code == 422

    def test_infinite_budget_rejected(self, client):
        """An infinite budget fails validation instead of crashing JSON serialisation."""
        response = client.get("/api/restocking/recommendations?budget=inf")
        assert response.status_code == 422

    def test_full_budget_covers_every_shortfall(self, client):
        """A budget at max_budget fully covers every item with no partial lines."""
        max_budget = client.get("/api/restocking/recommendations?budget=0").json()["max_budget"]
        data = client.get(f"/api/restocking/recommendations?budget={max_budget}").json()
        assert len(data["items"]) > 0
        for item in data["items"]:
            assert item["quantity"] == item["shortfall"]
            assert item["partial"] is False
        assert data["total_cost"] == pytest.approx(max_budget, abs=0.01)
        assert data["remaining"] == pytest.approx(0, abs=0.01)

    def test_never_exceeds_budget(self, client):
        """Total cost never exceeds the budget at any level."""
        for budget in (100, 1000, 2500, 5000, 12345.67, 50000):
            data = client.get(f"/api/restocking/recommendations?budget={budget}").json()
            assert data["total_cost"] <= budget + 0.01
            assert data["remaining"] == pytest.approx(budget - data["total_cost"], abs=0.01)

    def test_priority_order_increasing_trend_first(self, client):
        """Increasing-trend items come before stable ones, larger shortfalls first within a trend."""
        max_budget = client.get("/api/restocking/recommendations?budget=0").json()["max_budget"]
        items = client.get(f"/api/restocking/recommendations?budget={max_budget}").json()["items"]
        trends = [i["trend"] for i in items]
        assert trends[0] == "increasing"
        # Once a stable item appears, no increasing item may follow
        first_stable = trends.index("stable")
        assert "increasing" not in trends[first_stable:]
        increasing = [i["shortfall"] for i in items if i["trend"] == "increasing"]
        assert increasing == sorted(increasing, reverse=True)

    def test_partial_fill_stops_at_first_unaffordable_item(self, client):
        """The first item that does not fit is partially filled and nothing follows it."""
        data = client.get("/api/restocking/recommendations?budget=5000").json()
        items = data["items"]
        assert items[-1]["partial"] is True
        assert all(not i["partial"] for i in items[:-1])
        assert items[-1]["quantity"] < items[-1]["shortfall"]

    def test_excludes_items_without_shortfall(self, client):
        """Items already stocked above forecast demand are never recommended."""
        max_budget = client.get("/api/restocking/recommendations?budget=0").json()["max_budget"]
        items = client.get(f"/api/restocking/recommendations?budget={max_budget}").json()["items"]
        skus = [i["sku"] for i in items]
        assert "PSU-501" not in skus  # 420 on hand vs 252 forecast
        assert "MTR-304" not in skus  # decreasing demand, stocked

    def test_lead_time_is_slowest_line(self, client):
        """The order lead time equals the longest lead time among its lines."""
        max_budget = client.get("/api/restocking/recommendations?budget=0").json()["max_budget"]
        data = client.get(f"/api/restocking/recommendations?budget={max_budget}").json()
        assert data["lead_time_days"] == max(i["lead_time_days"] for i in data["items"])

    def test_item_structure(self, client):
        """Each recommended item exposes the fields the UI needs, with consistent totals."""
        items = client.get("/api/restocking/recommendations?budget=5000").json()["items"]
        for item in items:
            for field in ("sku", "name", "trend", "shortfall", "quantity", "unit_cost",
                          "line_total", "supplier_name", "lead_time_days", "partial"):
                assert field in item
            assert item["line_total"] == pytest.approx(item["quantity"] * item["unit_cost"], abs=0.01)


class TestRestockOrders:
    """Tests for POST/GET /api/restock-orders"""

    def test_create_order(self, client):
        """A valid order is created with server-side pricing and lead time."""
        response = client.post("/api/restock-orders", json={
            "budget": 5000,
            "items": [{"sku": "FLT-405", "quantity": 100}, {"sku": "GSK-203", "quantity": 50}],
        })
        assert response.status_code == 201
        order = response.json()
        assert order["status"] == "Submitted"
        assert order["order_number"].startswith("RST-")
        assert order["total_cost"] == pytest.approx(100 * 6.20 + 50 * 8.75, abs=0.01)
        assert order["lead_time_days"] == 10  # GSK-203 (10 days) is slower than FLT-405 (7 days)
        assert len(order["items"]) == 2

    def test_client_cannot_set_prices(self, client):
        """Unit cost comes from demand data even if the client sends a different one."""
        response = client.post("/api/restock-orders", json={
            "budget": 5000,
            "items": [{"sku": "FLT-405", "quantity": 10, "unit_cost": 0.01}],
        })
        assert response.status_code == 201
        assert response.json()["items"][0]["unit_cost"] == 6.20

    def test_created_order_appears_in_list_newest_first(self, client):
        """Submitted orders are listed newest first."""
        first = client.post("/api/restock-orders", json={"budget": 1000, "items": [{"sku": "FLT-405", "quantity": 1}]}).json()
        second = client.post("/api/restock-orders", json={"budget": 1000, "items": [{"sku": "GSK-203", "quantity": 1}]}).json()
        listed = client.get("/api/restock-orders").json()
        assert [o["id"] for o in listed[:2]] == [second["id"], first["id"]]

    def test_list_empty_initially(self, client):
        """With no submitted orders the list is empty."""
        response = client.get("/api/restock-orders")
        assert response.status_code == 200
        assert response.json() == []

    def test_empty_items_rejected(self, client):
        """An order with no items is a 400."""
        response = client.post("/api/restock-orders", json={"budget": 1000, "items": []})
        assert response.status_code == 400

    def test_non_positive_quantity_rejected(self, client):
        """Zero or negative quantities are a 400."""
        for quantity in (0, -5):
            response = client.post("/api/restock-orders", json={"budget": 1000, "items": [{"sku": "FLT-405", "quantity": quantity}]})
            assert response.status_code == 400

    def test_unknown_sku_returns_404(self, client):
        """An SKU outside the demand forecast is a 404."""
        response = client.post("/api/restock-orders", json={"budget": 1000, "items": [{"sku": "NOPE-999", "quantity": 1}]})
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_duplicate_sku_rejected(self, client):
        """The same SKU twice in one order is a 400."""
        response = client.post("/api/restock-orders", json={
            "budget": 1000, "items": [{"sku": "FLT-405", "quantity": 1}, {"sku": "FLT-405", "quantity": 2}]})
        assert response.status_code == 400

    def test_over_budget_rejected(self, client):
        """An order whose total exceeds the budget is a 400."""
        response = client.post("/api/restock-orders", json={"budget": 10, "items": [{"sku": "WDG-001", "quantity": 100}]})
        assert response.status_code == 400
        assert "budget" in response.json()["detail"].lower()

    def test_invalid_payload_returns_422(self, client):
        """Missing fields and a negative budget fail validation."""
        assert client.post("/api/restock-orders", json={"items": []}).status_code == 422
        assert client.post("/api/restock-orders", json={"budget": -1, "items": []}).status_code == 422

    def test_recommendation_can_be_submitted_as_is(self, client):
        """Placing an order from a recommendation always succeeds (budget rounding tolerance)."""
        recommendation = client.get("/api/restocking/recommendations?budget=7777.77").json()
        response = client.post("/api/restock-orders", json={
            "budget": recommendation["budget"],
            "items": [{"sku": i["sku"], "quantity": i["quantity"]} for i in recommendation["items"]],
        })
        assert response.status_code == 201
        assert response.json()["total_cost"] == pytest.approx(recommendation["total_cost"], abs=0.01)
