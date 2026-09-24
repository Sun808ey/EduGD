from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from flask import g

import app.routes.dpc_controls as dpc
import app.routes.policies as policies
from app.admin_api import AdminRequestError

UUID_TEXT = "550e8400-e29b-41d4-a716-446655440000"


def _handler(function):
    return function.__wrapped__.__wrapped__


def test_policy_route_handlers_cover_invalid_and_persistence_paths(app, monkeypatch):
    with app.test_request_context(json={}):
        g.administrator_request_context = SimpleNamespace(
            administrator=SimpleNamespace(id=1, administrator_uuid=uuid4())
        )
        assert _handler(policies.create_admin_policy)().status_code == 400
        monkeypatch.setattr(
            policies,
            "create_policy",
            lambda **_: (_ for _ in ()).throw(policies.PolicyAdministrationConflict()),
        )
        with app.test_request_context(json={"name": "x", "payload": {}}):
            g.administrator_request_context = SimpleNamespace(
                administrator=SimpleNamespace(id=1)
            )
            assert _handler(policies.create_admin_policy)().status_code == 409
        monkeypatch.setattr(
            policies,
            "create_policy",
            lambda **_: (_ for _ in ()).throw(policies.PolicyAdministrationError()),
        )
        with app.test_request_context(json={"name": "x", "payload": {}}):
            g.administrator_request_context = SimpleNamespace(
                administrator=SimpleNamespace(id=1)
            )
            assert _handler(policies.create_admin_policy)().status_code == 503

    with app.test_request_context(json={"status": "active", "reason": "ok"}):
        g.administrator_request_context = SimpleNamespace(
            administrator=SimpleNamespace(id=1)
        )
        monkeypatch.setattr(
            policies,
            "set_lifecycle",
            lambda **_: (_ for _ in ()).throw(policies.PolicyAdministrationNotFound()),
        )
        assert (
            _handler(policies.update_admin_policy_lifecycle)(UUID_TEXT).status_code
            == 404
        )
        with app.test_request_context(json={"status": "active", "reason": "bad\n"}):
            g.administrator_request_context = SimpleNamespace(
                administrator=SimpleNamespace(id=1)
            )
            assert (
                _handler(policies.update_admin_policy_lifecycle)(UUID_TEXT).status_code
                == 400
            )


@pytest.mark.parametrize(
    "function, error, status",
    [
        (policies.admin_policies, AdminRequestError("bad", "bad", 400), 400),
        (policies.admin_policies, policies.AdminReadPersistenceError(), 503),
        (policies.admin_policy_detail, ValueError(), 400),
        (policies.admin_policy_detail, policies.AdminReadNotFoundError(), 404),
        (policies.admin_policy_detail, policies.AdminReadPersistenceError(), 503),
        (policies.admin_policy_revisions, ValueError(), 400),
        (policies.admin_policy_revisions, policies.AdminReadNotFoundError(), 404),
        (policies.admin_policy_revisions, policies.AdminReadPersistenceError(), 503),
    ],
)
def test_policy_read_routes_map_errors(app, monkeypatch, function, error, status):
    target = (
        "list_policies"
        if function is policies.admin_policies
        else (
            "get_policy"
            if function is policies.admin_policy_detail
            else "list_policy_revisions"
        )
    )
    monkeypatch.setattr(
        policies,
        target,
        lambda *args, error=error, **kwargs: (_ for _ in ()).throw(error),
    )
    with app.test_request_context():
        g.administrator_request_context = SimpleNamespace(
            administrator=SimpleNamespace(id=1)
        )
        response = (
            _handler(function)(UUID_TEXT)
            if function is not policies.admin_policies
            else _handler(function)()
        )
    assert response.status_code == status


def test_dpc_read_routes_and_summary_cover_empty_state(app, monkeypatch):
    class EmptySession:
        def scalar(self, _query):
            return None

        def scalars(self, _query):
            return SimpleNamespace(all=lambda: [])

    monkeypatch.setattr(dpc, "db", SimpleNamespace(session=EmptySession()))
    with app.test_request_context("/?page=1&per_page=10"):
        g.administrator_request_context = SimpleNamespace(
            administrator=SimpleNamespace(id=1)
        )
        assert _handler(dpc.get_block_override)(UUID_TEXT).status_code == 404
        assert _handler(dpc.control_evidence)(UUID_TEXT).status_code == 404
        assert _handler(dpc.dpc_summary)().status_code == 200


