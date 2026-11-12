from lib.notification_batching_api import apply_notification_batching

def test_notification_batching_regression():
    assert apply_notification_batching(3) == 5
