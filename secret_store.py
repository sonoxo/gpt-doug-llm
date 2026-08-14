"""OS-backed secret retrieval without exporting credentials to child processes."""

from __future__ import annotations

import os
import subprocess
import sys


class SecretStore:
    SERVICES = {
        "developer_totp": "com.sonoxo.gpt-doug.developer-totp",
        "officer_totp": "com.sonoxo.gpt-doug.security-officer-totp",
        "audit_hmac": "com.sonoxo.gpt-doug.audit-hmac",
    }

    @staticmethod
    def get(name: str, account: str) -> str:
        if name not in SecretStore.SERVICES:
            raise ValueError("unknown secret name")
        if sys.platform == "darwin":
            result = subprocess.run(
                ["/usr/bin/security", "find-generic-password", "-a", account, "-s", SecretStore.SERVICES[name], "-w"],
                capture_output=True, text=True, timeout=10, check=False, env={"PATH": "/usr/bin:/bin"},
            )
            if result.returncode != 0 or not result.stdout.strip():
                raise ValueError(f"required Keychain secret unavailable: {name}")
            return result.stdout.strip()
        if os.getenv("GPT_DOUG_ALLOW_ENV_SECRETS", "false").lower() != "true":
            raise ValueError("OS secret store unavailable; environment-secret fallback is disabled")
        env_name = {"developer_totp": "GPT_DOUG_TOTP_SECRET", "officer_totp": "ASTRAL_SECURITY_OFFICER_TOTP_SECRET", "audit_hmac": "ASTRAL_AUDIT_HMAC_KEY"}[name]
        value = os.getenv(env_name, "").strip()
        if not value:
            raise ValueError(f"required secret unavailable: {name}")
        return value
