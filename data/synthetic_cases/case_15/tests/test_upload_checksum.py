from lib.upload_checksum_api import apply_upload_checksum

def test_upload_checksum_regression():
    assert apply_upload_checksum(3) == 5
