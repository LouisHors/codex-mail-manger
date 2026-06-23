from __future__ import annotations

import subprocess


class KeychainCredentialError(RuntimeError):
    pass


def get_keychain_password(account: str, service: str) -> str:
    try:
        result = subprocess.run(
            [
                "security",
                "find-generic-password",
                "-a",
                account,
                "-s",
                service,
                "-w",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as exc:
        message = (
            f"Unable to read Keychain credential for service '{service}' and account '{account}'. "
            "Make sure the generic password exists in macOS Keychain Access."
        )
        if exc.stderr:
            message = f"{message} security stderr: {exc.stderr.strip()}"
        raise KeychainCredentialError(message) from exc
