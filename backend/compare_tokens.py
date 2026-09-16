import tiktoken

enc = tiktoken.encoding_for_model("gpt-4")

samples = [
    "Your example conversation text here.",
    'def hello_world():\n    print("Hello, World!")',
    ("The quick brown fox jumps over the lazy dog. " * 50),
    "Tokenization is the process of splitting text into tokens.",
]

for s in samples:
    real = len(enc.encode(s))
    words = set(re.findall(r"\b\w+\b", s))  # Use word boundary to avoid false positives
    word_count = len(words)
    char_count = len(s)
    est = int((word_count * 1.3 + char_count / 4) / 2)
    diff = est - real
    pct = 100 * diff / real if real else 0
    print(f"Real: {real:5d}  Estimated: {est:5d}  Diff: {diff:+5d}  ({pct:+.1f}%)")
