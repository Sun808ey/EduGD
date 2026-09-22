"""Opt-in Redis protocol check using synthetic, expiring keys; no secret output."""

from __future__ import annotations

import argparse
import getpass
import os
import sys
from urllib.parse import urlsplit
from uuid import uuid4

from limits import RateLimitItemPerMinute
from limits.storage import RedisStorage
from limits.strategies import FixedWindowRateLimiter
from redis import Redis


def validated_url(url: str, expected_host: str) -> str:
    """Require the operator's intended TLS endpoint, without URL overrides."""
    parsed = urlsplit(url)
    if (
        parsed.scheme != "rediss"
        or not expected_host
        or parsed.hostname != expected_host.lower()
        or not parsed.password
        or parsed.path not in ("", "/", "/0")
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("Invalid approved Redis endpoint")
    if parsed.port is not None and not 1 <= parsed.port <= 65535:
        raise ValueError("Invalid Redis port")
    return url


def verify(url: str, expected_host: str, ca_file: str | None = None) -> None:
    """Check TLS/auth, expiry and the same fixed-window library used by Flask."""
    url = validated_url(url, expected_host)
    options = {
        "socket_connect_timeout": 3,
        "socket_timeout": 3,
        "ssl_cert_reqs": "required",
        "ssl_check_hostname": True,
    }
    if ca_file:
        options["ssl_ca_certs"] = ca_file
    client = Redis.from_url(url, **options)
    # Reuse the verified TLS pool for the installed limits library.
    namespace = f"edug-redis-probe:{uuid4().hex}"
    storage = RedisStorage(
        url, connection_pool=client.connection_pool, key_prefix=namespace
    )
    limiter = FixedWindowRateLimiter(storage)
    limit = RateLimitItemPerMinute(2, namespace=namespace)
    key = f"{namespace}:sentinel"
    value = uuid4().hex.encode()
    try:
        if not client.ping():
            raise RuntimeError("PING failed")
        if not client.set(key, value, ex=60, nx=True):
            raise RuntimeError("Synthetic key creation failed")
        ttl = client.ttl(key)
        if client.get(key) != value or not isinstance(ttl, int) or not 0 < ttl <= 60:
            raise RuntimeError("Read/expiry check failed")
        results = [limiter.hit(limit, "synthetic") for _ in range(3)]
        if results != [True, True, False]:
            raise RuntimeError("Rate-limit enforcement failed")
        if limiter.get_window_stats(limit, "synthetic").remaining != 0:
            raise RuntimeError("Rate-limit counter check failed")
    finally:
        # Only this run's keys. No FLUSHDB, FLUSHALL, wildcard deletion or reset.
        # Both keys expire within 60 seconds if connection loss prevents cleanup.
        try:
            client.delete(key)
            storage.clear(limit.key_for("synthetic"))
        finally:
            client.close()
            client.connection_pool.disconnect()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--environment", choices=("staging", "production"), required=True
    )
    parser.add_argument("--approve-probe-writes", action="store_true")
    parser.add_argument(
        "--prompt-url",
        action="store_true",
        help="Read the TLS URL without echoing it or saving it in shell history.",
    )
    parser.add_argument("--expected-host", help="Approved non-secret database hostname")
    args = parser.parse_args()
    if not args.approve_probe_writes:
        print("NOT RUN: synthetic writes require explicit probe approval.")
        return 2
    if args.prompt_url and not sys.stdin.isatty():
        print("NOT RUN: hidden URL entry requires an interactive terminal.")
        return 2
    try:
        verify(
            getpass.getpass("Approved rediss:// URL (hidden): ")
            if args.prompt_url
            else os.environ.get("REDIS_PROBE_URL", ""),
            args.expected_host or os.environ.get("REDIS_PROBE_EXPECTED_HOST", ""),
            os.environ.get("REDIS_PROBE_CA_FILE") or None,
        )
    except Exception:
        # Provider/client exceptions can contain connection URLs or passwords.
        print(f"FAIL: {args.environment} Redis check; details suppressed.")
        return 1
    print(f"PASS: {args.environment} TLS/auth, expiry and fixed-window checks.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
