from src.router import ComplexityRouter

# USD per 1M tokens (Groq, current): (input, output). Large is exactly 2x small.
P_SMALL = (0.075, 0.30)   # gpt-oss-20b
P_LARGE = (0.15,  0.60)   # gpt-oss-120b
OUT_TOKENS = 300          # assumed output per request -> isolates the routing effect

def est_input_tokens(text):
    return max(1, round(len(text.split()) * 1.3))

def cost(price, in_tok, out_tok):
    return in_tok / 1e6 * price[0] + out_tok / 1e6 * price[1]

WORKLOAD = [
    "hi",
    "What's the capital of France?",
    "Translate 'hello' to French.",
    "What time is it in Tokyo?",
    "Define photosynthesis.",
    "Summarize in one line: cats are mammals.",
    "Is 17 prime?",
    "Explain step by step why transformers use attention and compare to RNNs.",
    "Debug this: def f(x): retur x+1",
    "Analyze the tradeoffs between microservices and monoliths.",
    "Derive the quadratic formula and explain each step.",
    "Compare REST and GraphQL; which is better and why?",
]

def main():
    router = ComplexityRouter(small=None, large=None, threshold=3)  # classify-only
    router_total = baseline_total = 0.0
    n_small = n_large = 0
    for text in WORKLOAD:
        d = router.classify("chat", text, {})
        in_tok = est_input_tokens(text)
        price = P_SMALL if d.tier == "small" else P_LARGE
        router_total += cost(price, in_tok, OUT_TOKENS)
        baseline_total += cost(P_LARGE, in_tok, OUT_TOKENS)
        n_small += d.tier == "small"
        n_large += d.tier == "large"
        print(f"  [{d.tier:5}] {text[:52]}")

    print(f"\n  {n_small} small, {n_large} large")
    print(f"  router cost    : ${router_total*1e6:8.2f}  per 1M such requests")
    print(f"  always-large   : ${baseline_total*1e6:8.2f}  per 1M such requests")
    print(f"  SAVINGS        : {(1 - router_total/baseline_total)*100:5.1f}%")

if __name__ == "__main__":
    main()
