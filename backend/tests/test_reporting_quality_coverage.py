from __future__ import annotations

from datetime import UTC, date, datetime
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from flask import g
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

import app.routes.incidents as incident_routes
import app.routes.logs as logs
import app.services.incidents as incidents
import app.services.school_registration as school_registration
import app.services.violation_reports as violations
from app.admin_api import Pagination
from app.extensions import db
from app.models import Administrator, Device, Incident
from app.services.administrator_authentication import bootstrap_administrator


def test_incident_service_lifecycle_and_validation(app) -> None:
    with app.app_context():
        bootstrap_administrator(
            username="incident.service",
            display_name="Incident Service Administrator",
            password="IncidentService!2026",
            operator_subject="test:incident-service",
            reason="incident service fixture",
        )
        administrator = db.session.execute(select(Administrator)).scalar_one()
        device = Device(device_uuid=uuid4(), android_version="10", api_level=29)
        db.session.add(device)
        db.session.commit()

        with pytest.raises(incidents.IncidentValidationError):
            incidents.create_incident(
                device_uuid=device.device_uuid,
                incident_type="not-a-type",
                description="description",
                reported_by="teacher",
                responsible_person=None,
                administrator=administrator,
            )
        with pytest.raises(incidents.IncidentValidationError):
            incidents.create_incident(
                device_uuid=device.device_uuid,
                incident_type="device_missing",
                description="\n",
                reported_by="teacher",
                responsible_person=None,
                administrator=administrator,
            )
        with pytest.raises(incidents.IncidentNotFoundError):
            incidents.create_incident(
                device_uuid=uuid4(),
                incident_type="device_missing",
                description="Device was not returned",
                reported_by="teacher",
                responsible_person=None,
                administrator=administrator,
            )

        created = incidents.create_incident(
            device_uuid=device.device_uuid,
            incident_type="device_missing",
            description="Device was not returned",
            reported_by="teacher",
            responsible_person="ICT officer",
            administrator=administrator,
        )
        assert created["status"] == "OPEN"
        page = incidents.list_incidents(
            Pagination(page=1, per_page=10, offset=0),
            device_uuid=device.device_uuid,
        )
        assert len(page.items) == 1

        closed = incidents.update_incident(
            UUID(str(created["incident_uuid"])),
            status="CLOSED",
            action_taken="Device was recovered",
            responsible_person="ICT officer",
            administrator=administrator,
        )
        assert closed["status"] == "CLOSED"
        row = db.session.execute(select(Incident)).scalar_one()
        with pytest.raises(incidents.IncidentConflictError):
            incidents.update_incident(
                row.incident_uuid,
                status="OPEN",
                action_taken=None,
                responsible_person=None,
                administrator=administrator,
            )
        second = incidents.create_incident(
            device_uuid=device.device_uuid,
            incident_type="device_offline",
            description="Device did not check in",
            reported_by="teacher",
            responsible_person=None,
            administrator=administrator,
        )
        with pytest.raises(incidents.IncidentValidationError):
            incidents.update_incident(
                UUID(str(second["incident_uuid"])),
                status="CLOSED",
                action_taken=None,
                responsible_person=None,
                administrator=administrator,
            )
        with pytest.raises(incidents.IncidentNotFoundError):
            incidents.update_incident(
                uuid4(),
                status="OPEN",
                action_taken=None,
                responsible_person=None,
                administrator=administrator,
            )


def test_incident_service_maps_database_failures(app, monkeypatch) -> None:
    with app.app_context():

        class FailingSession:
            def scalar(self, _statement):
                raise SQLAlchemyError("read failure")

            def scalars(self, _statement):
                raise SQLAlchemyError("read failure")

            def rollback(self):
                return None

        monkeypatch.setattr(incidents, "db", SimpleNamespace(session=FailingSession()))
        with pytest.raises(incidents.IncidentPersistenceError):
            incidents.list_incidents(Pagination(page=1, per_page=10, offset=0))


