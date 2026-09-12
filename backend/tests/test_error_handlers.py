from flask import Flask


def test_http_errors_use_stable_nested_error_contract(app: Flask) -> None:
    not_found = app.test_client().get("/api/v1/does-not-exist")
    method_not_allowed = app.test_client().get("/api/v1/devices/register")

    assert not_found.status_code == 404
    assert not_found.get_json() == {
        "error": {
            "code": "http_404",
            "message": "The requested URL was not found on the server. If you entered the URL manually please check your spelling and try again.",
        }
    }
    assert method_not_allowed.status_code == 405
    assert method_not_allowed.get_json()["error"]["code"] == "http_405"


def test_unexpected_errors_use_safe_nested_error_contract(app: Flask) -> None:
    @app.get("/api/v1/test-unexpected-error")
    def raise_unexpected_error() -> None:
        raise RuntimeError("secret database details")

    response = app.test_client().get("/api/v1/test-unexpected-error")

    assert response.status_code == 500
    assert response.get_json() == {
        "error": {
            "code": "internal_server_error",
            "message": "internal server error",
        }
    }