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