def test_school_service_update_and_error_paths(app, monkeypatch) -> None:
    with app.app_context():
        bootstrap_administrator(
            username="school.service",
            display_name="School Service Administrator",
            password="SchoolService!2026",
            operator_subject="test:school-service",
            reason="school service fixture",
        )
        administrator = db.session.execute(select(Administrator)).scalar_one()
        payload = {
            "name": "Coverage School",
            "district": "Kampala",
            "school_type": "Secondary",
            "contact_person": "ICT Officer",
            "official_telephone": "+256 700 000 000",
            "official_email": "ict@coverage.example",
            "physical_location": "Kampala",
            "authorised_administrator_name": "School Service Administrator",
            "timezone": "Africa/Kampala",
        }
        with pytest.raises(school_registration.SchoolRegistrationError):
            school_registration.register_school(
                payload={**payload, "timezone": "Mars"},
                administrator_id=administrator.id,
            )
        school = school_registration.register_school(
            payload=payload, administrator_id=administrator.id
        )
        updated = school_registration.update_school(
            payload={**payload, "name": "Updated Coverage School", "timezone": "UTC"},
            administrator_id=administrator.id,
        )
        assert updated.name == "Updated Coverage School"
        assert updated.timezone == "UTC"
        assert school is updated
        with pytest.raises(school_registration.SchoolAlreadyRegistered):
            school_registration.register_school(
                payload=payload, administrator_id=administrator.id
            )

        monkeypatch.setattr(
            school_registration.db.session,
            "scalar",
            lambda _statement: (_ for _ in ()).throw(SQLAlchemyError("offline")),
        )
        with pytest.raises(school_registration.SchoolRegistrationUnavailable):
            school_registration.get_school()


def test_school_service_rejects_missing_administrator_and_invalid_payload(app) -> None:
    with app.app_context():
        payload = {
            "name": "Coverage School",
            "district": "Kampala",
            "school_type": "Secondary",
            "contact_person": "ICT Officer",
            "official_telephone": "+256 700 000 000",
            "official_email": None,
            "physical_location": "Kampala",
            "authorised_administrator_name": "Administrator",
            "timezone": "Africa/Kampala",
        }
        with pytest.raises(school_registration.SchoolRegistrationError):
            school_registration.register_school(
                payload={"timezone": "UTC"}, administrator_id=999
            )
        with pytest.raises(school_registration.SchoolRegistrationError):
            school_registration.update_school(payload=payload, administrator_id=999)
        with pytest.raises(school_registration.SchoolRegistrationError):
            school_registration.register_school(
                payload={**payload, "timezone": ""}, administrator_id=999
            )
        with pytest.raises(school_registration.SchoolRegistrationError):
            school_registration.register_school(payload=payload, administrator_id=999)


def test_school_service_maps_registration_database_failure(app, monkeypatch) -> None:
    with app.app_context():
        bootstrap_administrator(
            username="school.db",
            display_name="School Database Administrator",
            password="SchoolDatabase!2026",
            operator_subject="test:school-db",
            reason="school database fixture",
        )
        administrator = db.session.execute(select(Administrator)).scalar_one()
        payload = {
            "name": "Database School",
            "district": "Kampala",
            "school_type": "Secondary",
            "contact_person": "ICT Officer",
            "official_telephone": "+256 700 000 000",
            "official_email": None,
            "physical_location": "Kampala",
            "authorised_administrator_name": "Administrator",
            "timezone": "UTC",
        }
        monkeypatch.setattr(
            db.session,
            "commit",
            lambda: (_ for _ in ()).throw(SQLAlchemyError("offline")),
        )
        with pytest.raises(school_registration.SchoolRegistrationUnavailable):
            school_registration.register_school(
                payload=payload, administrator_id=administrator.id
            )


