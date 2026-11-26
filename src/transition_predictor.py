"""Transition-count prediction policy backed by nested hash maps."""

from typing import Dict, Optional


class TransitionPredictor:
    def __init__(self) -> None:
        self.transitions: Dict[str, Dict[str, int]] = {}

    def record_transition(self, source: str, successor: str) -> None:
        """Record one observed source-to-successor access."""
        successors = self.transitions.setdefault(source, {})
        successors[successor] = successors.get(successor, 0) + 1

    def predict_next(
        self, current_item: str, fallback: Optional[str] = None
    ) -> Optional[str]:
        """Choose the most frequent observed successor, or use the fallback."""
        successors = self.transitions.get(current_item)
        if not successors:
            return fallback
        return min(successors, key=lambda item: (-successors[item], item))
