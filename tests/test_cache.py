from src.cache import RedisCache

def test_key_stable_under_normalization():
    k1 = RedisCache.make_key("chat", "Hello", {})
    k2 = RedisCache.make_key(" CHAT ", "Hello  ", {})   # task case + whitespace
    assert k1 == k2

def test_key_differs_for_different_prompt():
    k1 = RedisCache.make_key("chat", "hello", {})
    k2 = RedisCache.make_key("chat", "HELLO", {})        # prompt case DOES matter
    assert k1 != k2
