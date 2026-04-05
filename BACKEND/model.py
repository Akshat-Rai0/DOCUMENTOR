from typing import List, Optional

from pydantic import BaseModel, Field

class UserInput(BaseModel):
    content: str
    context: Optional[str] = None
    source_url: Optional[str] = None
    use_reranker: bool = True

class RetrievedChunk(BaseModel):
    chunk_id: str
    score: float
    text: str
    source_url: Optional[str] = None
    function_name: Optional[str] = None
    rank: Optional[int] = None

class UserOutput(BaseModel):
    status: str = "success"
    intent: str
    processed_content: str
    recommended_functions: List[str] = Field(default_factory=list)
    use_when: List[str] = Field(default_factory=list)
    avoid_when: List[str] = Field(default_factory=list)
    code_snippet: str = ""
    source_url: Optional[str] = None
    confidence: float = 0.0
    explanation: str = ""
    fixes: List[str] = Field(default_factory=list)
    retrieved_chunks: List[RetrievedChunk] = Field(default_factory=list)

class CrawlRequest(BaseModel):
    url: str

class CrawlResponse(BaseModel):
    status: str
    pages_indexed: int
    library_name: str
    message: str