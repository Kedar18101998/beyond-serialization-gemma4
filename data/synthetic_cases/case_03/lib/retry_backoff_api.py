from lib.engine_03 import calculate

def apply_retry_backoff(value: int) -> int:
    """Apply retry backoff for this request."""
    return calculate(value)
