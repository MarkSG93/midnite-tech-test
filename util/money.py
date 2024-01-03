def _str_to_cents(amount: str) -> int:
    return int(float(amount) * 100)

def _float_to_cents(amount: float) -> int:
    return int(amount * 100)