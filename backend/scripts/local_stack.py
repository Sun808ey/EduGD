"""Run the disposable local PostgreSQL, Flask, and Vite development stack."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from secrets import token_urlsafe
from urllib.error import URLError
from urllib.request import urlopen

BACKEND = Path(__file__).resolve().parents[1]
FRONTEND = BACKEND.parent / "frontend" / "school-policy-admin"
COMPOSE_FILE = BACKEND / "compose.local-postgres.yml"
PROJECT_NAME = "edug-local-stack"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run EduGD's disposable local PostgreSQL, Flask, and Vite stack."
    )
    parser.add_argument("--backend-port", type=int, default=5000)
    parser.add_argument("--frontend-port", type=int, default=5173)
    parser.add_argument("--postgres-port", type=int, default=55432)
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="start the stack, verify health/readiness and Vite, then clean up",
    )
    parser.add_argument(
        "--e2e",
        action="store_true",
        help="seed disposable fixtures and keep the live stack for browser tests",
    )
    return parser


def _run(command: list[str], *, env: dict[str, str] | None = None) -> None:
    subprocess.run(command, cwd=BACKEND, env=env, check=True)


def _compose(
    command: list[str],
    *,
    env: dict[str, str],
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "docker",
            "compose",
            "--project-name",
            PROJECT_NAME,
            "--file",
            str(COMPOSE_FILE),
            *command,
        ],
        cwd=BACKEND,
        env=env,
        text=True,
        check=check,
    )


def _wait_for(url: str, process: subprocess.Popen[bytes], timeout: float = 60) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"child process exited before {url} became ready")
        try:
            with urlopen(url, timeout=2) as response:  # noqa: S310 - local URLs only
                if 200 <= response.status < 500:
                    return
        except (OSError, URLError):
            time.sleep(0.5)
    raise RuntimeError(f"timed out waiting for {url}")


def _terminate(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=10)


def main() -> int:
    args = _parser().parse_args()
    if shutil.which("docker") is None:
        raise RuntimeError("Docker is required for the disposable local database")
    if not FRONTEND.exists():
        raise RuntimeError(f"frontend directory does not exist: {FRONTEND}")
    if not (FRONTEND / "node_modules").exists():
        raise RuntimeError(
            "run npm ci in frontend/school-policy-admin before starting Vite"
        )

    token = token_urlsafe(32)
    pairing_token_pepper = token_urlsafe(32)
    env = os.environ.copy()
    env.update(
        {
            "EDUG_LOCAL_POSTGRES_TOKEN": token,
            "EDUG_LOCAL_POSTGRES_PORT": str(args.postgres_port),
            "APP_ENV": "development",
            "DEVELOPMENT_DATABASE_URL": (
                "postgresql+psycopg2://edug_local:"
                f"{token}@127.0.0.1:{args.postgres_port}/edug_local"
            ),
            "MIGRATION_DATABASE_URL": (
                "postgresql+psycopg2://edug_local:"
                f"{token}@127.0.0.1:{args.postgres_port}/edug_local"
            ),
            "PAIRING_TOKEN_PEPPER": pairing_token_pepper,
            "PAIRING_TOKEN_PEPPER_VERSION": "1",
            "FLASK_DEBUG": "0",
            "ADMIN_FRONTEND_ORIGINS": (
                f"http://localhost:{args.frontend_port},"
                f"http://127.0.0.1:{args.frontend_port}"
            ),
            "ENROLLMENT_ADMIN_ENABLED": "true",
            "DEVICE_ENROLLMENT_MODE": "legacy",
        }
    )
    compose_env = env.copy()
    flask_process: subprocess.Popen[bytes] | None = None
    vite_process: subprocess.Popen[bytes] | None = None
    try:
        _compose(
            [
                "up",
                "--detach",
                "--wait",
                "postgres",
            ],
            env=compose_env,
        )
        _run(
            [sys.executable, "-m", "flask", "--app", "run.py", "db", "upgrade"],
            env=env,
        )
        if args.e2e:
            _run([sys.executable, "-m", "scripts.seed_local_e2e"], env=env)
        flask_process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "flask",
                "--app",
                "run.py",
                "run",
                "--host",
                "127.0.0.1",
                "--port",
                str(args.backend_port),
                "--no-debugger",
                "--no-reload",
            ],
            cwd=BACKEND,
            env=env,
        )
        _wait_for(f"http://127.0.0.1:{args.backend_port}/api/v1/ready", flask_process)
        npm_command = "npm.cmd" if os.name == "nt" else "npm"
        vite_process = subprocess.Popen(
            [
                npm_command,
                "run",
                "dev",
                "--",
                "--host",
                "127.0.0.1",
                "--port",
                str(args.frontend_port),
            ],
            cwd=FRONTEND,
            env={**env, "VITE_API_BASE_URL": ""},
        )
        _wait_for(f"http://127.0.0.1:{args.frontend_port}/login", vite_process)
        print(
            f"Local EduGD stack ready: API=http://127.0.0.1:{args.backend_port}/api/v1 "
            f"Frontend=http://127.0.0.1:{args.frontend_port}"
        )
        if args.smoke:
            return 0
        while True:
            if flask_process.poll() is not None or vite_process.poll() is not None:
                raise RuntimeError("local stack child process exited unexpectedly")
            time.sleep(1)
    except KeyboardInterrupt:
        return 0
    finally:
        if vite_process is not None:
            _terminate(vite_process)
        if flask_process is not None:
            _terminate(flask_process)
        _compose(
            ["down", "--volumes", "--remove-orphans"], env=compose_env, check=False
        )


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, subprocess.CalledProcessError) as error:
        print(f"Local stack blocked: {error}", file=sys.stderr)
        raise SystemExit(1) from error
