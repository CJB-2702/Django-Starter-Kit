#!/usr/bin/env python3
"""
Generate a `.env` file for this Django project and typical nginx reverse-proxy deployment.

Django environment requirements (what this file targets)
--------------------------------------------------------
Core (required for any non-trivial deployment):
  - SECRET_KEY — signing sessions, CSRF, password reset tokens, etc.; must be unique and secret.
  - DEBUG — must be False in production; True only for local development.
  - ALLOWED_HOSTS — hostnames the site may serve; prevents Host header attacks.

Database:
  - DATABASE_URL — supported forms: ``sqlite:///relative.db``, ``sqlite:////absolute/path.db``,
    or ``postgresql://USER:PASSWORD@HOST:PORT/NAME`` (requires psycopg2 / psycopg).

HTTPS / reverse proxy (when TLS terminates at nginx):
  - CSRF_TRUSTED_ORIGINS — scheme + host for trusted browser origins (e.g. https://app.example.com).
  - SECURE_SSL_REDIRECT, SESSION_COOKIE_SECURE, CSRF_COOKIE_SECURE — lock cookies and redirects.
  - SECURE_PROXY_SSL_HEADER — tells Django the request was HTTPS (e.g. ``HTTP_X_FORWARDED_PROTO,https``).
  - USE_X_FORWARDED_HOST — trust ``X-Forwarded-Host`` from nginx.

Static/media for production:
  - STATIC_ROOT, MEDIA_ROOT — absolute paths for ``collectstatic`` and uploaded files.

Nginx-related keys below are for operators pasting into server blocks or config management;
Django does not read them unless you wire that yourself.
"""

from __future__ import annotations

import argparse
import os
import secrets
import string
import sys
from datetime import datetime
from pathlib import Path


# When neither --dev nor --no-dev is passed, default here.
DEFAULT_DEV_MODE = False


