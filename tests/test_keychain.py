import subprocess

import pytest

from keychain import KeychainCredentialError, get_keychain_password


def test_get_keychain_password_raises_friendly_error_when_item_missing(monkeypatch) -> None:
    def fake_run(*_args, **_kwargs):
        raise subprocess.CalledProcessError(
            returncode=44,
            cmd=["security", "find-generic-password"],
            stderr="The specified item could not be found in the keychain.",
        )

    monkeypatch.setattr("keychain.subprocess.run", fake_run)

    with pytest.raises(KeychainCredentialError) as excinfo:
        get_keychain_password("hors.liu@ugreen.com", "ugreenmailimap")

    message = str(excinfo.value)
    assert "ugreenmailimap" in message
    assert "hors.liu@ugreen.com" in message
