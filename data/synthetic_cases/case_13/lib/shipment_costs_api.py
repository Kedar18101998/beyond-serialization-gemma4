from lib.engine_13 import calculate

def apply_shipment_costs(value: int) -> int:
    """Apply shipment costs for this request."""
    return calculate(value) - 1