class EnvGenerator:
    """Build a Django + nginx-oriented environment file."""

    def __init__(self, dev_mode: bool = False) -> None:
        self.dev_mode = dev_mode
        self.project_root = Path(__file__).resolve().parent
        self.env_file = self.project_root / ".env"

    def _timestamp(self) -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def generate_secret_key(self, byte_length: int = 32) -> str:
        if self.dev_mode:
            return "dev-insecure-secret-key-do-not-use-in-production"
        return secrets.token_urlsafe(byte_length)

    def generate_password(self, length: int = 24, include_special: bool = True) -> str:
        if self.dev_mode:
            return "dev-admin-password-change-me"

        lower = string.ascii_lowercase
        upper = string.ascii_uppercase
        digits = string.digits
        special = "!@$%^&*-_+=?"
        required = [
            secrets.choice(lower),
            secrets.choice(upper),
            secrets.choice(digits),
        ]
        if include_special:
            required.append(secrets.choice(special))
        pool = lower + upper + digits + (special if include_special else "")
        body = [secrets.choice(pool) for _ in range(max(0, length - len(required)))]
        out = required + body
        secrets.SystemRandom().shuffle(out)
        return "".join(out)

    def _database_url(self) -> str:
        if self.dev_mode:
            return "sqlite:///db.sqlite3"
        return "sqlite:///db.sqlite3"

    def _allowed_hosts(self) -> str:
        if self.dev_mode:
            return "127.0.0.1,localhost"
        return "127.0.0.1,localhost"

    def _csrf_trusted_origins(self) -> str:
        if self.dev_mode:
            return "http://127.0.0.1:8000,http://localhost:8000"
        return "https://127.0.0.1,https://localhost"

    def _secure_flags(self) -> tuple[str, str, str]:
        """Returns (secure_ssl_redirect, session_cookie_secure, csrf_cookie_secure) as 'True'/'False'."""
        if self.dev_mode:
            return "False", "False", "False"
        return "True", "True", "True"

    def build_content(self) -> tuple[str, dict[str, str]]:
        secret_key = self.generate_secret_key()
        db_url = self._database_url()
        admin_password = self.generate_password()
        ssl_redir, sess_secure, csrf_secure = self._secure_flags()

        static_root = str(self.project_root / "staticfiles")
        media_root = str(self.project_root / "media")

        nginx_upstream_host = "127.0.0.1"
        nginx_upstream_port = "8000"
        nginx_server_name = "localhost"

        content = f"""# Django + nginx environment — generated {self._timestamp()}
# Keep this file out of version control.

# --- Django core ---
SECRET_KEY={secret_key}
DJANGO_DEBUG={'True' if self.dev_mode else 'False'}
ALLOWED_HOSTS={self._allowed_hosts()}

# --- Database (see config/settings.py for supported DATABASE_URL forms) ---
DATABASE_URL={db_url}

# --- Initial superuser (optional; use with createsuperuser or a bootstrap script) ---
DJANGO_SUPERUSER_PASSWORD={admin_password}

# --- HTTPS / cookies (set to True in production behind TLS) ---
SECURE_SSL_REDIRECT={ssl_redir}
SESSION_COOKIE_SECURE={sess_secure}
CSRF_COOKIE_SECURE={csrf_secure}
CSRF_TRUSTED_ORIGINS={self._csrf_trusted_origins()}

# Comma-separated pair: header_name,expected_value
SECURE_PROXY_SSL_HEADER=HTTP_X_FORWARDED_PROTO,https
USE_X_FORWARDED_HOST=True

# --- Static & media (production paths; safe to set in dev) ---
STATIC_ROOT={static_root}
MEDIA_ROOT={media_root}

# --- Nginx / process manager (for templates; Django ignores unless you read them) ---
NGINX_SERVER_NAME={nginx_server_name}
DJANGO_UPSTREAM_HOST={nginx_upstream_host}
DJANGO_UPSTREAM_PORT={nginx_upstream_port}
NGINX_CLIENT_MAX_BODY_SIZE=25M
"""

        credentials = {
            "secret_key": secret_key,
            "database_url": db_url,
            "django_superuser_password": admin_password,
        }
        return content, credentials

    def write_env(self, content: str) -> None:
        self.env_file.write_text(content, encoding="utf-8")
        os.chmod(self.env_file, 0o600)

    def backup_existing(self) -> Path | None:
        if not self.env_file.is_file():
            return None
        safe_ts = self._timestamp().replace(":", "-").replace(" ", "_")
        backup = self.env_file.with_name(f".env.backup.{safe_ts}")
        backup.write_bytes(self.env_file.read_bytes())
        return backup

    def print_summary(self, credentials: dict[str, str]) -> None:
        print()
        print("=" * 72)
        print("Generated .env — store secrets safely (password manager, vault).")
        print("=" * 72)
        print(f"  File: {self.env_file}")
        print(f"  DJANGO_SUPERUSER_PASSWORD: {credentials['django_superuser_password']}")
        print("=" * 72)
        print()

    def run(self, force: bool = False) -> bool:
        if self.env_file.exists() and not force:
            answer = input(f"{self.env_file} exists. Overwrite? [y/N]: ").strip().lower()
            if answer != "y":
                print("Aborted.")
                return False
            self.backup_existing()

        content, credentials = self.build_content()
        self.write_env(content)
        self.print_summary(credentials)
        return True


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a .env file for Django (and nginx deployment hints).",
    )
    parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="Overwrite .env without prompting (still creates a backup if present).",
    )
    parser.add_argument(
        "--dev",
        "-d",
        dest="dev",
        action="store_true",
        help="Development-oriented secrets and relaxed security flags.",
    )
    parser.add_argument(
        "--no-dev",
        dest="dev",
        action="store_false",
        help="Production-oriented defaults (stronger secrets, stricter cookies).",
    )
    parser.set_defaults(dev=DEFAULT_DEV_MODE)
    args = parser.parse_args()

    gen = EnvGenerator(dev_mode=bool(args.dev))
    if args.force and gen.env_file.exists():
        gen.backup_existing()

    ok = gen.run(force=args.force)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
