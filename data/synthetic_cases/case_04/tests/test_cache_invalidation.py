from lib.cache_invalidation_api import apply_cache_invalidation

def test_cache_invalidation_regression():
    assert apply_cache_invalidation(3) == 5
