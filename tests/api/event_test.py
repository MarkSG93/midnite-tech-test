from flask import Flask, request, abort
import pytest

app = Flask(__name__)

@app.route("/event", methods=["POST"])
def event():
    content = request.get_json()
    event_type = content["type"]
    if event_type != 'deposit' and event_type != 'withdraw':
        return abort(400, "Only 'deposit' or 'withdraw' are supported event types")
    return ""

def test_event_accepts_payload():
    response = app.test_client().post("/event", json={
        "type": "deposit",
        "amount": "42.00",
        "user_id": 1,
        "t": 10
    })
    assert response.status_code == 200

@pytest.mark.parametrize("input", [
    ("not-valid"),
    ("also-not-valid"),
])
def test_event_rejects_invalid_types(input: str):
    response = app.test_client().post("/event", json={
        "type": input,
    })
    assert response.status_code == 400

@pytest.mark.parametrize("input", [
    ("deposit"),
    ("withdraw")
])
def test_event_accepts_valid_event_types(input: str):
    response = app.test_client().post("/event", json={
        "type": input
    })
    assert response.status_code == 200