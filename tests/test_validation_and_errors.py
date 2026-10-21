from datetime import date

import pytest
from flask import abort

from app.extensions import db
from app.models import (
    DemandHistory,
    InventoryBalance,
    Order,
    OrderLine,
    Product,
    Shop,
    StockMovement,
    User,
    load_user,
)
from app.services.seed import seed_database


def _product_for_supplier(app, supplier_id=1):
    with app.app_context():
        product = Product.query.filter_by(supplier_id=supplier_id).first()
        return product.id, product.pack_size


def _create_order(client, app, supplier_id=1):
    product_id, pack_size = _product_for_supplier(app, supplier_id)
    response = client.post(
        "/api/v1/orders",
        json={
            "shop_id": 1,
            "supplier_id": supplier_id,
            "lines": [{"product_id": product_id, "quantity": pack_size}],
        },
    )
    assert response.status_code == 201
    return response.get_json()["order"]["id"], product_id, pack_size


def test_inventory_rejects_unknown_shop_and_clamps_pagination(auth_client):
    missing = auth_client.get("/api/v1/inventory?shop_id=99999")
    assert missing.status_code == 404
    assert missing.get_json()["error"] == "not_found"

    bounded = auth_client.get("/api/v1/inventory?shop_id=1&page=-3&per_page=500")
    assert bounded.status_code == 200
    assert bounded.get_json()["page"] == 1
    assert len(bounded.get_json()["items"]) == 20


@pytest.mark.parametrize(
    ("payload", "status", "message_part"),
    [
        ({}, 400, "required fields"),
        ({"shop_id": 99999, "product_id": 1, "movement_type": "sale", "quantity": 1}, 404, "access denied"),
        ({"shop_id": 1, "product_id": 1, "movement_type": "transfer", "quantity": 1}, 400, "not supported"),
        ({"shop_id": 1, "product_id": 1, "movement_type": "sale", "quantity": 0}, 400, "greater than zero"),
        ({"shop_id": 1, "product_id": 99999, "movement_type": "sale", "quantity": 1}, 404, "Product not found"),
    ],
)
def test_movement_validation_paths(auth_client, payload, status, message_part):
    response = auth_client.post("/api/v1/movements", json=payload)
    assert response.status_code == status
    assert message_part in response.get_json()["message"]


def test_receipt_creates_a_missing_inventory_balance(auth_client, app):
    with app.app_context():
        product = Product.query.first()
        product_id = product.id
        InventoryBalance.query.filter_by(shop_id=1, product_id=product_id).delete()
        db.session.commit()

    response = auth_client.post(
        "/api/v1/movements",
        json={"shop_id": 1, "product_id": product_id, "movement_type": "receipt", "quantity": 3},
    )
    assert response.status_code == 201
    assert response.get_json()["item"]["on_hand"] == 3


def test_sale_creates_missing_daily_demand(auth_client, app):
    with app.app_context():
        balance = InventoryBalance.query.filter(InventoryBalance.shop_id == 1, InventoryBalance.on_hand > 0).first()
        product_id = balance.product_id
        DemandHistory.query.filter_by(shop_id=1, product_id=product_id, demand_date=date.today()).delete()
        db.session.commit()

    response = auth_client.post(
        "/api/v1/movements",
        json={"shop_id": 1, "product_id": product_id, "movement_type": "sale", "quantity": 1},
    )
    assert response.status_code == 201
    with app.app_context():
        demand = DemandHistory.query.filter_by(shop_id=1, product_id=product_id, demand_date=date.today()).one()
        assert demand.quantity_sold == 1


def test_recommendation_errors_and_provisional_result(auth_client, app):
    assert auth_client.get("/api/v1/recommendations?shop_id=99999").status_code == 404
    negative = auth_client.get("/api/v1/recommendations?shop_id=1&budget=-1")
    assert negative.status_code == 400

    with app.app_context():
        supplier_product_ids = [row.id for row in Product.query.filter_by(supplier_id=2).all()]
        DemandHistory.query.filter(
            DemandHistory.shop_id == 1,
            DemandHistory.product_id.in_(supplier_product_ids),
        ).delete(synchronize_session=False)
        db.session.commit()

    provisional = auth_client.get("/api/v1/recommendations?shop_id=1&supplier_id=2&budget=1000")
    assert provisional.status_code == 200
    assert provisional.get_json()["provisional"] is True
    assert "provisional" in provisional.get_json()["message"]


def test_order_listing_filter_and_unknown_shop(auth_client, app):
    assert auth_client.get("/api/v1/orders?shop_id=99999").status_code == 404
    _create_order(auth_client, app)
    drafts = auth_client.get("/api/v1/orders?shop_id=1&status=draft&page=-2&per_page=500")
    assert drafts.status_code == 200
    assert drafts.get_json()["page"] == 1
    assert drafts.get_json()["total"] == 1
    assert auth_client.get("/api/v1/orders?shop_id=1&status=received").get_json()["total"] == 0


