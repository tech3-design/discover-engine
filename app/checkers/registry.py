from __future__ import annotations

from app.checkers.base import BaseChecker
from app.models.enums import Layer


class CheckerRegistry:
    _instance: CheckerRegistry | None = None
    _checkers: list[BaseChecker]

    def __new__(cls) -> CheckerRegistry:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._checkers = []
        return cls._instance

    def register(self, checker: BaseChecker) -> None:
        self._checkers.append(checker)

    def all(self) -> list[BaseChecker]:
        return list(self._checkers)

    def by_layer(self, layer: Layer) -> list[BaseChecker]:
        return [c for c in self._checkers if c.layer == layer]

    def reset(self) -> None:
        self._checkers.clear()


registry = CheckerRegistry()
