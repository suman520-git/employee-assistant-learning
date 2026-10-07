import math
import time
from collections import defaultdict, deque
from threading import Lock

from fastapi import HTTPException


LIMITS = {
    "/ask": 5,
    "/search": 10,
    "/documents": 20
}

request_times = defaultdict(deque)
rate_lock = Lock()


def check_rate_limit(user_id, path):
    # Document entry, listing, and upload share one limit.
    if path == "/documents/upload":
        path = "/documents"

    limit = LIMITS.get(path)

    if limit is None:
        return

    key = (user_id, path)

    # Prevent simultaneous requests from changing the counter together.
    with rate_lock:
        now = time.monotonic()
        timestamps = request_times[key]

        # Remove requests older than the 60-second window.
        while timestamps and timestamps[0] <= now - 60:
            timestamps.popleft()

        if len(timestamps) >= limit:
            retry_after = max(
                1,
                math.ceil(60 - (now - timestamps[0]))
            )

            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Please try again later.",
                headers={"Retry-After": str(retry_after)}
            )

        timestamps.append(now)