from pydantic import BaseModel
from typing import Optional

class UserInput(BaseModel):
    content: str
    context: Optional[str] = None
    
class UserOutput(BaseModel):
    processed_content: str
    status: str
