from datetime import datetime
from pydantic import BaseModel



# API caller sends when creating a document
class DocumentCreate(BaseModel):
    filename: str
    file_size: int  


# API return includes DB generated fields
class DocumentResponse(BaseModel):
    id: int
    user_id: str
    filename: str 
    file_size: int 
    status: str 
    created_at: datetime 

    model_config = {"from_attributes": True}

# -------- chat schemas ---------

class ChatResquest(BaseModel):
    question: str 
    session_id: int | None = None #optional - new session


class MessageResponse(BaseModel):
    id:int
    session_id:int 
    role: str 
    content : str 
    created_at: datetime

    model_config = {"from_attrubutes": True}


class ChatSessionResponse(BaseModel):
    id: int  
    user_id: str 
    document_id: int 
    created_at: datetime
    messages: list[MessageResponse] = []

    model_config = {"from_attributes":True}