def test_school_service_maps_integrity_and_update_failures(app, monkeypatch) -> None:
    with app.app_context():
        bootstrap_administrator(
            username="school.errors",
            display_name="School Error Administrator",
            password="SchoolErrors!2026",
            operator_subject="test:school-errors",
            reason="school error fixture",
        )
        administrator = db.session.execute(select(Administrator)).scalar_one()
        payload = {
            "name": "Error School",
            "district": "Kampala",
            "school_type": "Secondary",
            "contact_person": "ICT Officer",
            "official_telephone": "+256 700 000 000",
            "official_email": None,
            "physical_location": "Kampala",
            "authorised_administrator_name": "Administrator",
            "timezone": "UTC",
        }
        monkeypatch.setattr(
            db.session,
            "commit",
            lambda: (_ for _ in ()).throw(IntegrityError("statement", {}, None)),
        )
        with pytest.raises(school_registration.SchoolAlreadyRegistered):
            school_registration.register_school(
                payload=payload, administrator_id=administrator.id
            )


def test_school_service_maps_update_database_failure(app, monkeypatch) -> None:
    with app.app_context():
        bootstrap_administrator(
            username="school.update",
            display_name="School Update Administrator",
            password="SchoolUpdate!2026",
            operator_subject="test:school-update",
            reason="school update fixture",
        )
        administrator = db.session.execute(select(Administrator)).scalar_one()
        payload = {
            "name": "Update School",
            "district": "Kampala",
            "school_type": "Secondary",
            "contact_person": "ICT Officer",
            "official_telephone": "+256 700 000 000",
            "official_email": None,
            "physical_location": "Kampala",
            "authorised_administrator_name": "Administrator",
            "timezone": "UTC",
        }
        school_registration.register_school(
            payload=payload, administrator_id=administrator.id
        )
        monkeypatch.setattr(
            db.session,
            "commit",
            lambda: (_ for _ in ()).throw(SQLAlchemyError("offline")),
        )
        with pytest.raises(school_registration.SchoolRegistrationUnavailable):
            school_registration.update_school(
                payload=payload, administrator_id=administrator.id
            )


def test_violation_filters_summary_and_persistence_paths(app, monkeypatch) -> None:
    device_uuid = uuid4()
    filters = violations.build_filters(
        device_uuid=str(device_uuid),
        class_name="  Senior One ",
        from_date="2026-09-01",
        to_date="2026-09-30",
    )
    assert filters.device_uuid == device_uuid
    assert filters.class_name == "Senior One"
    assert filters.from_date == date(2026, 9, 1)
    with pytest.raises(ValueError):
        violations.build_filters(
            device_uuid="not-a-uuid", class_name=None, from_date=None, to_date=None
        )
    with pytest.raises(ValueError):
        violations.build_filters(
            device_uuid=None,
            class_name="x" * 121,
            from_date="2026-09-01",
            to_date="2026-08-01",
        )
    assert violations._violation_type("unknown_event") == "Unknown Event"

    now = datetime(2026, 9, 20, 12, tzinfo=UTC)
    event = SimpleNamespace(
        event_uuid=uuid4(),
        policy_uuid=None,
        revision_uuid=None,
        event_code="web_filter_blocked",
        outcome="blocked",
        rule_id="web-filter",
        event_metadata={"domain_hash": "hash", "ignored": "value"},
        occurred_at=now,
        received_at=now,
        sequence=2,
        event_hash=b"event-hash",
        previous_event_hash=None,
    )
    device = SimpleNamespace(device_uuid=device_uuid, asset_number="TAB-01", id=1)
    assignment = SimpleNamespace(target_name="Senior One")

    class Session:
        def query(self, _column):
            return SimpleNamespace(
                filter=lambda *args: SimpleNamespace(exists=lambda: True)
            )

        def scalar(self, _statement):
            return None

        def scalars(self, _statement):
            return SimpleNamespace(first=lambda: assignment)

        def execute(self, _statement):
            return SimpleNamespace(all=lambda: [(event, device)])

    monkeypatch.setattr(violations, "db", SimpleNamespace(session=Session()))
    summary = violations.all_violations(filters)
    assert summary[0]["class_name"] == "Senior One"
    assert summary[0]["details"] == {"domain_hash": "hash"}
    listed, pagination = violations.list_violations(
        Pagination(page=1, per_page=10, offset=0), filters
    )
    assert len(listed) == 1
    assert pagination["total"] == 0

    class FailingSession:
        def query(self, _column):
            return SimpleNamespace(
                filter=lambda *args: SimpleNamespace(exists=lambda: True)
            )

        def execute(self, _statement):
            raise SQLAlchemyError("offline")

        def scalar(self, _statement):
            raise SQLAlchemyError("offline")

    monkeypatch.setattr(violations, "db", SimpleNamespace(session=FailingSession()))
    with pytest.raises(violations.ViolationReportPersistenceError):
        violations.all_violations(filters)
    with pytest.raises(violations.ViolationReportPersistenceError):
        violations.list_violations(Pagination(page=1, per_page=10, offset=0), filters)


