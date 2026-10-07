import os
import secrets

from fastapi import Depends, HTTPException, Request
from fastapi.security import APIKeyHeader
from psycopg import Error as DatabaseError

from database import get_connection

from rate_limit import check_rate_limit


APP_API_KEY = os.environ["APP_API_KEY"]
APP_USERNAME = os.environ["APP_USERNAME"]

if not APP_API_KEY.strip():
    raise RuntimeError("APP_API_KEY must not be empty.")

api_key_header = APIKeyHeader(
    name="X-API-Key",
    auto_error=False
)


def authenticate(
    request: Request,
    api_key: str | None = Depends(api_key_header)
):
    # Allow health checks without authentication.
    if request.url.path == "/health":
        return None

    if api_key is None or not secrets.compare_digest(
        api_key.encode("utf-8"),
        APP_API_KEY.encode("utf-8")
    ):
        raise HTTPException(
            status_code=401,
            detail="Missing or invalid API key."
        )

    # Associate this application key with the configured user.
    try:
        with get_connection() as connection:
            user = connection.execute(
                """
                SELECT id, username
                FROM users
                WHERE username = %s
                """,
                (APP_USERNAME,)
            ).fetchone()
    except DatabaseError as error:
        print("Authentication database error:", type(error).__name__)

        raise HTTPException(
            status_code=503,
            detail="Authentication is temporarily unavailable."
        ) from error

    if user is None:
        raise HTTPException(
            status_code=503,
            detail="The application user is not configured."
        )

    # We will use this later when recording request logs.
        request.state.user_id = user["id"]
    request.state.user_id = user["id"]
    check_rate_limit(
        user_id=user["id"],
        path=request.url.path
    )

    return user