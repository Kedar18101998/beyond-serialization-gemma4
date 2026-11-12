from lib.config_precedence_api import apply_config_precedence

def test_config_precedence_regression():
    assert apply_config_precedence(3) == 5