def test_logs_routes_map_report_errors_and_csv(app, monkeypatch) -> None:
    def handler(function):
        return function.__wrapped__.__wrapped__

    context = SimpleNamespace(administrator=SimpleNamespace(id=1))
    with app.test_request_context("/admin/reports/violations"):
        monkeypatch.setattr(
            logs,
            "list_violations",
            lambda *_: (_ for _ in ()).throw(
                logs.ViolationReportPersistenceError("offline")
            ),
        )
        g.administrator_request_context = context
        assert handler(logs.violation_report)().status_code == 503

    with app.test_request_context("/admin/reports/violations.csv"):
        monkeypatch.setattr(
            logs,
            "all_violations",
            lambda *_: [
                {
                    "event_uuid": "event",
                    "device_uuid": "device",
                    "asset_number": "TAB-01",
                    "class_name": None,
                    "occurred_at": "2026-09-20T12:00:00+00:00",
                    "violation_type": "Blocked web domain",
                    "event_code": "web_filter_blocked",
                    "outcome": "blocked",
                    "rule_id": "filter",
                    "policy_name": None,
                    "policy_version": None,
                    "details": {"domain_hash": "hash"},
                    "sequence": 1,
                    "event_hash": "hash",
                }
            ],
        )
        g.administrator_request_context = context
        response = handler(logs.violation_report_csv)()
        assert response.status_code == 200
        assert "edugd-violations.csv" in response.headers["Content-Disposition"]
        assert "web_filter_blocked" in response.get_data(as_text=True)


def test_logs_audit_and_policy_routes_map_request_and_storage_errors(
    app, monkeypatch
) -> None:
    def handler(function):
        return function.__wrapped__.__wrapped__

    context = SimpleNamespace(administrator=SimpleNamespace(id=1))
    for function, target, error in [
        (logs.audit_events, "list_audit_events", logs.AdminRequestError("bad", "bad")),
        (logs.policy_changes, "list_policy_changes", logs.AdminReadPersistenceError()),
    ]:
        monkeypatch.setattr(
            logs,
            target,
            lambda *args, error=error, **kwargs: (_ for _ in ()).throw(error),
        )
        with app.test_request_context("/admin/logs"):
            g.administrator_request_context = context
            assert handler(function)().status_code in {400, 503}
    with app.test_request_context("/admin/reports/violations?from=bad"):
        g.administrator_request_context = context
        assert handler(logs.violation_report)().status_code == 400
    with app.test_request_context("/admin/reports/violations.csv?to=bad"):
        g.administrator_request_context = context
        assert handler(logs.violation_report_csv)().status_code == 400


def test_incident_read_routes_map_filters_and_storage_errors(app, monkeypatch) -> None:
    def handler(function):
        return function.__wrapped__.__wrapped__

    context = SimpleNamespace(administrator=SimpleNamespace(id=1))
    monkeypatch.setattr(
        incident_routes,
        "list_incidents",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            incident_routes.IncidentPersistenceError("offline")
        ),
    )
    with app.test_request_context("/admin/incidents"):
        g.administrator_request_context = context
        assert handler(incident_routes.admin_incidents)().status_code == 503
    with app.test_request_context("/admin/devices/not-a-uuid/incidents"):
        g.administrator_request_context = context
        assert (
            handler(incident_routes.admin_device_incidents)("not-a-uuid").status_code
            == 400
        )
