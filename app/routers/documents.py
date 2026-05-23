from fastapi import APIRouter, Depends, HTTPException, status 
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models.document import Document
from app.schemas.document import DocumentCreate, DocumentResponse


router = APIRouter(
    prefix="/documents",
    tags=["documents"],
)

# list all the documents
@router.get("/",response_model=list[DocumentResponse])
async def list_documents(
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Document))
    documents = result.scalars().all()
    return documents



# ---------- create a document record -----
@router.post("/",response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def create_document(
    payload : DocumentCreate,
    db: AsyncSession = Depends(get_db),
):
    
    document = Document(
        user_id = payload.user_id,
        filename = payload.filename,
        file_path = f"uploads/{payload.filename}",
        file_size = payload.file_size,
        status = "uploaded",
    )

    db.add(document)
    await db.flush()
    await db.refresh(document)
    return document


# --------- get a single document ----------
@router.get("/{doc_id}", response_model=DocumentResponse)
async def get_document(
    doc_id : int,
    db: AsyncSession = Depends(get_db),
):
    
    result = await db.execute(
        select(Document).where(Document.id == doc_id)
    )

    document = result.scalars().first()

    if not document:
        raise HTTPException(
            status_code= status.HTTP_404_NOT_FOUND,
            detail = f"Document with id {doc_id} not found",
        )
    
    return document 

