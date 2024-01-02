import pytest
from api import app

def test_event_accepts_payload():
    response = app.test_client().post("/event", data={
        "type": "deposit",
        "amount": "42.00",
        "user_id": 1,
        "t": 10
    })
    assert response.status_code == 200