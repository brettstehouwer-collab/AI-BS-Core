import re


class HeuristicTokenEstimator:
    def __init__(self, max_context_window: int = 6000):
        self.max_context_window = max_context_window

    @staticmethod
    def estimate_tokens(text: str) -> int:
        if not text:
            return 0
        words = set(re.findall(r"\b\w+\b", text))
        word_count = len(words)
        char_count = len(text)
        return max(1, int((word_count * 1.3 + char_count / 4) / 2))
