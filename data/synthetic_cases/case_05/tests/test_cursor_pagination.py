from lib.cursor_pagination_api import apply_cursor_pagination

def test_cursor_pagination_regression():
    assert apply_cursor_pagination(3) == 5
