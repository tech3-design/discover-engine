from app.checkers.registry import registry

from .content_quality import ContentQualityChecker

registry.register(ContentQualityChecker())
