import os

from app import create_app
from app.deployment_identity import validate_deployment_identity

if (
    os.getenv("APP_ENV", "development").lower() == "production"
    or os.getenv("RAILWAY_ENVIRONMENT_ID")
    or os.getenv("EDUG_ENVIRONMENT")
):
    validate_deployment_identity(os.environ)

app = create_app()


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", "5000")),
    )
