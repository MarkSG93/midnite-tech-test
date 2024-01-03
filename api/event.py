from flask import Flask, request, abort, jsonify
from datetime import datetime

from util.money import _float_to_cents, _str_to_cents

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
    if event_type != 'deposit' and event_type != 'withdraw':
        return abort(400, "Only 'deposit' or 'withdraw' are supported event types")

    if event_type == "withdraw" and amount > WITHDRAW_THRESHOLD:
        alert_codes.append(1100)
    
    if event_type == "withdraw":
        user_actions = db[user_id]["actions"]
        if len(user_actions) >= TOTAL_WITHDRAWALS_BEFORE_ALERT:
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
            if total_deposits >= TOTAL_DEPOSITS_BEFORE_ALERT:
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
                
                if (now - previous_action_time).total_seconds() <= CONSECUTIVE_DEPOSIT_TIME_THRESHOLD:
                    deposits_within_30_seconds += 1
                    deposit_amount_within_last_30_seconds += db[user_id]["amounts"][i]
                if deposit_amount_within_last_30_seconds > CONSECUTIVE_DEPOSIT_THRESHOLD:
                    alert_codes.append(123)
                    break

    if len(alert_codes) > 0:
        return jsonify(user_id=user_id, alert_codes=alert_codes, alert=True)

    return jsonify(user_id=user_id, alert_codes=[], alert=False)


