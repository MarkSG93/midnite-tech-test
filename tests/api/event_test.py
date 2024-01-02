from flask import Flask, request, abort, jsonify
import pytest

app = Flask(__name__)
database = {
    1: { "actions": ["widthdraw", "withdraw"]}
}
# Code: 1100 : A withdraw amount over 100
# Code: 30 : 3 consecutive withdraws
# Code: 300 : 3 consecutive increasing deposits (ignoring withdraws)
# Code: 123 : Accumulative deposit amount over a window of 30 seconds is over 200
@app.route("/event", methods=["POST"])
def event():
    content = request.get_json()
    event_type = content["type"]
    user_id = content["user_id"]
    if event_type != 'deposit' and event_type != 'withdraw':
        return abort(400, "Only 'deposit' or 'withdraw' are supported event types")

    if user_id not in database:
        database[user_id] = { "actions": [event_type] }
    if event_type == "withdraw" and float(content["amount"]) > 100:
        return jsonify(user_id=user_id, alert_codes=[1100], alert=True)
    
    if event_type == "withdraw":
        user_actions = database[user_id]["actions"]
        if len(user_actions) >= 2:
            return jsonify(user_id=user_id, alert_codes=[30], alert=True)

    return jsonify(user_id=user_id, alert_codes=[], alert=False)

def seed_database():
    database = {
        1: { "actions": ["withdraw", "withdraw"] }
    }

@pytest.mark.parametrize("input", [
    ("not-valid"),
    ("also-not-valid"),
])
def test_event_rejects_invalid_types(input: str):
    response = app.test_client().post("/event", json={
        "type": input,
        "user_id": 1,
        "amount": "100.00"
    })
    assert response.status_code == 400

@pytest.mark.parametrize("input", [
    ("deposit"),
    ("withdraw")
])
def test_event_accepts_valid_event_types(input: str):
    response = app.test_client().post("/event", json={
        "type": input,
        "user_id": 1,
        "amount": "100.00"
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

@pytest.mark.parametrize("input", [
    ("100.01"),
    ("10123.51"),
    ("2348.7234")
])
def test_responds_with_alert_code_for_withdrawal(input):
    response = app.test_client().post("/event", json={
        "type": "withdraw",
        "amount": input,
        "user_id": 1,
        "t": 10
    })
    json = response.get_json()
    assert json["alert"] == True
    assert json["alert_codes"] == [1100]
    assert json["user_id"] == 1

def test_responds_with_alert_code_for_consecutive_withdrawals():
    response = app.test_client().post("/event", json={
        "type": "withdraw",
        "amount": "99.00",
        "user_id": 1,
        "t": 10
    })
    json = response.get_json()
    assert json["alert"] == True
    assert json["alert_codes"] == [30]
    assert json["user_id"] == 1


def test_responds_with_multiple_alert_codes():
    response = app.test_client().post("/event", json={
        "type": "withdraw",
        "amount": "101.00",
        "user_id": 1,
        "t": 10
    })
    json = response.get_json()
    assert json["alert"] == True
    assert [30, 1110] in json["alert_codes"]
    assert json["user_id"] == 1