def test_dpc_evidence_and_override_invalid_inputs(app):
    with app.test_request_context():
        g.administrator_request_context = SimpleNamespace(
            administrator=SimpleNamespace(id=1)
        )
        assert _handler(dpc.get_block_override)("not-a-uuid").status_code == 400
        assert _handler(dpc.control_evidence)("not-a-uuid").status_code == 400


def test_web_filter_event_and_usage_map_auth_and_payload_errors(app, monkeypatch):
    context = SimpleNamespace(device=SimpleNamespace(device_uuid=UUID_TEXT, id=1))
    monkeypatch.setattr(dpc, "get_device_authentication_context", lambda: context)
    with app.test_request_context(json={}):
        g.device_authentication_context = context
        assert dpc.web_filter_event.__wrapped__(UUID_TEXT).status_code == 400
        monkeypatch.setattr(
            dpc,
            "report_usage",
            lambda *_: SimpleNamespace(
                usage_date=datetime.now(UTC).date(), active_minutes=3
            ),
        )
        assert dpc.usage.__wrapped__(UUID_TEXT).status_code == 200


def test_policy_mutation_handlers_cover_revision_assignment_and_clear(app, monkeypatch):
    context = SimpleNamespace(
        administrator=SimpleNamespace(id=1, administrator_uuid=uuid4())
    )
    with app.test_request_context(json={"payload": {}}):
        g.administrator_request_context = context
        revision = SimpleNamespace(revision_uuid=uuid4(), version=2)
        monkeypatch.setattr(policies, "add_revision", lambda **_: revision)
        response = _handler(policies.create_admin_policy_revision)(UUID_TEXT)
        assert response.status_code == 201
        monkeypatch.setattr(
            policies,
            "add_revision",
            lambda **_: (_ for _ in ()).throw(policies.PolicyAdministrationNotFound()),
        )
        assert (
            _handler(policies.create_admin_policy_revision)(UUID_TEXT).status_code
            == 404
        )

    assignment = SimpleNamespace(event_uuid=uuid4(), status="active")
    result = SimpleNamespace(assignment=assignment, replaced=False)
    with app.test_request_context(
        json={"policy_revision_uuid": str(uuid4()), "reason": "assign"}
    ):
        g.administrator_request_context = context
        monkeypatch.setattr(
            policies,
            "validate_assignment_request",
            lambda _: SimpleNamespace(
                policy_revision_uuid=str(uuid4()), reason="assign"
            ),
        )
        monkeypatch.setattr(policies, "replace_policy_assignment", lambda *args: result)
        response = _handler(policies.assign_device_policy)(UUID_TEXT)
        assert response.status_code == 200
        assert response.headers["Cache-Control"] == "no-store"

    clear_result = SimpleNamespace(event=SimpleNamespace(event_uuid=uuid4()))
    with app.test_request_context(json={"reason": "clear"}):
        g.administrator_request_context = context
        monkeypatch.setattr(policies, "validate_clear_request", lambda _: "clear")
        monkeypatch.setattr(
            policies, "clear_policy_assignment", lambda *args: clear_result
        )
        assert _handler(policies.clear_device_policy)(UUID_TEXT).status_code == 200


