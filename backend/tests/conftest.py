from collections.abc import Iterator

import pytest
from flask import Flask

from app import create_app


@pytest.fixture()
def app() -> Iterator[Flask]:
    yield create_app("testing")
