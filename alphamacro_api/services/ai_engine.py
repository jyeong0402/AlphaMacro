"""Server-local FinBERT inference engine with deterministic fallback."""
import re
from typing import Iterable

class SentimentEngine:
    def __init__(self, model_name: str = "ProsusAI/finbert", load_model: bool = False):
        self.status = "fallback:model-disabled"
        self.pipeline = None
        self.model_name = model_name
        if load_model:
            self.load()

    def load(self) -> str:
        try:
            from transformers import pipeline
            self.pipeline = pipeline("sentiment-analysis", model=self.model_name)
            self.status = "finbert"
        except (ImportError, OSError, RuntimeError, ValueError) as exc:
            self.pipeline = None
            self.status = f"fallback:model-unavailable ({type(exc).__name__})"
        return self.status

    def analyze(self, texts: Iterable[str]) -> tuple[float, str, list[str]]:
        items = [str(x) for x in texts if str(x).strip()]
        if not items:
            return 0.0, "neutral", []
        if self.pipeline:
            scores = []
            for text in items:
                result = self.pipeline(text[:2000])[0]
                score = float(result["score"]) * (1 if result["label"].upper() == "POSITIVE" else -1)
                scores.append(score)
        else:
            positive = {"growth", "profit", "increase", "positive", "surge", "상승", "호재"}
            negative = {"loss", "decline", "decrease", "negative", "risk", "하락", "악재"}
            scores = [(sum(w in t.lower() for w in positive) - sum(w in t.lower() for w in negative)) / 3 for t in items]
        score = max(-1.0, min(1.0, sum(scores) / len(scores)))
        return score, "positive" if score > .15 else "negative" if score < -.15 else "neutral", [re.sub(r"\s+", " ", x)[:180] for x in items[:3]]
