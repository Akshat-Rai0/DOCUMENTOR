from pydantic import BaseModel
from typing import Optional, List
 
 
class FunctionSchema(BaseModel):
    type: str  # "function" | "class" | "method"
    name: str
    library: str
    version: Optional[str] = None
    params: List[str] = []
    description: Optional[str] = None
    use_when: List[str] = []
    avoid_when: List[str] = []
    example: Optional[str] = None
    related: List[str] = []
    notes: Optional[str] = None
    source_url: Optional[str] = None
 