def test_order_creation_validation_paths(auth_client, app):
    no_shop = auth_client.post("/api/v1/orders", json={"shop_id": 99999, "supplier_id": 1, "lines": []})
    assert no_shop.status_code == 404
    no_supplier = auth_client.post("/api/v1/orders", json={"shop_id": 1, "supplier_id": 99999, "lines": []})
    assert no_supplier.status_code == 400

    product_id, pack_size = _product_for_supplier(app, 1)
    wrong_supplier = auth_client.post(
        "/api/v1/orders",
        json={"shop_id": 1, "supplier_id": 2, "lines": [{"product_id": product_id, "quantity": pack_size}]},
    )
    assert wrong_supplier.status_code == 400
    assert "selected supplier" in wrong_supplier.get_json()["message"]

    duplicate = auth_client.post(
        "/api/v1/orders",
        json={
            "shop_id": 1,
            "supplier_id": 1,
            "lines": [
                {"product_id": product_id, "quantity": pack_size},
                {"product_id": product_id, "quantity": pack_size},
            ],
        },
    )
    assert duplicate.status_code == 400
    assert "unique" in duplicate.get_json()["message"]


def test_order_state_and_constraint_failures(auth_client, app):
    assert auth_client.post("/api/v1/orders/99999/approve", json={}).status_code == 404
    assert auth_client.post("/api/v1/orders/99999/receive", json={}).status_code == 404

    order_id, _, _ = _create_order(auth_client, app)
    with app.app_context():
        shop = db.session.get(Shop, 1)
        shop.cash_budget = 0
        db.session.commit()
    over_budget = auth_client.post(f"/api/v1/orders/{order_id}/approve", json={})
    assert over_budget.status_code == 409
    assert over_budget.get_json()["error"] == "constraint_violation"

    with app.app_context():
        shop = db.session.get(Shop, 1)
        shop.cash_budget = 100000
        shop.storage_capacity_units = 0
        db.session.commit()
    no_space = auth_client.post(f"/api/v1/orders/{order_id}/approve", json={})
    assert no_space.status_code == 409
    assert "storage" in no_space.get_json()["message"]

    with app.app_context():
        shop = db.session.get(Shop, 1)
        shop.storage_capacity_units = 100000
        db.session.commit()
    assert auth_client.post(f"/api/v1/orders/{order_id}/approve", json={}).status_code == 200
    assert auth_client.post(f"/api/v1/orders/{order_id}/approve", json={}).status_code == 409
    assert auth_client.post(f"/api/v1/orders/{order_id}/receive", json={}).status_code == 200
    assert auth_client.post(f"/api/v1/orders/{order_id}/receive", json={}).status_code == 409


def test_receive_creates_missing_balance_and_skips_fully_received_line(auth_client, app):
    order_id, product_id, pack_size = _create_order(auth_client, app)
    assert auth_client.post(f"/api/v1/orders/{order_id}/approve", json={}).status_code == 200
    with app.app_context():
        InventoryBalance.query.filter_by(shop_id=1, product_id=product_id).delete()
        db.session.commit()
    received = auth_client.post(f"/api/v1/orders/{order_id}/receive", json={})
    assert received.status_code == 200
    with app.app_context():
        assert InventoryBalance.query.filter_by(shop_id=1, product_id=product_id).one().on_hand == pack_size

    second_id, _, _ = _create_order(auth_client, app)
    with app.app_context():
        order = db.session.get(Order, second_id)
        order.status = "approved"
        order.lines[0].quantity_received = order.lines[0].quantity_ordered
        movement_count = StockMovement.query.count()
        db.session.commit()
    assert auth_client.post(f"/api/v1/orders/{second_id}/receive", json={}).status_code == 200
    with app.app_context():
        assert StockMovement.query.count() == movement_count


def test_login_logout_and_authenticated_login_redirect(auth_client):
    assert auth_client.get("/login").status_code == 302
    logged_out = auth_client.post("/logout", follow_redirects=True)
    assert logged_out.status_code == 200
    assert b"You have signed out" in logged_out.data
    assert auth_client.get("/dashboard").status_code == 302


def test_owner_denied_unknown_shop_and_admin_can_open_any_shop(auth_client, client):
    assert auth_client.get("/dashboard?shop_id=99999").status_code == 403
    auth_client.post("/logout")
    login = client.post("/login", data={"email": "admin@demo.co.za", "password": "admin2026"})
    assert login.status_code == 302
    assert client.get("/dashboard?shop_id=2").status_code == 200
    assert client.get("/api/v1/inventory").status_code == 200


def test_html_and_api_not_found_handlers(client):
    html = client.get("/does-not-exist")
    assert html.status_code == 404
    assert b"Page not found" in html.data
    api = client.get("/api/v1/does-not-exist")
    assert api.status_code == 404
    assert api.get_json()["error"] == "not_found"


def test_html_and_api_server_error_handlers(app):
    app.config["PROPAGATE_EXCEPTIONS"] = False

    @app.get("/qa-boom")
    def qa_boom():
        raise RuntimeError("expected QA error")

    @app.get("/api/v1/qa-boom")
    def qa_api_boom():
        raise RuntimeError("expected API QA error")

    client = app.test_client()
    html = client.get("/qa-boom")
    assert html.status_code == 500
    assert b"Something went wrong" in html.data
    api = client.get("/api/v1/qa-boom")
    assert api.status_code == 500
    assert api.get_json()["error"] == "server_error"


def test_seed_is_idempotent_and_user_loader_works(app):
    with app.app_context():
        before = (User.query.count(), Shop.query.count(), Product.query.count())
        seed_database()
        after = (User.query.count(), Shop.query.count(), Product.query.count())
        assert before == after == (2, 5, 20)
        assert load_user(1).email == "owner@demo.co.za"

