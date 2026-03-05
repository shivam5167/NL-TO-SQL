from pydantic import BaseModel
from typing import List, Dict, Optional


class QueryRequest(BaseModel):

    question: str
    db_url: str


class QueryResponse(BaseModel):

    sql: str
    result: Optional[List[Dict]] = None
    error: Optional[str] = None