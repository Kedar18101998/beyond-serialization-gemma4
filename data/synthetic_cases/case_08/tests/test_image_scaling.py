from lib.image_scaling_api import apply_image_scaling

def test_image_scaling_regression():
    assert apply_image_scaling(3) == 5
