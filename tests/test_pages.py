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
