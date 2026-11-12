from lib.shipment_costs_api import apply_shipment_costs

def test_shipment_costs_regression():
    assert apply_shipment_costs(3) == 5
