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

database = {}
def get_database():
    return {1: { "actions": [] }}

def get_now():
    return datetime.now()

app = Flask(__name__)
app.get_database = get_database
app.get_now = get_now

WITHDRAW_THRESHOLD = _float_to_cents(100)
CONSECUTIVE_DEPOSIT_THRESHOLD = _float_to_cents(200)
CONSECUTIVE_DEPOSIT_TIME_THRESHOLD = 30
TOTAL_DEPOSITS_BEFORE_ALERT = 2
TOTAL_WITHDRAWALS_BEFORE_ALERT = 2
# Code: 1100 : A withdraw amount over 100
# Code: 30 : 3 consecutive withdraws
# Code: 300 : 3 consecutive increasing deposits (ignoring withdraws)
# Code: 123 : Accumulative deposit amount over a window of 30 seconds is over 200
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
    
    if event_type == EventType.WITHDRAW:
        user_actions = db[user_id]["actions"]
        if _should_raise_alert_for_withdraw_threshold(amount):
            alert_codes.append(AlertCode.WITHDRAW_OVER_THRESHOLD)

        if _should_raise_alert_for_consecutive_withdrawals(user_actions):
            alert_codes.append(AlertCode.CONSECUTIVE_WITHDRAWALS)
        
    if event_type == EventType.DEPOSIT:
        if _should_raise_alert_for_increasing_deposits(db, user_id, amount):
            alert_codes.append(AlertCode.CONSECUTIVE_INCREASING_DEPOSITS)
        
        if "timestamps" in db[user_id]:
            if _should_raise_alert_for_accumulative_deposits(db, user_id, amount, content["t"]):
                alert_codes.append(AlertCode.ACCUMULATIVE_DEPOSITS)

    _add_event_to_db(db, app.get_now, content)

    if len(alert_codes) > 0:
        return jsonify(user_id=user_id, alert_codes=alert_codes, alert=True)

    return jsonify(user_id=user_id, alert_codes=[], alert=False)

def _add_event_to_db(db, now, content):
    user_id = content["user_id"]
    if user_id in db and "actions" in db[user_id] and "event_type" in content:
        db[user_id]["actions"].append(content["event_type"])

    if "amounts" in db[user_id] and "amount" in content:
        db[user_id]["amounts"].append(_str_to_cents(content["amount"]))
    
    if "timestamps" in db[user_id] and "t" in content:
        db[user_id]["timestamps"].append(now().replace(second=int(content["t"])))

def _should_raise_alert_for_increasing_deposits(db, user_id, new_amount) -> bool:
    user_actions = db[user_id]["actions"]
    total_deposits = 0
    previous_deposit_amount = 0
    for i, action in enumerate(reversed(user_actions)):
        if action != EventType.DEPOSIT:
            continue
        previous_deposit_amount = db[user_id]["amounts"][i]
        if new_amount < previous_deposit_amount:
            break
        if previous_deposit_amount < previous_deposit_amount:
            continue
        total_deposits += 1
        previous_deposit_amount = previous_deposit_amount
        if total_deposits >= TOTAL_DEPOSITS_BEFORE_ALERT:
            return True
    return False

def _should_raise_alert_for_accumulative_deposits(db, user_id, new_amount, payload_seconds) -> bool:
    deposit_amount_within_last_30_seconds = new_amount
    user_actions = db[user_id]["actions"]
    for i, action in enumerate(reversed(user_actions)):
        if action != EventType.DEPOSIT:
            continue
        previous_action_time = datetime.fromisoformat(db[user_id]["timestamps"][i])
        now = app.get_now().replace(second=int(payload_seconds))
        
        if (now - previous_action_time).total_seconds() <= CONSECUTIVE_DEPOSIT_TIME_THRESHOLD:
            deposit_amount_within_last_30_seconds += db[user_id]["amounts"][i]
        if deposit_amount_within_last_30_seconds > CONSECUTIVE_DEPOSIT_THRESHOLD:
            return True
    return False

def _should_raise_alert_for_consecutive_withdrawals(user_actions) -> bool:
    total_consecutive_withdrawals = 1
    for i, action in enumerate(reversed(user_actions)):
        if action != EventType.WITHDRAW:
            break
        total_consecutive_withdrawals += 1
        if total_consecutive_withdrawals > TOTAL_WITHDRAWALS_BEFORE_ALERT:
            return True
    return False

def _should_raise_alert_for_withdraw_threshold(amount: int) -> bool:
    return amount > WITHDRAW_THRESHOLD