from lib.request_throttling_api import apply_request_throttling

def test_request_throttling_regression():
    assert apply_request_throttling(3) == 5
