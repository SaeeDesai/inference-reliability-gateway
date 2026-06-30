from src.router import ComplexityRouter

def _router(threshold=3):
    return ComplexityRouter(small=None, large=None, threshold=threshold)

def test_simple_prompt_routes_small():
    assert _router().classify("chat", "hi", {}).tier == "small"

def test_complex_prompt_routes_large():
    d = _router().classify("chat", "Explain step by step why X, and compare to Y.", {})
    assert d.tier == "large"
    assert d.score >= 3

def test_code_routes_large():
    assert _router().classify("chat", "fix def foo(): pass", {}).tier == "large"

def test_forced_override_wins():
    assert _router().classify("chat", "hi", {"model": "large"}).tier == "large"
    assert _router().classify("chat", "Explain compare analyze why", {"model": "small"}).tier == "small"
