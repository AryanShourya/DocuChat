import os 
import shutil
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile ,File, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models.document import Document
from app.schemas.document import DocumentCreate, DocumentResponse
from app.auth import get_current_user
from app.config import settings
from app.services.ingestion import ingest_document


router = APIRouter(
    prefix="/documents",
    tags=["documents"],
)

# Allowed file tyeps
ALLOWED_EXTENSIONS = {".pdf",".docx"}
MAX_FILE_SIZE = settings.MAX_FILE_SIZE_MB * 1024 * 1024 #covert MB to byte

# ---- upload a document ------
@router.post("/upload",response_model=DocumentResponse,status_code=status.HTTP_201_CREATED)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    #-----Validate file extension--------
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail = f"File type {file_ext} not allowed. Use PDF or Docx."
        )
        
    # validate file size ----
    file.file.seek(0,2)
    file_size = file.file.tell()
    file.file.seek(0)
    
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code= status.HTTP_400_BAD_REQUEST,
            detail = f"File too large. Maximum size is {settings.MAX_FILE_SIZE_MB}."
        )
        
    
    # -------- save file ---------
    os.makedirs(settings.UPLOAD_DIR, exist_ok = True)
    file_path = os.path.join(settings.UPLOAD_DIR,f"{user_id}_{file.filename}")

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # ------- Save metadata to DB ------
    document = Document(
        user_id = user_id,
        filename = file.filename,
        file_path = file_path,
        file_size = file_size,
        status = "uploaded",
    )
    
    db.add(document)
    await db.flush()
    await db.refresh(document)
    
    await db.commit()
    # ----- Queue ingestion as background task ------
    background_tasks.add_task(
        ingest_document,
        doc_id = document.id,
        user_id = user_id,
        file_path = file_path,
        filename = file.filename,
    )
    
    # Return immediately - ingestion runs in background
    return document

# list all the documents (current user's)
@router.get("/",response_model=list[DocumentResponse])
async def list_documents(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    result = await db.execute(
        select(Document).where(Document.user_id == user_id)
        )
    documents = result.scalars().all()
    return documents



# ---------- create a document record ----- (current user)
@router.post("/",response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def create_document(
    payload : DocumentCreate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    
    document = Document(
        user_id = user_id,
        filename = payload.filename,
        file_path = f"uploads/{payload.filename}",
        file_size = payload.file_size,
        status = "uploaded",
    )

    db.add(document)
    await db.flush()
    await db.refresh(document)
    return document


# --------- get a single document ---------- (current user's)
@router.get("/{doc_id}", response_model=DocumentResponse)
async def get_document(
    doc_id : int,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    
    result = await db.execute(
        select(Document).where(
            Document.id == doc_id,
            Document.user_id == user_id,
            )
    )

    document = result.scalars().first()

    if not document:
        raise HTTPException(
            status_code= status.HTTP_404_NOT_FOUND,
            detail = f"Document with id {doc_id} not found",
        )
    
    return document 


# --------- Delete a document ------
@router.delete("/{doc_id}",status_code = status.HTTP_204_NO_CONTENT)
async def delete_documents(
    doc_id: int,
    db: AsyncSession = Depends(get_db),
    user_id:str = Depends(get_current_user),
):
    result = await db.execute(
        select(Document).where(
            Document.id == doc_id,
            Document.user_id == user_id,
        )
    )
    
    document = result.scalars().first()
    
    if not document:
        raise HTTPException(
            status_code= status.HTTP_404_NOT_FOUND,
            detail = f"Document with id {doc_id} not found",
        )
        
    
    # Delete file from disk
    if os.path.exists(document.file_path):
        os.remove(document.file_path)
        
    await db.delete(document)
    return None