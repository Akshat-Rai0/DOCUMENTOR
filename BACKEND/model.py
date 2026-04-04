from pydantic import BaseModel
from typing import Optional, List

class UserInput(BaseModel):
    content: str
    context: Optional[str] = None

class UserOutput(BaseModel):
    processed_content: str
    status: str

class CrawlRequest(BaseModel):
    url: str

class CrawlResponse(BaseModel):
    status: str
    pages_indexed: int
    library_name: str
    message: str