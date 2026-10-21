import pytest

from app import create_app
from app.extensions import db
from app.services.seed import seed_database


@pytest.fixture()
def app():
    application = create_app("testing")
    with application.app_context():
        db.create_all()
        seed_database()
        yield application
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def auth_client(client):
    response = client.post(
        "/login",
        data={"email": "owner@demo.co.za", "password": "demo2026"},
        follow_redirects=False,
    )
    assert response.status_code == 302
    return client

