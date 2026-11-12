from lib.timezone_scheduling_api import apply_timezone_scheduling

def test_timezone_scheduling_regression():
    assert apply_timezone_scheduling(3) == 5
