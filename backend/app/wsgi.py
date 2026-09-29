"""Production WSGI entrypoint with deployment-identity validation."""

import os

from app import create_app
from app.deployment_identity import validate_deployment_identity


validate_deployment_identity(os.environ)
app = create_app("production")
