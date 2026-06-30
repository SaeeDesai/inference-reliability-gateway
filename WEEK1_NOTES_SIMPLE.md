# Week 1 — Notes (Plain + Technical)

**What we're building:** a *gateway* — a program that sits in front of AI models and
handles all the messy real-world stuff (waiting, failures, picking a model, tracking).
Think "a really good waiter standing between customers and the kitchen." This week we
build the basic waiter: take an order, talk to the kitchen, don't freeze when it's slow.

The real terms are kept (and **bolded**) so you can use them in interviews — but each one
gets a plain explanation.

---

## 1. The Backend abstraction (one shape every model fits)

**Plain idea:** instead of writing custom code for each AI model, you decide on *one shape*
that every model must fit, and the rest of your app only ever talks to that shape.

- **The shape** is an **abstract base class** (`abc.ABC`) called `Backend` with one required
  method: `async def predict(prompt) -> str`. "Abstract" = it's a template, not usable on its
  own; real models fill it in.
- Each real model (mock, small LLM, big LLM) is a **subclass** that implements `predict`.
  Because they all share the shape, your app can use any of them the same way — that's
  **polymorphism** (one interface, many implementations).
- **dependency inversion** = a fancy name for the rule "depend on the *shape*, not on a
  *specific model*." Your gateway code points at `Backend`, never at "Groq" directly.
