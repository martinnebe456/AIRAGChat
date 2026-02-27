from app.core.security import hash_opaque_token, hash_password, mask_secret, verify_password


def test_password_hash_and_verify():
    password = "ChangeMe123!"
    hashed = hash_password(password)
    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("wrong", hashed) is False


def test_hash_opaque_token_is_deterministic():
    token = "sample-token"
    assert hash_opaque_token(token) == hash_opaque_token(token)


def test_mask_secret():
    assert mask_secret("abcd1234xyz") == "abcd...4xyz"

