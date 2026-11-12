from lib.retry_backoff_api import apply_retry_backoff

def test_retry_backoff_regression():
    assert apply_retry_backoff(3) == 5
