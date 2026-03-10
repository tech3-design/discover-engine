from app.checkers.registry import registry

from .ai_visibility import AiVisibilityChecker
from .faq_schema import FaqSchemaChecker

for cls in [FaqSchemaChecker, AiVisibilityChecker]:
    registry.register(cls())
