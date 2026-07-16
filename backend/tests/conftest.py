from collections.abc import Iterator

import pytest
from flask import Flask
from flask_migrate import upgrade

from app import create_app
from app.extensions import db


@pytest.fixture()
def app() -> Iterator[Flask]:
    application = create_app("testing")
    with application.app_context():
        upgrade()

    yield application

    with application.app_context():
        db.session.remove()
