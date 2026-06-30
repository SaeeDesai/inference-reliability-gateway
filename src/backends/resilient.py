import asyncio
import random
import time
from src.backends.base import Backend


class CircuitOpenError(Exception):
    """Raised when the circuit is open: we fail fast instead of calling a dead backend."""


class ResilientBackend(Backend):
    """Wraps any Backend and adds timeout + retry/backoff + a circuit breaker."""

    def __init__(self, inner: Backend, timeout: float = 15.0, retries: int = 2,
                 backoff: float = 0.5, failure_threshold: int = 3, cooldown: float = 10.0):
        self.inner = inner
        self.name = inner.name            # transparent: same name as the wrapped backend
        self.timeout = timeout            # max seconds to wait per attempt
        self.retries = retries            # extra attempts after the first
        self.backoff = backoff            # base backoff seconds (doubles each retry)
        self.failure_threshold = failure_threshold  # failures before the circuit opens
        self.cooldown = cooldown          # seconds to stay open before a trial

        # circuit breaker state
        self.state = "closed"             # closed -> open -> half_open -> closed
        self.failures = 0
        self.opened_at = None

    def _cooldown_elapsed(self) -> bool:
        return self.opened_at is not None and (time.monotonic() - self.opened_at) >= self.cooldown

    def _record_success(self) -> None:
        self.failures = 0
        self.state = "closed"
        self.opened_at = None

    def _record_failure(self) -> None:
        self.failures += 1
        # a failure while testing recovery (half_open), or too many in a row, opens the circuit
        if self.state == "half_open" or self.failures >= self.failure_threshold:
            self.state = "open"
            self.opened_at = time.monotonic()
            self.failures = 0

    async def predict(self, prompt: str) -> str:
        # 1) Circuit gate: if open, fail fast (unless the cooldown has passed -> trial)
        if self.state == "open":
            if self._cooldown_elapsed():
                self.state = "half_open"        # allow ONE trial request through
            else:
                raise CircuitOpenError(f"{self.name} circuit is open")

        # 2) Try, with timeout + retries
        last_exc = None
        for attempt in range(self.retries + 1):
            try:
                result = await asyncio.wait_for(self.inner.predict(prompt), self.timeout)
                self._record_success()
                return result
            except Exception as e:
                last_exc = e
                if attempt < self.retries:
                    delay = self.backoff * (2 ** attempt) + random.uniform(0, 0.05)  # backoff + jitter
                    await asyncio.sleep(delay)

        # 3) All attempts failed -> record it (may open the circuit) and surface the error
        self._record_failure()
        raise last_exc
