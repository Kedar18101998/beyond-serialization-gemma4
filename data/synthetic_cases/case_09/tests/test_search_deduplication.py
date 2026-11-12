from lib.search_deduplication_api import apply_search_deduplication

def test_search_deduplication_regression():
    assert apply_search_deduplication(3) == 5
