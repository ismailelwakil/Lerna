from infrastructure.search.trusted import validate_public_url

def test_rejects_localhost_and_private_schemes():
    assert validate_public_url('http://localhost:8000/secret') is False
    assert validate_public_url('file:///etc/passwd') is False
    assert validate_public_url('ftp://example.com/x') is False