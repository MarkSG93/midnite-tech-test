from flask import Flask, request, abort, jsonify
import pytest

app = Flask(__name__)

@app.route("/event", methods=["POST"])
def event():
    content = request.get_json()
    event_type = content["type"]
    if event_type != 'deposit' and event_type != 'withdraw':
        return abort(400, "Only 'deposit' or 'withdraw' are supported event types")
    if "user_id" in content:
        return jsonify(user_id=content["user_id"])
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

def test_responds_with_payload_with_user_id():
    response = app.test_client().post("/event", json={
        "type": "deposit",
        "amount": "42.00",
        "user_id": 1,
        "t": 10
    })
    json = response.get_json()
    assert json['user_id'] == 1

def test_responds_with_no_alert():
    response = app.test_client().post("/event", json={
        "type": "deposit",
        "amount": "42.00",
        "user_id": 1,
        "t": 10
    })
    json = response.get_json()
    assert json['user_id'] == 1
    assert json['alert_codes'] == []
    assert json['alert'] == False