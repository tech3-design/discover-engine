from app.checkers.registry import registry

from .json_ld import JsonLdChecker
from .og_metadata import OgMetadataChecker
from .semantic_html import SemanticHtmlChecker

for cls in [JsonLdChecker, OgMetadataChecker, SemanticHtmlChecker]:
    registry.register(cls())
