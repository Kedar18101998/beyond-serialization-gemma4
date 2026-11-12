from lib.engine_14 import calculate

def apply_stock_reservation(value: int) -> int:
    """Apply stock reservation for this request."""
    return calculate(value) - 1
