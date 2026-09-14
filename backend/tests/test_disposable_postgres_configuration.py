from pathlib import Path

import yaml

from test_support.postgres_safety import validate_postgres_test_environment


def test_disposable_stack_cannot_publish_database_or_use_hosted_secrets() -> None:
    configuration = yaml.safe_load(
        (Path(__file__).resolve().parents[1] / "compose.postgres-test.yml").read_text()
    )
    assert configuration["networks"]["isolated"]["internal"] is True
    for service in configuration["services"].values():
        assert "ports" not in service
        assert "env_file" not in service
        assert "network_mode" not in service
    values = configuration["services"]["tests"]["environment"]
    approved = validate_postgres_test_environment(values, require_destructive=True)
    assert (
        f"db.{approved.project_ref}.supabase.co"
        in configuration["services"]["postgres"]["networks"]["isolated"]["aliases"]
    )
    assert "${" not in str(values)
