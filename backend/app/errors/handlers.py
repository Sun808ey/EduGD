from flask import Flask, Response, jsonify
from werkzeug.exceptions import HTTPException


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(HTTPException)
    def handle_http_error(error: HTTPException) -> tuple[Response, int]:
        response = jsonify(
            {
                "error": error.name.lower(),
                "message": error.description,
            }
        )
        return response, error.code or 500

    @app.errorhandler(Exception)
    def handle_unexpected_error(error: Exception) -> tuple[Response, int]:
        app.logger.exception("Unhandled server error", exc_info=error)
        return jsonify({"error": "internal server error"}), 500