def test_dpc_evidence_serialization_and_listing(app, monkeypatch):
    class Column:
        def desc(self):
            return self

    class Usage:
        device_id = Column()
        reported_at = Column()

    class Override:
        device_id = Column()
        created_at = Column()

    class WebFilter:
        device_id = Column()
        observed_at = Column()

    class Application:
        device_id = Column()
        observed_at = Column()

    class Query:
        def where(self, *_):
            return self

        def order_by(self, *_):
            return self

        def limit(self, *_):
            return self

    now = datetime.now(UTC)
    usage = Usage()
    usage.reported_at = now
    usage.usage_date = now.date()
    usage.active_minutes = 10
    usage.policy_uuid = uuid4()
    usage.revision_uuid = uuid4()
    override = Override()
    override.created_at = now
    override.operation = "block"
    override.reason = "ok"
    web_filter = WebFilter()
    web_filter.observed_at = now
    web_filter.domain_hash = b"x" * 32
    web_filter.rule_id = "focus"
    web_filter.outcome = "blocked"
    web_filter.policy_uuid = uuid4()
    web_filter.revision_uuid = uuid4()
    application = Application()
    application.observed_at = now
    application.outcome = "applied"
    application.error_code = None
    application.policy_uuid = None
    application.revision_uuid = None
    rows = [[usage], [override], [web_filter], [application]]

    class Session:
        def scalar(self, _):
            return SimpleNamespace(id=7)

        def scalars(self, _):
            return SimpleNamespace(all=lambda: rows.pop(0))

    monkeypatch.setattr(dpc, "DeviceUsageDaily", Usage)
    monkeypatch.setattr(dpc, "DeviceControlEvent", Override)
    monkeypatch.setattr(dpc, "DeviceWebFilterEvent", WebFilter)
    monkeypatch.setattr(dpc, "PolicyApplicationEvent", Application)
    monkeypatch.setattr(dpc, "select", lambda *_: Query())
    monkeypatch.setattr(dpc, "db", SimpleNamespace(session=Session()))
    with app.test_request_context("/?page=1&per_page=10"):
        g.administrator_request_context = SimpleNamespace(
            administrator=SimpleNamespace(id=1)
        )
        response = _handler(dpc.control_evidence)(UUID_TEXT)
    assert response.status_code == 200
    assert [item["kind"] for item in response.get_json()["evidence"]] == [
        "usage",
        "override",
        "web_filter",
        "policy_application",
    ]
    with pytest.raises(TypeError):
        dpc._evidence_item("unknown", object())


def test_dpc_web_filter_success_and_device_identity_failures(app, monkeypatch):
    context = SimpleNamespace(device=SimpleNamespace(device_uuid=UUID_TEXT, id=1))
    calls: list[object] = []
    session = SimpleNamespace(
        add=lambda row: calls.append(row), commit=lambda: None, rollback=lambda: None
    )
    monkeypatch.setattr(dpc, "get_device_authentication_context", lambda: context)
    monkeypatch.setattr(dpc, "db", SimpleNamespace(session=session))
    payload = {
        "event_uuid": str(uuid4()),
        "domain_hash": "ab" * 32,
        "rule_id": "focus",
        "outcome": "blocked",
        "policy_uuid": str(uuid4()),
        "revision_uuid": str(uuid4()),
        "observed_at": "2026-09-24T12:00:00Z",
    }
    with app.test_request_context(json=payload):
        assert dpc.web_filter_event.__wrapped__(UUID_TEXT).status_code == 201
    assert len(calls) == 1
    with app.test_request_context(json=payload):
        assert dpc.web_filter_event.__wrapped__(str(uuid4())).status_code == 401
        assert dpc.usage.__wrapped__(str(uuid4())).status_code == 401
        assert dpc.sync_v3.__wrapped__(str(uuid4())).status_code == 401


def test_dpc_override_read_and_summary_error_paths(app, monkeypatch):
    class Query:
        def where(self, *_):
            return self

    now = datetime.now(UTC)
    override = SimpleNamespace(
        version=1, status="active", reason="focus", issued_at=now, cleared_at=None
    )
    results = [SimpleNamespace(id=7), override]
    session = SimpleNamespace(scalar=lambda _: results.pop(0))
    monkeypatch.setattr(dpc, "select", lambda *_: Query())
    monkeypatch.setattr(dpc, "db", SimpleNamespace(session=session))
    with app.test_request_context():
        g.administrator_request_context = SimpleNamespace(
            administrator=SimpleNamespace(id=1)
        )
        response = _handler(dpc.get_block_override)(UUID_TEXT)
    assert response.status_code == 200
    assert response.get_json()["override"]["status"] == "active"

    class BrokenSession:
        def scalar(self, _):
            raise RuntimeError("database unavailable")

    monkeypatch.setattr(dpc, "db", SimpleNamespace(session=BrokenSession()))
    with app.test_request_context():
        g.administrator_request_context = SimpleNamespace(
            administrator=SimpleNamespace(id=1)
        )
        assert _handler(dpc.dpc_summary)().status_code == 503


