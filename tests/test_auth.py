from src.auth import hash_admin_password, verify_admin_password


def test_plain_admin_password_matches_direct_value():
    assert verify_admin_password("clave-test", "clave-test")
    assert not verify_admin_password("otra", "clave-test")


def test_hashed_admin_password_matches_pbkdf2_value():
    password_hash = hash_admin_password("clave-test")

    assert password_hash.startswith("pbkdf2_sha256:")
    assert verify_admin_password("clave-test", password_hash)
    assert not verify_admin_password("otra", password_hash)


def test_missing_admin_password_fails_closed():
    assert not verify_admin_password("clave-test", "")
