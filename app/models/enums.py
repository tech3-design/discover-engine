from enum import Enum


class CheckStatus(str, Enum):
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"
    NA = "n/a"


class AuditStatus(str, Enum):
    PENDING = "pending"
    CRAWLING = "crawling"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    FAILED = "failed"


class Layer(str, Enum):
    SITE_FOUNDATION = "S"
    INDEXABILITY_SPEED = "I"
    GRAPH_DISCOVERY = "G"
    NODE_READABILITY = "N"
    AUTHORITY_TRUST = "A"
    LLM_EXTRACTION = "L"
    CONTENT_QUALITY = "C"
