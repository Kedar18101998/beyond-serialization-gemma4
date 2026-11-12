from lib.percentile_metrics_api import apply_percentile_metrics

def test_percentile_metrics_regression():
    assert apply_percentile_metrics(3) == 5
