from collections.abc import Callable
from typing import cast

import click

from app.services.administrator_authentication import (
    AdministratorMutationResult,
    AdministratorOperationError,
    bootstrap_administrator,
    disable_administrator,
    reset_administrator_password,
    revoke_administrator_sessions,
)


@click.group("admin")
def admin_cli() -> None:
    """Manage local administrator authentication."""


def _operator_options[**P](command: Callable[P, None]) -> Callable[P, None]:
    command = click.option(
        "--reason",
        required=True,
        help="Bounded non-secret reason for the operation.",
    )(command)
    return click.option(
        "--operator",
        "operator_subject",
        required=True,
        help="Non-secret trusted host-operator identity.",
    )(command)


def _prompt_password() -> str:
    return cast(
        str,
        click.prompt(
            "Password",
            hide_input=True,
            confirmation_prompt=True,
            type=str,
        ),
    )


def _run_operation(
    operation: Callable[..., AdministratorMutationResult],
    **arguments: object,
) -> AdministratorMutationResult:
    try:
        return operation(**arguments)
    except AdministratorOperationError as error:
        raise click.ClickException(str(error)) from None


@admin_cli.command("bootstrap")
@click.option("--username", required=True)
@click.option("--display-name", required=True)
@_operator_options
def bootstrap_command(
    username: str,
    display_name: str,
    operator_subject: str,
    reason: str,
) -> None:
    """Create the first local administrator."""
    _run_operation(
        bootstrap_administrator,
        username=username,
        display_name=display_name,
        password=_prompt_password(),
        operator_subject=operator_subject,
        reason=reason,
    )
    click.echo("Administrator bootstrap completed.")


@admin_cli.command("reset-password")
@click.argument("username")
@_operator_options
def reset_password_command(
    username: str,
    operator_subject: str,
    reason: str,
) -> None:
    """Reset an administrator password and revoke active sessions."""
    result = _run_operation(
        reset_administrator_password,
        username=username,
        password=_prompt_password(),
        operator_subject=operator_subject,
        reason=reason,
    )
    click.echo(
        f"Administrator password reset completed; "
        f"revoked sessions: {result.revoked_sessions}."
    )


@admin_cli.command("disable")
@click.argument("username")
@_operator_options
def disable_command(
    username: str,
    operator_subject: str,
    reason: str,
) -> None:
    """Disable an administrator and revoke active sessions."""
    result = _run_operation(
        disable_administrator,
        username=username,
        operator_subject=operator_subject,
        reason=reason,
    )
    click.echo(f"Administrator disabled; revoked sessions: {result.revoked_sessions}.")


@admin_cli.command("revoke-sessions")
@click.argument("username")
@_operator_options
def revoke_sessions_command(
    username: str,
    operator_subject: str,
    reason: str,
) -> None:
    """Revoke every unexpired administrator session."""
    result = _run_operation(
        revoke_administrator_sessions,
        username=username,
        operator_subject=operator_subject,
        reason=reason,
    )
    click.echo(f"Administrator sessions revoked: {result.revoked_sessions}.")


__all__ = ["admin_cli"]
