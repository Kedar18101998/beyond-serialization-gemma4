from lib.session_expiry_api import apply_session_expiry

def test_session_expiry_regression():
    assert apply_session_expiry(3) == 5
