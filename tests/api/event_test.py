from flask import Flask, request, abort, jsonify
import pytest

app = Flask(__name__)
# Code: 1100 : A withdraw amount over 100
# Code: 30 : 3 consecutive withdraws
# Code: 300 : 3 consecutive increasing deposits (ignoring withdraws)
# Code: 123 : Accumulative deposit amount over a window of 30 seconds is over 200
@app.route("/event", methods=["POST"])
def event():
    content = request.get_json()
    event_type = content["type"]
    if event_type != 'deposit' and event_type != 'withdraw':
        return abort(400, "Only 'deposit' or 'withdraw' are supported event types")
    if "user_id" in content:
        if float(content["amount"]) > 100:
            return jsonify(user_id=content["user_id"], alert_codes=[1100], alert=True)
        return jsonify(user_id=content["user_id"], alert_codes=[], alert=False)
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

def test_responds_with_alert_code_for_withdrawal():
    response = app.test_client().post("/event", json={
        "type": "deposit",
        "amount": "100.01",
        "user_id": 1,
        "t": 10
    })
    json = response.get_json()
    assert json["alert"] == True
    assert json["alert_codes"] == [1100]
    assert json["user_id"] == 1