def test_main_pages_render_for_authenticated_user(auth_client):
    for path in ["/dashboard", "/inventory", "/replenishment", "/orders", "/impact"]:
        response = auth_client.get(path)
        assert response.status_code == 200
        assert b"StockWise" in response.data


def test_login_rejects_wrong_password(client):
    response = client.post(
        "/login",
        data={"email": "owner@demo.co.za", "password": "wrong"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"not correct" in response.data


def test_pages_load_pinned_bootstrap_and_responsive_navigation(auth_client):
    for path in ["/dashboard", "/inventory", "/replenishment", "/orders", "/impact"]:
        page = auth_client.get(path).get_data(as_text=True)
        assert "https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" in page
        assert "https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js" in page
        assert 'data-bs-toggle="collapse"' in page
        assert 'aria-controls="main-nav"' in page
        assert 'name="viewport"' in page


def test_inventory_and_planner_keep_forms_and_tables_accessible(auth_client):
    from html.parser import HTMLParser

    class FormParser(HTMLParser):
        def __init__(self):
            super().__init__()
            self.fields = []
            self.labels = set()

        def handle_starttag(self, tag, attrs):
            attrs = dict(attrs)
            if tag in {"input", "select"} and attrs.get("type") != "hidden":
                self.fields.append(attrs.get("id"))
            if tag == "label":
                self.labels.add(attrs.get("for"))

    for path in ["/inventory", "/replenishment", "/login"]:
        if path == "/login":
            auth_client.post("/logout")
        page = auth_client.get(path).get_data(as_text=True)
        parser = FormParser()
        parser.feed(page)
        assert parser.fields
        assert all(field and field in parser.labels for field in parser.fields)
        if path != "/login":
            assert 'class="table-responsive"' in page


def dashboard_metric(response, name):
    import re

    match = re.search(r'id="kpi-' + name + r'"[^>]*>([^<]+)<', response.get_data(as_text=True))
    assert match, name
    return match.group(1).strip()


def test_dashboard_kpis_change_after_a_sale(auth_client, app):
    from datetime import date
    from app.extensions import db
    from app.models import DemandHistory, InventoryBalance, Product, Shop

    with app.app_context():
        shop = db.session.get(Shop, 1)
        # No cash may suppress allocation, but must not hide a reorder need.
        shop.cash_budget = 0
        DemandHistory.query.filter_by(shop_id=shop.id).delete()
        balance = InventoryBalance.query.filter_by(shop_id=shop.id).first()
        product_id = balance.product_id
        cover = balance.product.supplier.lead_time_days + shop.review_period_days + shop.safety_stock_days
        balance.on_hand = cover
        db.session.add(DemandHistory(shop_id=shop.id, product_id=product_id, demand_date=date.today(), quantity_sold=14))
        tracked = Product.query.filter_by(active=True).count()
        db.session.commit()

    before = auth_client.get("/dashboard?shop_id=1")
    assert dashboard_metric(before, "reorder") == "0"
    assert float(dashboard_metric(before, "cover")) == cover
    assert dashboard_metric(before, "skus") == str(tracked)

    sale = auth_client.post("/api/v1/movements", json={
        "shop_id": 1, "product_id": product_id, "movement_type": "sale", "quantity": 1,
    })
    assert sale.status_code == 201
    after = auth_client.get("/dashboard?shop_id=1")
    assert dashboard_metric(after, "reorder") == "1"
    assert float(dashboard_metric(after, "cover")) < cover
    assert dashboard_metric(after, "skus") == str(tracked)


def test_dashboard_handles_no_demand(auth_client, app):
    from app.extensions import db
    from app.models import DemandHistory

    with app.app_context():
        DemandHistory.query.filter_by(shop_id=1).delete()
        db.session.commit()
    response = auth_client.get("/dashboard?shop_id=1")
    assert dashboard_metric(response, "cover") == "No demand data"
    assert dashboard_metric(response, "reorder") == "0"


def test_shop_settings_persist_and_recalculate_recommendations(auth_client):
    before = auth_client.get("/api/v1/recommendations?shop_id=1&supplier_id=1").get_json()
    settings = {"cash_budget": 1234.50, "review_period_days": 14, "safety_stock_days": 7}
    saved = auth_client.patch("/api/v1/shops/1", json=settings)
    assert saved.status_code == 200
    for field, value in settings.items():
        assert saved.get_json()[field] == value
    after = auth_client.get("/api/v1/recommendations?shop_id=1&supplier_id=1").get_json()
    assert sum(item["recommended_quantity"] for item in after["items"]) > sum(
        item["recommended_quantity"] for item in before["items"]
    )
    page = auth_client.get("/replenishment?shop_id=1").get_data(as_text=True)
    assert 'id="shop-settings-form"' in page
    assert 'id="settings-budget"' in page
    assert 'value="1234.50"' in page
    assert 'value="14"' in page
    assert 'value="7"' in page
