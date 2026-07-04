from pydantic import BaseModel
from typing import Optional, List
 
 
# Bump this whenever FunctionSchema's fields change in a way that makes old
# stored data (Chroma metadata / BM25 pickles) incompatible or incomplete —
# e.g. adding a new required field, renaming a field, changing a field's
# meaning. Old indexed collections carry whatever schema_version was current
# when they were written, so check_cache()/indexing code can detect and
# force a re-index instead of silently serving data shaped like an older
# version of this schema (Issue #11).
CURRENT_SCHEMA_VERSION = 1
 
 
class FunctionSchema(BaseModel):
    schema_version: int = CURRENT_SCHEMA_VERSION
    type: str  # "function" | "class" | "method"
    name: str
    library: str
    version: Optional[str] = None  # the LIBRARY's version, e.g. "2.1.0" — not this schema's version
    params: List[str] = []
    description: Optional[str] = None
    use_when: List[str] = []
    avoid_when: List[str] = []
    example: Optional[str] = None
    related: List[str] = []
    notes: Optional[str] = None
    source_url: Optional[str] = None
 