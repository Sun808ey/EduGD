"""One-school registration service for the administrator panel."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.extensions import db
from app.models import Administrator, School


class SchoolRegistrationError(RuntimeError):
    pass


class SchoolAlreadyRegistered(SchoolRegistrationError):
    pass


class SchoolRegistrationUnavailable(SchoolRegistrationError):
    pass


SUPPORTED_SCHOOL_TIMEZONES = frozenset({"Africa/Kampala", "Africa/Nairobi", "UTC"})


def _validate_payload(payload: dict[str, object]) -> None:
    timezone = payload.get("timezone")
    if not isinstance(timezone, str) or not timezone.strip():
        raise SchoolRegistrationError("timezone is required")
    if timezone not in SUPPORTED_SCHOOL_TIMEZONES:
        raise SchoolRegistrationError("invalid school timezone")


def get_school() -> School | None:
    try:
        return db.session.scalar(select(School).where(School.singleton_key == "1"))
    except SQLAlchemyError as error:
        db.session.rollback()
        raise SchoolRegistrationUnavailable("school could not be read") from error


def register_school(*, payload: dict[str, object], administrator_id: int) -> School:
    _validate_payload(payload)
    try:
        school = School(
            name=payload["name"],
            district=payload["district"],
            school_type=payload["school_type"],
            contact_person=payload["contact_person"],
            official_telephone=payload["official_telephone"],
            official_email=payload["official_email"],
            physical_location=payload["physical_location"],
            authorised_administrator_name=payload["authorised_administrator_name"],
            timezone=payload["timezone"],
            registered_by_administrator_id=administrator_id,
        )
    except (KeyError, TypeError, ValueError) as error:
        raise SchoolRegistrationError("invalid school registration") from error
    try:
        existing = db.session.scalar(
            select(School).where(School.singleton_key == "1").with_for_update()
        )
        if existing is not None:
            raise SchoolAlreadyRegistered("a school is already registered")
        administrator = db.session.get(Administrator, administrator_id)
        if administrator is None or administrator.status != "active":
            raise SchoolRegistrationError("administrator is unavailable")
        school.registered_by_administrator_id = administrator.id
        db.session.add(school)
        db.session.commit()
        return school
    except SchoolRegistrationError:
        db.session.rollback()
        raise
    except IntegrityError as error:
        db.session.rollback()
        raise SchoolAlreadyRegistered(
            "school registration conflicts with existing state"
        ) from error
    except SQLAlchemyError as error:
        db.session.rollback()
        raise SchoolRegistrationUnavailable("school could not be registered") from error


def update_school(*, payload: dict[str, object], administrator_id: int) -> School:
    _validate_payload(payload)
    try:
        school = db.session.scalar(
            select(School).where(School.singleton_key == "1").with_for_update()
        )
        administrator = db.session.get(Administrator, administrator_id)
        if school is None or administrator is None or administrator.status != "active":
            raise SchoolRegistrationError("school or administrator is unavailable")
        for field in (
            "name",
            "district",
            "school_type",
            "contact_person",
            "official_telephone",
            "official_email",
            "physical_location",
            "authorised_administrator_name",
            "timezone",
        ):
            setattr(school, field, payload[field])
        db.session.commit()
        return school
    except SchoolRegistrationError:
        db.session.rollback()
        raise
    except (IntegrityError, SQLAlchemyError) as error:
        db.session.rollback()
        raise SchoolRegistrationUnavailable("school could not be updated") from error
