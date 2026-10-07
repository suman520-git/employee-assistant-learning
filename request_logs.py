from database import get_connection


def save_request_log(user_id, method, path, status_code, duration_ms):
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO api_request_logs (
                user_id, method, path, status_code, duration_ms
            )
            VALUES (%s, %s, %s, %s, %s)
            """,
            (user_id, method, path, status_code, duration_ms)
        )