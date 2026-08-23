from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def test_render_uses_dependency_aware_readiness_health_check() -> None:
    render_configuration = (REPOSITORY_ROOT / "render.yaml").read_text(encoding="utf-8")

    assert "healthCheckPath: /api/v1/ready" in render_configuration
    assert "healthCheckPath: /api/v1/health" not in render_configuration


def test_render_declares_deterministic_database_pool_budget() -> None:
    render_configuration = (REPOSITORY_ROOT / "render.yaml").read_text(encoding="utf-8")

    assert '- key: SQLALCHEMY_POOL_SIZE\n        value: "3"' in render_configuration
    assert '- key: SQLALCHEMY_MAX_OVERFLOW\n        value: "2"' in render_configuration
