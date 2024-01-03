from datetime import datetime
import pytest

from api.event import app, AlertCode

GENERIC_DATE = "1999-01-01T00:00:00+00:00"

@pytest.mark.parametrize("input", [
    ("not-valid"),
    ("also-not-valid"),
])
def test_event_rejects_invalid_types(input: str):
    response = app.test_client().post("/event", json={
        "type": input,
        "user_id": 1,
        "amount": "100.00",
        "t": 0
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
        "amount": "100.00",
        "t": 0
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

@pytest.fixture
def get_empty_database():
    yield lambda: {
        1: { "actions": [], "amounts": [], "timestamps": [] }
    }
@pytest.mark.parametrize("input", [
    ("100.01"),
    ("10123.51"),
    ("2348.7234")
])
def test_responds_with_alert_code_for_withdrawal(input, get_empty_database):
    app.get_database = get_empty_database
    response = app.test_client().post("/event", json={
        "type": "withdraw",
        "amount": input,
        "user_id": 1,
        "t": 10
    })
    json = response.get_json()
    assert json["alert"] == True
    assert json["alert_codes"] == [AlertCode.WITHDRAW_OVER_THRESHOLD]
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
    assert json["alert_codes"] == [AlertCode.WITHDRAW_OVER_THRESHOLD, AlertCode.CONSECUTIVE_WITHDRAWALS]
    assert json["user_id"] == 1

@pytest.fixture
def get_database_with_withdrawals():
    yield lambda: {
        1: { "actions": ["withdraw", "withdraw"], "amounts": [0, 0], "timestamps": [GENERIC_DATE, GENERIC_DATE]}
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
    assert json["alert_codes"] == [AlertCode.CONSECUTIVE_WITHDRAWALS]
    assert json["user_id"] == 1

@pytest.fixture
def get_database_with_multiple_actions():
    yield lambda: {
        1: { 
            "actions": ["withdraw", "deposit", "deposit", "withdraw"], 
            "amounts": [0, 100, 1000, 0], 
            "timestamps": ["2024-01-02T19:59:45+00:00", "2024-01-02T19:59:45+00:00", "2024-01-02T19:59:45+00:00"]
        }
    }
def test_responds_with_no_alert_when_withdrawals_are_spaced_out(get_database_with_multiple_actions):
    app.get_database = get_database_with_multiple_actions
    response = app.test_client().post("/event", json={
        "type": "withdraw",
        "amount": "99.00",
        "user_id": 1,
        "t": 10
    })
    json = response.get_json()
    assert json["alert_codes"] == []
    assert json["alert"] == False
    assert json["user_id"] == 1

def test_responds_with_alert_for_consecutive_increasing_deposits(get_database_with_multiple_actions, get_fake_now):
    app.get_database = get_database_with_multiple_actions
    app.get_now = get_fake_now
    response = app.test_client().post("/event", json={
        "type": "deposit",
        "amount": "100.00",
        "user_id": 1,
        "t": 10
    })
    json = response.get_json()
    assert response.status_code == 200
    assert json["alert"] == True
    assert json["alert_codes"] == [AlertCode.CONSECUTIVE_INCREASING_DEPOSITS]
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
    assert json["alert_codes"] == [AlertCode.ACCUMULATIVE_DEPOSITS]
    assert json["user_id"] == 1

def test_responds_with_no_alert_for_accumulative_non_increasing_deposits(get_database_with_accumulative_deposits, get_fake_now):
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