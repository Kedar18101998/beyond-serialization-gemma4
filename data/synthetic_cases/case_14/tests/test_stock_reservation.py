from lib.stock_reservation_api import apply_stock_reservation

def test_stock_reservation_regression():
    assert apply_stock_reservation(3) == 5
