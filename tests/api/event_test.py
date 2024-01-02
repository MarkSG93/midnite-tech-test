from flask import Flask, request, abort, jsonify
from datetime import datetime
import pytest

database = {}
def get_database():
    return {1: { "actions": [] }}

def get_now():
    return datetime.now()

app = Flask(__name__)
app.get_database = get_database
app.get_now = get_now

# Code: 1100 : A withdraw amount over 100
# Code: 30 : 3 consecutive withdraws
# Code: 300 : 3 consecutive increasing deposits (ignoring withdraws)
# Code: 123 : Accumulative deposit amount over a window of 30 seconds is over 200
@app.route("/event", methods=["POST"])
def event():
    content = request.get_json()
    event_type = content["type"]
    user_id = content["user_id"]
    amount = int(float(content["amount"]) * 100)
    alert_codes = []
    db = app.get_database()
    if event_type != 'deposit' and event_type != 'withdraw':
        return abort(400, "Only 'deposit' or 'withdraw' are supported event types")

    if event_type == "withdraw" and amount > 100 * 100:
        alert_codes.append(1100)
    
    if event_type == "withdraw":
        user_actions = db[user_id]["actions"]
        if len(user_actions) >= 2:
            alert_codes.append(30)
        
    if event_type == "deposit":
        user_actions = db[user_id]["actions"]
        total_deposits = 0
        previous_deposit_amount = 0
        for i, action in enumerate(reversed(user_actions)):
            if action != "deposit":
                continue
            deposit_amount = db[user_id]["amounts"][i]
            if amount < deposit_amount:
                break
            if deposit_amount < previous_deposit_amount:
                continue
            total_deposits += 1
            previous_deposit_amount = deposit_amount
            if total_deposits >= 2:
                alert_codes.append(300)
                break
        
        if "timestamps" in db[user_id]:
            deposits_within_30_seconds = 0
            deposit_amount_within_last_30_seconds = amount
            for i, action in enumerate(reversed(user_actions)):
                if action != "deposit":
                    continue
                previous_action_time = datetime.fromisoformat(db[user_id]["timestamps"][i])
                payload_seconds = content["t"]
                now = app.get_now().replace(second=int(payload_seconds))
                
                if (now - previous_action_time).total_seconds() <= 30:
                    deposits_within_30_seconds += 1
                    deposit_amount_within_last_30_seconds += db[user_id]["amounts"][i]
                if deposit_amount_within_last_30_seconds > 200 * 100:
                    alert_codes.append(123)
                    break

    if len(alert_codes) > 0:
        return jsonify(user_id=user_id, alert_codes=alert_codes, alert=True)

    return jsonify(user_id=user_id, alert_codes=[], alert=False)

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

@pytest.fixture
def get_database_with_withdrawals():
    yield lambda: {
        1: { "actions": ["withdraw", "withdraw"]}
    }

def test_responds_with_alert_code_for_consecutive_withdrawals(get_database_with_withdrawals):
    app.get_database = get_database_with_withdrawals
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

def test_responds_with_multiple_alert_codes(get_database_with_withdrawals):
    app.get_database = get_database_with_withdrawals
    response = app.test_client().post("/event", json={
        "type": "withdraw",
        "amount": "101.00",
        "user_id": 1,
        "t": 10
    })
    json = response.get_json()
    assert response.status_code == 200
    assert json["alert"] == True
    assert json["alert_codes"] == [1100, 30]
    assert json["user_id"] == 1

@pytest.fixture
def get_database_with_multiple_actions():
    yield lambda: {
        1: { "actions": ["withdraw", "deposit", "withdraw", "deposit"], "amounts": [0, 1000, 0, 2000]}
    }
def test_responds_with_alert_for_consecutive_increasing_deposits(get_database_with_multiple_actions):
    app.get_database = get_database_with_multiple_actions
    response = app.test_client().post("/event", json={
        "type": "deposit",
        "amount": "3000.00",
        "user_id": 1,
        "t": 10
    })
    json = response.get_json()
    assert response.status_code == 200
    assert json["alert"] == True
    assert json["alert_codes"] == [300]
    assert json["user_id"] == 1

@pytest.fixture
def get_database_with_accumulative_deposits():
    yield lambda: {
        1: { 
            "actions": ["deposit", "deposit", "deposit"], 
            "amounts": [1000, 10000, 7500], 
            "timestamps": ["1999-01-02T21:40:11+00:00", "2024-01-02T19:59:30+00:00", "2024-01-02T19:59:45+00:00"]
        }
    }
@pytest.fixture
def get_fake_now():
    yield lambda: datetime.fromisoformat("2024-01-02T20:00:00+00:00")

def test_responds_with_alert_for_accumulative_deposits_over_threshold(get_database_with_accumulative_deposits, get_fake_now):
    app.get_database = get_database_with_accumulative_deposits
    app.get_now = get_fake_now
    response = app.test_client().post("/event", json={
        "type": "deposit",
        "amount": "50.00",
        "user_id": 1,
        "t": 0
    })
    json = response.get_json()
    assert response.status_code == 200
    assert json["alert"] == True
    assert json["alert_codes"] == [123]
    assert json["user_id"] == 1

def test_responds_with_no_alert_for_accumulative_deposits(get_database_with_accumulative_deposits, get_fake_now):
    app.get_database = get_database_with_accumulative_deposits
    app.get_now = get_fake_now
    response = app.test_client().post("/event", json={
        "type": "deposit",
        "amount": "10.00",
        "user_id": 1,
        "t": 25
    })
    json = response.get_json()
    assert response.status_code == 200
    assert json["alert"] == False
    assert json["alert_codes"] == []
    assert json["user_id"] == 1