def test_policy_write_routes_cover_success_and_unavailable_errors(app, monkeypatch):
    context = SimpleNamespace(
        administrator=SimpleNamespace(id=1, administrator_uuid=uuid4())
    )
    created = SimpleNamespace(policy_uuid=uuid4(), status="draft")
    monkeypatch.setattr(policies, "create_policy", lambda **_: created)
    with app.test_request_context(json={"name": "Policy", "payload": {}}):
        g.administrator_request_context = context
        assert _handler(policies.create_admin_policy)().status_code == 201

    monkeypatch.setattr(
        policies,
        "add_revision",
        lambda **_: (_ for _ in ()).throw(policies.PolicyAdministrationConflict()),
    )
    with app.test_request_context(json={"payload": {}}):
        g.administrator_request_context = context
        assert (
            _handler(policies.create_admin_policy_revision)(UUID_TEXT).status_code
            == 409
        )
    monkeypatch.setattr(
        policies,
        "add_revision",
        lambda **_: (_ for _ in ()).throw(policies.PolicyAdministrationError()),
    )
    with app.test_request_context(json={"payload": {}}):
        g.administrator_request_context = context
        assert (
            _handler(policies.create_admin_policy_revision)(UUID_TEXT).status_code
            == 503
        )

    monkeypatch.setattr(
        policies,
        "set_lifecycle",
        lambda **_: SimpleNamespace(policy_uuid=uuid4(), status="inactive"),
    )
    with app.test_request_context(json={"status": "inactive", "reason": "approved"}):
        g.administrator_request_context = context
        assert (
            _handler(policies.update_admin_policy_lifecycle)(UUID_TEXT).status_code
            == 200
        )
    monkeypatch.setattr(
        policies,
        "set_lifecycle",
        lambda **_: (_ for _ in ()).throw(policies.PolicyAdministrationError()),
    )
    with app.test_request_context(json={"status": "inactive", "reason": "approved"}):
        g.administrator_request_context = context
        assert (
            _handler(policies.update_admin_policy_lifecycle)(UUID_TEXT).status_code
            == 503
        )


@pytest.mark.parametrize(
    "handler, validator, error, expected",
    [
        (
            policies.assign_device_policy,
            "validate_assignment_request",
            policies.PolicyAssignmentRequestError(400),
            400,
        ),
        (
            policies.assign_device_policy,
            "replace_policy_assignment",
            policies.PolicyAssignmentNotFoundError(),
            404,
        ),
        (
            policies.assign_device_policy,
            "replace_policy_assignment",
            policies.PolicyAssignmentPersistenceError(),
            503,
        ),
        (
            policies.clear_device_policy,
            "validate_clear_request",
            policies.PolicyAssignmentRequestError(400),
            400,
        ),
        (
            policies.clear_device_policy,
            "clear_policy_assignment",
            policies.PolicyAssignmentConflictError(),
            409,
        ),
        (
            policies.clear_device_policy,
            "clear_policy_assignment",
            policies.PolicyAssignmentPersistenceError(),
            503,
        ),
    ],
)
def test_policy_assignment_routes_map_failures(
    app, monkeypatch, handler, validator, error, expected
):
    context = SimpleNamespace(
        administrator=SimpleNamespace(id=1, administrator_uuid=uuid4())
    )
    if (
        handler is policies.assign_device_policy
        and validator != "validate_assignment_request"
    ):
        monkeypatch.setattr(
            policies,
            "validate_assignment_request",
            lambda _: SimpleNamespace(
                policy_revision_uuid=str(uuid4()), reason="approved"
            ),
        )
    if (
        handler is policies.clear_device_policy
        and validator != "validate_clear_request"
    ):
        monkeypatch.setattr(policies, "validate_clear_request", lambda _: "approved")
    monkeypatch.setattr(
        policies,
        validator,
        lambda *args, error=error: (_ for _ in ()).throw(error),
    )
    with app.test_request_context(json={"reason": "approved"}):
        g.administrator_request_context = context
        assert _handler(handler)(UUID_TEXT).status_code == expected
