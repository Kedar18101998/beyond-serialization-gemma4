from lib.invoice_rounding_api import apply_invoice_rounding

def test_invoice_rounding_regression():
    assert apply_invoice_rounding(3) == 5
