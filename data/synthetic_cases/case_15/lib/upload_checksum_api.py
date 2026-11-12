from lib.engine_15 import calculate

def apply_upload_checksum(value: int) -> int:
    """Apply upload checksum for this request."""
    return calculate(value) - 1
