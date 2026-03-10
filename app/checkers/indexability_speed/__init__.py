from app.checkers.registry import registry

from .core_web_vitals import CoreWebVitalsChecker
from .js_rendering import JsRenderingChecker

for cls in [CoreWebVitalsChecker, JsRenderingChecker]:
    registry.register(cls())
