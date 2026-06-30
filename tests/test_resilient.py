import asyncio
import time
import pytest
from src.backends.resilient import ResilientBackend, CircuitOpenError
from tests.fakes import SlowBackend, FailNTimes


async def test_timeout_fails_fast():
    g = ResilientBackend(SlowBackend(delay=2.0), timeout=0.2, retries=0)
    start = time.perf_counter()
    with pytest.raises(TimeoutError):
        await g.predict("hi")
    assert time.perf_counter() - start < 1.0   # gave up fast, didn't wait 2s


async def test_retry_recovers():
    fb = FailNTimes(fail_first_n=1)
    g = ResilientBackend(fb, timeout=1, retries=2, backoff=0.01)
    out = await g.predict("hi")
    assert out == "ok (call 2)"
    assert fb.calls == 2                        # failed once, succeeded on retry


async def test_circuit_opens_and_shields_backend():
    fb = FailNTimes(fail_first_n=100)           # always fails
    cb = ResilientBackend(fb, timeout=1, retries=0, failure_threshold=2, cooldown=5)
    for _ in range(2):
        with pytest.raises(Exception):
            await cb.predict("hi")
    assert cb.state == "open"
    calls_before = fb.calls
    with pytest.raises(CircuitOpenError):       # fast-fail
        await cb.predict("hi")
    assert fb.calls == calls_before             # backend was NOT called -> shielded


async def test_circuit_recovers_after_cooldown():
    fb = FailNTimes(fail_first_n=2)
    cb = ResilientBackend(fb, timeout=1, retries=0, failure_threshold=2, cooldown=0.2)
    for _ in range(2):
        with pytest.raises(Exception):
            await cb.predict("hi")
    assert cb.state == "open"
    await asyncio.sleep(0.25)                    # wait out the cooldown
    out = await cb.predict("hi")                 # half-open trial succeeds
    assert cb.state == "closed"
    assert out.startswith("ok")
