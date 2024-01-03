import enum
from flask import Flask, request, abort, jsonify
from datetime import datetime

from util.money import _float_to_cents, _str_to_cents

class EventType(str, enum.Enum):
    DEPOSIT = "deposit"
    WITHDRAW = "withdraw"

class AlertCode(int, enum.Enum):
    WITHDRAW_OVER_THRESHOLD = 1100
    CONSECUTIVE_WITHDRAWALS = 30
    CONSECUTIVE_INCREASING_DEPOSITS = 300
    ACCUMULATIVE_DEPOSITS = 123

WITHDRAW_THRESHOLD = _float_to_cents(100)
CONSECUTIVE_DEPOSIT_THRESHOLD = _float_to_cents(200)
CONSECUTIVE_DEPOSIT_TIME_THRESHOLD = 30
TOTAL_INCREASING_DEPOSITS_BEFORE_ALERT = 2
TOTAL_WITHDRAWALS_BEFORE_ALERT = 2

# very basic database
default_database = {1: { "actions": [], "amounts": [], "timestamps": [] }}
def get_database():
    return default_database

def get_now():
    return datetime.now()

app = Flask(__name__)
app.get_database = get_database
app.get_now = get_now

@app.route("/event", methods=["POST"])
def event():
    content = request.get_json()
    event_type = content["type"]
    user_id = content["user_id"]
    amount = _str_to_cents(content["amount"])
    alert_codes = []
    db = app.get_database()
    
    if event_type != EventType.DEPOSIT and event_type != EventType.WITHDRAW:
        return abort(400, "Only 'deposit' or 'withdraw' are supported event types")
    
    _add_event_to_db(db, app.get_now, content)
    if event_type == EventType.WITHDRAW:
        if _should_raise_alert_for_withdraw_threshold(amount):
            alert_codes.append(AlertCode.WITHDRAW_OVER_THRESHOLD)

        if _should_raise_alert_for_consecutive_withdrawals(db[user_id]["actions"]):
            alert_codes.append(AlertCode.CONSECUTIVE_WITHDRAWALS)
        
    if event_type == EventType.DEPOSIT:
        if _should_raise_alert_for_increasing_deposits(db, user_id, amount):
            alert_codes.append(AlertCode.CONSECUTIVE_INCREASING_DEPOSITS)
        
        if _should_raise_alert_for_accumulative_deposits(db, user_id, amount, content["t"]):
            alert_codes.append(AlertCode.ACCUMULATIVE_DEPOSITS)

    if len(alert_codes) > 0:
        return jsonify(user_id=user_id, alert_codes=alert_codes, alert=True)

    return jsonify(user_id=user_id, alert_codes=[], alert=False)

def _add_event_to_db(db, now, content):
    user_id = content["user_id"]
    if user_id not in db:
        db[user_id] = { "actions": [], "timestamps": [], "amounts": [] }

    if "type" in content:
        db[user_id]["actions"].append(content["type"])

    if "amount" in content:
        db[user_id]["amounts"].append(_str_to_cents(content["amount"]))
    
    if "t" in content:
        timestamp = now().replace(second=int(content["t"]))
        db[user_id]["timestamps"].append(timestamp.isoformat())

def _should_raise_alert_for_increasing_deposits(db, user_id, new_amount) -> bool:
    user_actions = db[user_id]["actions"][::-1]
    amounts = db[user_id]["amounts"][::-1]
    total_deposits = 0
    current_amount = -1
    print(user_actions, amounts)
    for i, action in enumerate(user_actions):
        if action != EventType.DEPOSIT:
            continue
        current_amount = amounts[i]
        if i + 1 < len(amounts) and current_amount > amounts[i+1]:
            total_deposits += 1
        if total_deposits > TOTAL_INCREASING_DEPOSITS_BEFORE_ALERT:
            return True
    return False

def _should_raise_alert_for_accumulative_deposits(db, user_id, new_amount, payload_seconds) -> bool:
    deposit_amount_within_time_period = new_amount
    user_actions = db[user_id]["actions"][::-1]
    timestamps = db[user_id]["timestamps"][::-1]
    if len(user_actions) < 2:
        return False

    for i, action in enumerate(user_actions):
        if action != EventType.DEPOSIT:
            continue
        previous_action_time = datetime.fromisoformat(timestamps[i])
        now = app.get_now().replace(second=payload_seconds)
        
        if (now - previous_action_time).total_seconds() <= CONSECUTIVE_DEPOSIT_TIME_THRESHOLD:
            deposit_amount_within_time_period += db[user_id]["amounts"][i]
        if deposit_amount_within_time_period > CONSECUTIVE_DEPOSIT_THRESHOLD:
            return True
    return False

def _should_raise_alert_for_consecutive_withdrawals(user_actions) -> bool:
    total_consecutive_withdrawals = 0
    for action in reversed(user_actions):
        if action != EventType.WITHDRAW:
            return False
        total_consecutive_withdrawals += 1
        if total_consecutive_withdrawals > TOTAL_WITHDRAWALS_BEFORE_ALERT:
            return True
    return False

def _should_raise_alert_for_withdraw_threshold(amount: int) -> bool:
    return amount > WITHDRAW_THRESHOLD