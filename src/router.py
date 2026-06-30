import re
from dataclasses import dataclass
from src.backends.base import Backend


@dataclass
class RouteDecision:
    tier: str          # "small" or "large"
    score: int
    reasons: list


@dataclass
class RouteResult:
    output: str
    backend: str
    route: str
    failed_over: bool = False


class ComplexityRouter:
    """Routes by an explainable complexity score: simple/short -> small (cheap) model,
    complex/long/code -> large model. Fails over to the other backend on failure."""

    HARD_KEYWORDS = ("explain", "analyze", "compare", "prove", "debug",
                     "step by step", "reason", "derive", "why", "design")

    def __init__(self, small: Backend, large: Backend, threshold: int = 3):
        self.small = small
        self.large = large
        self.threshold = threshold

    def classify(self, task: str, text: str, options: dict) -> RouteDecision:
        # explicit override wins
        forced = (options or {}).get("model")
        if forced in ("small", "large"):
            return RouteDecision(forced, 0, [f"forced->{forced}"])

        reasons, score = [], 0
        n_words = len(text.split())
        if n_words > 60:
            score += 3; reasons.append(f"long({n_words}w)")
        elif n_words > 25:
            score += 1; reasons.append(f"medium({n_words}w)")

        low = text.lower()
        hits = [k for k in self.HARD_KEYWORDS if k in low]
        if hits:
            score += len(hits); reasons.append(f"kw={hits}")

        if "```" in text or re.search(r"(?:^|\s)(def|class|import|function)\s", text):
            score += 3; reasons.append("code")

        if text.count("?") >= 2:
            score += 1; reasons.append("multi-q")

        tier = "large" if score >= self.threshold else "small"
        return RouteDecision(tier, score, reasons or ["simple"])

    def _route_str(self, d: RouteDecision, used: str, failed_over: bool) -> str:
        s = f"{d.tier} (score={d.score}: {', '.join(d.reasons)})"
        return s + (f" [failed over -> {used}]" if failed_over else "")

    async def complete(self, task: str, text: str, options: dict) -> RouteResult:
        d = self.classify(task, text, options)
        primary = self.large if d.tier == "large" else self.small
        secondary = self.small if d.tier == "large" else self.large
        try:
            output = await primary.predict(text)
            return RouteResult(output, primary.name, self._route_str(d, primary.name, False))
        except Exception:
            # primary failed (e.g. circuit open) -> fail over to the other backend
            output = await secondary.predict(text)   # if this also fails, it propagates
            return RouteResult(output, secondary.name, self._route_str(d, secondary.name, True), True)
