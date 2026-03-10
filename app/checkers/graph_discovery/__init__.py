from app.checkers.registry import registry

from .internal_linking import InternalLinkingChecker
from .llm_txt import LlmTxtChecker

for cls in [InternalLinkingChecker, LlmTxtChecker]:
    registry.register(cls())