- **Why it matters / what breaks without it:** without the shape, your code gets glued to one
  model. Swapping models = rewriting everything. With it, adding or switching a model is a
  tiny, local change. (This is *why* next week's router is easy.)
- **Bonus:** Python *enforces* the shape — if a subclass forgets `predict`, Python refuses to
  create it. The contract is checked automatically.

## 2. The web framework — FastAPI (and why not Flask)

**Plain idea:** a **web framework** is pre-built machinery so your program can receive
requests over the internet and send back answers, without you coding all that from scratch.

- Two styles exist. **WSGI** is the older, **synchronous** style (Flask). One worker handles
  **one request at a time**. **ASGI** is the newer, **async** style (FastAPI). One worker can
  juggle **many requests at once**.
- FastAPI runs on top of **Starlette** (the ASGI engine) and is served by **uvicorn** (the
  thing that actually runs it — you saw `server: uvicorn` in your response).
- **Why FastAPI for us:** our gateway spends almost all its time *waiting* on slow AI models
  (this is called being **I/O-bound**). The async style shines exactly here. Plus FastAPI
  gives you **Pydantic** (auto-checks incoming requests are valid) and the free **/docs** page
  you just used.
- **Interview-ready sentence:** *"I chose FastAPI over Flask because the work is I/O-bound on
  backend calls, so an async (ASGI) stack handles far more requests per worker."*

## 3. Async / await (the most important idea this week)

**Plain idea:** "async" = *don't sit around doing nothing while waiting.* Hand off the slow
task, go help someone else, come back when it's ready.

- A function written `async def` is a **coroutine** — a task that can pause and resume.
- The word **`await`** means "this part is slow (a network call) — pause me here, go run other
  waiting tasks, wake me when the answer's ready." The thing managing all this hand-off is the
  **event loop**.
- **Key truth (people get this wrong):** async does **not** make a single call faster. It just
  stops your program from idling while it waits, so *many* waiting requests overlap. Result:
  **throughput goes up** (more requests handled per second), but one request isn't quicker.
- **When async helps:** **I/O-bound** work — waiting on network, disk, APIs (← that's us).
  **When it doesn't:** **CPU-bound** work — heavy number-crunching. (Side note: Python's **GIL**
  means real CPU parallelism needs multiple *processes*, not async.) Knowing which kind of work
  you have is the whole decision.
- **Contagion rule:** once a path is async, everything it waits on must also be async — one
  old "blocking" call freezes the event loop and cancels the benefit. (That's the next point.)

- **📊 My result (Day 3):** 20 concurrent 0.5s calls → 0.50s async vs 10.07s blocking =
20.1× throughput (39.9 vs 2.0 req/s). Proof, not theory.

## 4. Talking to the kitchen — httpx, not requests

**Plain idea:** to call the AI models you need an HTTP client (a "phone"). The popular one,
**`requests`**, makes you hold the line until the call finishes — that *blocks* everything and
ruins async. So we use **`httpx`**, whose `AsyncClient` lets you `await` the call and do other
work meanwhile.

- Bonus: httpx does **connection pooling** (reuses open connections to a backend instead of
  re-dialing every time) — a bit faster and lighter.
- **Rule:** async app → async client. Never drop a blocking call into an async path.

## 5. Surviving failure (resilience patterns)

**Plain idea:** AI backends *will* be slow or fail sometimes. These three small skills keep one
bad backend from sinking the whole service.

- **Timeout** — "if no answer in X seconds, give up and return an error" instead of waiting
  forever. *Without it: one stuck call hangs that request indefinitely.*
- **Retry with exponential backoff (+ jitter)** — if a call fails, try again, but wait longer
  each time (1s, 2s, 4s…) so you don't pile onto a struggling backend. **jitter** = add a little
  randomness so all clients don't retry at the exact same instant (that pile-up is called a
  **thundering herd**). *Without it: you either give up too early, or you hammer a backend
  that's already hurting.*
- **Circuit breaker** — if a backend just failed many times in a row, stop calling it for a
  bit. Three states:
  - **Closed** = healthy, calls go through (normal).
  - **Open** = "it's clearly down" — skip it, fail fast or use a backup, for a short cooldown.
  - **Half-open** = after cooldown, send *one* test call; if it works → back to Closed, if not →
    back to Open.
  *Without it: a dead backend makes every new request wait through the same failure — that
  pile-up is a **cascading failure**, and it's how whole systems collapse.*
- *(Worth name-dropping:)* **bulkhead** — keep each backend's resources separate so one
  overloaded backend can't drown the others (like watertight compartments in a ship).

## 6. Testing — mocks and pytest

**Plain idea:** before "opening", automatically check the waiter still behaves — and use a
*fake* backend so tests are instant, free, and offline.

- **mock / fake / stub** = a stand-in for the real thing. Your `MockBackend` returns a fixed
  answer immediately, so tests don't need the internet, an API key, or money, and always give
  the same result (**deterministic**).
- **pytest** = the tool that runs your tests. **Unit tests** check one piece in isolation (with
  mocks); an **integration test** checks the whole app end-to-end via an in-memory client.
- **Why it matters:** code with no tests reads as "student". A test suite you re-run on every
  change is a basic professional expectation.

## 7. Packaging — Docker

**Plain idea:** Docker fixes "but it works on *my* laptop." It packs your app + its exact
dependencies into a sealed box that runs the same everywhere.

- **image** = the sealed box (a frozen snapshot of app + dependencies). **container** = a
  running copy of that box.
- **Dockerfile** = the recipe to build the image (pick a base, install deps, copy code, set the
  start command).
- **multi-stage build** = build in one stage, then copy only what's needed to *run* into a final
  clean stage — so the shipped image is small and has no leftover build tools.
- **Why:** **environment parity** — the exact thing you test locally is the exact thing that
  runs in the cloud (Week 4). No surprises.

---

## Tool choices (why this, not that)

| Tool | Its job | Picked over | Why |
|---|---|---|---|
| FastAPI | receive web requests | Flask | async-native, auto-validation, free docs page |
| uvicorn | run the FastAPI app | gunicorn (sync) | runs the async event loop |
| httpx (AsyncClient) | call the AI backends | requests | can `await` (won't freeze the loop) + connection pooling |
| Pydantic | check request/response shape | manual `dict` checks | automatic validation + clear contracts |
| pytest | run the tests | unittest | simpler, popular, great tooling |
| Docker | package the app | "just run it on the laptop" | same everywhere; matches the cloud |

---

## Done with Week 1 when…

1. `POST /v1/infer` and `GET /health` work, with requests validated by Pydantic. ✅ (you're here)
2. Requests go through the `Backend` shape to a `MockBackend` — and by week's end, a real model too.
3. Backend calls have **timeout + retry + a basic circuit breaker**.
4. A **pytest** suite passes (a few unit tests + one integration test).
5. It builds and runs from a **multi-stage Dockerfile**.
6. You have a real **async-vs-sync throughput number** written down for the report.

---

## Glossary (term → plain meaning)

- **abstract base class (ABC)** — a template class you can't use directly; subclasses fill it in.
- **abstract method** — a method the template *requires* every subclass to implement.
- **dependency inversion** — depend on the general shape, not a specific thing.
- **polymorphism** — many different objects usable through one shared interface.
- **WSGI / ASGI** — old synchronous / new asynchronous Python web standards.
- **uvicorn** — the server that runs your async (ASGI) app.
- **coroutine** — an `async def` task that can pause and resume.
- **event loop** — the manager that juggles paused/awaiting tasks.
- **`await`** — "pause here while this slow thing finishes; go do other work."
- **async ≠ parallelism** — async overlaps *waiting*, it doesn't run code at the same time.
- **I/O-bound vs CPU-bound** — limited by *waiting* (network/disk) vs by *computing* (math).
- **GIL** — Python's lock that stops true multi-core threading (use processes for CPU work).
- **connection pooling** — reuse open network connections instead of re-opening each time.
- **timeout** — give up waiting after a set time.
- **exponential backoff** — wait longer between each retry.
- **jitter** — small randomness added to retry timing to avoid synchronized pile-ups.
- **thundering herd** — many clients hitting a backend at the same instant.
- **circuit breaker** — stop calling a failing backend until it recovers (closed/open/half-open).
- **cascading failure** — one failure dragging down the whole system.
- **bulkhead** — isolating resources so one failure can't sink everything.
- **mock / fake / stub** — a stand-in for a real dependency in tests.
- **unit vs integration test** — test one piece alone vs test the whole thing together.
- **image vs container** — the frozen app box vs a running copy of it.
- **Dockerfile** — the recipe to build the image.
- **multi-stage build** — build in one stage, ship only the slim runtime stage.
- **environment parity** — local and production run the exact same thing.
