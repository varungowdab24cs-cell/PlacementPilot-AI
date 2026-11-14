from collections import defaultdict, deque
from threading import Lock
from time import monotonic


class AIRateLimitExceeded(Exception):
    def __init__(self, retry_after_seconds: int) -> None:
        self.retry_after_seconds = retry_after_seconds
        super().__init__("AI request rate limit exceeded")


class InMemoryRateLimiter:
    def __init__(self) -> None:
        self._requests: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check(self, key: str, limit: int, window_seconds: int = 60) -> None:
        now = monotonic()
        with self._lock:
            requests = self._requests[key]
            while requests and now - requests[0] >= window_seconds:
                requests.popleft()
            if len(requests) >= limit:
                retry_after = max(1, int(window_seconds - (now - requests[0])))
                raise AIRateLimitExceeded(retry_after)
            requests.append(now)


ai_rate_limiter = InMemoryRateLimiter()
