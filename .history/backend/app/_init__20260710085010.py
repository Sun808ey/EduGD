from .routes.devices import device_bp


app.register_blueprint(
device_bp,
url_prefix="/api"
)