from typing import Any, Dict, Optional

from flask import jsonify


# PUBLIC_INTERFACE
def error_response(
    status_code: int,
    message: str,
    *,
    code: Optional[int] = None,
    errors: Optional[Dict[str, Any]] = None,
):
    """
    Create a consistent JSON error response.

    Args:
      status_code: HTTP status code (e.g., 404).
      message: Human readable error message.
      code: Optional application error code (defaults to status_code).
      errors: Optional dict with field-level or structured error details.

    Returns:
      (json_response, status_code) tuple suitable for Flask return.
    """
    payload = {
        "code": int(code if code is not None else status_code),
        "status": str(status_code),
        "message": message,
        "errors": errors or {},
    }
    return jsonify(payload), status_code
