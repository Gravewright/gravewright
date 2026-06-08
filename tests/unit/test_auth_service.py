from __future__ import annotations


from app.business.auth.auth_service import AuthService
from tests.conftest import seed_user


def test_is_first_user_true_on_empty_db(db):
    assert AuthService().is_first_user() is True


def test_is_first_user_false_after_registration(db):
    seed_user()
    assert AuthService().is_first_user() is False


def test_register_creates_user(db):
    result = AuthService().register(
        name="Alice",
        email="alice@test.com",
        password="Password1!",
        client_ip="127.0.0.1",
    )
    assert result.success
    assert result.user is not None
    assert result.user["email"] == "alice@test.com"


def test_register_first_user_gets_owner_role(db):
    result = AuthService().register(
        name="Alice",
        email="alice@test.com",
        password="Password1!",
        client_ip="127.0.0.1",
    )
    assert result.success
    assert result.user["system_role"] == "owner"


def test_register_subsequent_user_gets_user_role(db):
    seed_user(name="First", email="first@test.com")
    result = AuthService().register(
        name="Second",
        email="second@test.com",
        password="Password1!",
        client_ip="127.0.0.1",
    )
    assert result.success
    assert result.user["system_role"] == "user"


def test_register_rejects_duplicate_email(db):
    AuthService().register(
        name="Alice",
        email="alice@test.com",
        password="Password1!",
        client_ip="127.0.0.1",
    )
    result = AuthService().register(
        name="Alice 2",
        email="alice@test.com",
        password="Password1!",
        client_ip="127.0.0.2",
    )
    assert not result.success
    assert result.error_key == "auth.errors.register_failed"


def test_register_rejects_weak_password(db):
    result = AuthService().register(
        name="Alice",
        email="alice@test.com",
        password="weak",
        client_ip="127.0.0.1",
    )
    assert not result.success
    assert result.error_key == "auth.errors.invalid_password"


def test_login_accepts_valid_credentials(db):
    AuthService().register(
        name="Alice",
        email="alice@test.com",
        password="Password1!",
        client_ip="127.0.0.1",
    )
    result = AuthService().login(
        email="alice@test.com",
        password="Password1!",
        client_ip="127.0.0.1",
    )
    assert result.success
    assert result.user is not None


def test_login_rejects_wrong_password(db):
    AuthService().register(
        name="Alice",
        email="alice@test.com",
        password="Password1!",
        client_ip="127.0.0.1",
    )
    result = AuthService().login(
        email="alice@test.com",
        password="WrongPass1!",
        client_ip="127.0.0.1",
    )
    assert not result.success


def test_login_rejects_unknown_email(db):
    result = AuthService().login(
        email="nobody@test.com",
        password="Password1!",
        client_ip="127.0.0.1",
    )
    assert not result.success


def test_password_hash_not_plaintext(db):
    from app.persistence.repositories.user_repository import UserRepository
    AuthService().register(
        name="Alice",
        email="alice@test.com",
        password="Password1!",
        client_ip="127.0.0.1",
    )
    user = UserRepository().get_by_email("alice@test.com")
    assert user is not None
    assert user["password_hash"] != "Password1!"
