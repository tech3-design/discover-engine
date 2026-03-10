from app.checkers.registry import registry

from .entity_brand import EntityBrandChecker
from .author_eeat import AuthorEeatChecker
from .expertise_schema import ExpertiseSchemaChecker

for cls in [EntityBrandChecker, AuthorEeatChecker, ExpertiseSchemaChecker]:
    registry.register(cls())
