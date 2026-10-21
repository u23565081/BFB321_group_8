from app.extensions import db
from app.models import InventoryBalance, Order, Product, Shop


def test_protected_page_requires_login(client):
    response = client.get("/dashboard")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_api_requires_login_with_json_error(client):
    response = client.get("/api/v1/inventory?shop_id=1")
    assert response.status_code == 401
    assert response.is_json
    assert response.get_json()["error"] == "unauthorised"


def test_inventory_api_paginates_and_filters(auth_client):
    response = auth_client.get("/api/v1/inventory?shop_id=1&page=1&per_page=5&q=maize")
    payload = response.get_json()
    assert response.status_code == 200
    assert payload["page"] == 1
    assert payload["total"] >= 1
    assert all("maize" in item["name"].lower() for item in payload["items"])


def test_sale_updates_balance_and_rejects_negative_stock(auth_client, app):
    with app.app_context():
        balance = InventoryBalance.query.filter_by(shop_id=1).first()
        product_id = balance.product_id
        before = balance.on_hand

    response = auth_client.post(
        "/api/v1/movements",
        json={"shop_id": 1, "product_id": product_id, "movement_type": "sale", "quantity": 1},
    )
    assert response.status_code == 201
    assert response.get_json()["item"]["on_hand"] == before - 1

    rejected = auth_client.post(
        "/api/v1/movements",
        json={"shop_id": 1, "product_id": product_id, "movement_type": "sale", "quantity": 9999},
    )
    assert rejected.status_code == 400
    assert "cannot be negative" in rejected.get_json()["message"]


def test_recommendations_respect_budget_and_pack_sizes(auth_client):
    response = auth_client.get("/api/v1/recommendations?shop_id=1&supplier_id=1&budget=900")
    payload = response.get_json()
    assert response.status_code == 200
    assert payload["totals"]["total_cost"] <= 900
    for item in payload["items"]:
        assert item["allocated_quantity"] % item["pack_size"] == 0


def test_draft_approve_receive_order_flow(auth_client, app):
    with app.app_context():
        product = Product.query.filter_by(supplier_id=1).first()
        shop = db.session.get(Shop, 1)
        balance = InventoryBalance.query.filter_by(shop_id=shop.id, product_id=product.id).first()
        before = balance.on_hand
        product_id = product.id
        pack_size = product.pack_size

    created = auth_client.post(
        "/api/v1/orders",
        json={"shop_id": 1, "supplier_id": 1, "lines": [{"product_id": product_id, "quantity": pack_size}]},
    )
    assert created.status_code == 201
    order_id = created.get_json()["order"]["id"]
    assert created.get_json()["order"]["status"] == "draft"

    approved = auth_client.post(f"/api/v1/orders/{order_id}/approve", json={})
    assert approved.status_code == 200
    assert approved.get_json()["order"]["status"] == "approved"

    received = auth_client.post(f"/api/v1/orders/{order_id}/receive", json={})
    assert received.status_code == 200
    assert received.get_json()["order"]["status"] == "received"

    with app.app_context():
        balance = InventoryBalance.query.filter_by(shop_id=1, product_id=product_id).first()
        assert balance.on_hand == before + pack_size


def test_order_rejects_non_pack_quantity(auth_client, app):
    with app.app_context():
        product = Product.query.filter_by(supplier_id=1).first()
        invalid = product.pack_size + 1
        product_id = product.id
    response = auth_client.post(
        "/api/v1/orders",
        json={"shop_id": 1, "supplier_id": 1, "lines": [{"product_id": product_id, "quantity": invalid}]},
    )
    assert response.status_code == 400
    assert "full packs" in response.get_json()["message"]
