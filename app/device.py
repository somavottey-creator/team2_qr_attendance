"""
Device identity utilities.
A device is identified by a stable cookie stored in the browser.
Falls back to IP address if the cookie is missing.
"""

import uuid
from flask import request, make_response


DEVICE_COOKIE_NAME = "attendance_device_id"
COOKIE_MAX_AGE = 60 * 60 * 24 * 365 * 5  # 5 years


def get_device_id(request_obj=None) -> str:
    """
    Read the device ID from the request cookie.
    If absent, one will be generated and must be set on the response.
    """
    req = request_obj or request
    device_id = req.cookies.get(DEVICE_COOKIE_NAME)
    if not device_id:
        device_id = str(uuid.uuid4())
    return device_id


def set_device_cookie(response, device_id: str):
    """Attach the device-id cookie to an outgoing response."""
    response.set_cookie(
        DEVICE_COOKIE_NAME,
        device_id,
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        samesite="Lax"
    )
    return response
