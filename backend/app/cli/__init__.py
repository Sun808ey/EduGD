from flask import Flask

from app.cli.admin import admin_cli


def register_cli_commands(app: Flask) -> None:
    app.cli.add_command(admin_cli)


__all__ = ["register_cli_commands"]
