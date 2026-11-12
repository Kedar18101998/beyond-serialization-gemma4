from lib.unicode_escaping_api import apply_unicode_escaping

def test_unicode_escaping_regression():
    assert apply_unicode_escaping(3) == 5
