from flask import Flask
import pytest

app = Flask(__name__)

@app.route("/event", methods=["POST"])
def event():
    return ""

def test_event_accepts_payload():
    response = app.test_client().post("/event", data={
        "type": "deposit",
        "amount": "42.00",
        "user_id": 1,
        "t": 10
    })
    assert response.status_code == 200

def test_event_rejects_invalid_types():
    response = app.test_client().post("/event", data={
        "type": "not-valid",
    })
    assert response.status_code == 400