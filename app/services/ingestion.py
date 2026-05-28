import os
import uuid
import fitz
from docx import Document as DocxDocument
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings as ChromaSettings

from app.config import settings

# ---- Initialize embedding model (loaded once, reused)
# This downloads the model on first run (~80MB), then caches it
print("Loading embedding model...")
embedding_model = SentenceTransformer(settings.EMBEDDING_MODEL)
print("Embedding model loaded")


# -- Initialize chromaDB client ------
chroma_client = chromadb.PersistentClient(
    path = settings.CHROMA_DIR,
    settings=ChromaSettings(anonymized_telemetry=False)
)



def get_or_create_collection(user_id: str):
    """Each user gets their own chromaDB collection"""
    collection_name = f"user_{user_id}"
    return chroma_client.get_or_create_collection(
        name = collection_name,
        metadata={"hnsw:space":"cosine"} #use cosine similarity 
    )



def extract_text_from_pdf(file_path:str)-> str:
    """Extract all text from a PDF file page by page"""

    doc = fitz.open(file_path)
    full_text = ""

    for page in doc:
        full_text += page.get_text()
    doc.close()
    return full_text 



def extract_text_from_docx(file_path:str)->str:
    """Extract all text from a Word Document"""
    doc = DocxDocument(file_path)

    full_text = ""

    for paragraph in doc.paragraphs:
        full_text += paragraph.text + "\n"
    return full_text



def chunk_text(text:str)-> list[str]:
    """
    Split text into overlapping chunks
    chunk_size = 500 -> each chunk is ~500 characters
    chunk_overlap = 50 -> consecutive chunks share 50 chars
    Overlap ensures context isn't lost at chunk boundaries
    """

    splitter = RecursiveCharacterTextSplitter(
        chunk_size = 500,
        chunk_overlap = 50,
        separators=["\n\n","\n","."," ",""]
    )

    return splitter.split_text(text)



def embed_chunks(chunks: list[str])-> list[list[float]]:
    """Convert text chunks to embeddings vectors"""
    embeddings = embedding_model.encode(chunks,show_progress_bar = True)
    return embeddings.tolist()


async def ingest_document(
    doc_id:int,
    user_id: str,
    file_path: str,
    filename: str,
):
    """
    Full ingestion pipeline:
    1.Extract text
    2.chunk text
    3. Embed chunks
    4. Store in chromaDB
    """

    from app.db.session import AsyncSessionLocal
    from app.models.document import Document
    from sqlalchemy import select

    print(f"Starting ingestion for document {doc_id}: {filename}")

    try:
        # ---STEP - 1 : Extract text ----
        if filename.lower().endswith(".pdf"):
            text = extract_text_from_pdf(file_path)
        elif filename.lower().endswith(".docx"):
            text = extract_text_from_docx(file_path)
        else:
            raise ValueError(f"Unsupported file type: {filename}")
        

        if not text.strip():
            raise ValueError(f"No text could be extracted from the document")
        
        print(f"Extracted {len(text)} characters from {filename}")

        # ----- STEP - 2: Chunk text --------
        chunks = chunk_text(text)
        print(f"Split into {len(chunks)} chunks")

        # ------ STEP - 3: Embed chunks ------
        embeddings = embed_chunks(chunks)
        print(f"Gnerated {len(embeddings)} embeddings")

        # ------ STEP - 4: Store in chromaDB ------
        collection = get_or_create_collection(user_id)


        # Generate unique IDs for each chunk
        chunk_ids = [f"doc_{doc_id}_chunk_{i}" for i in range(len(chunks))]

        collection.upsert(
            ids = chunk_ids,
            documents=chunks,
            embeddings=embeddings,
            metadatas=[
                {
                    "doc_id": doc_id,
                    "user_id": user_id,
                    "filename":filename,
                    "chunk_index": i,
                }
                for i in range(len(chunks))
            ]
        )
        print(f"Stored {len(chunks)} chunks in ChromaDB")

        # -- STEP - 5: Update document status in DB -----
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Document).where(Document.id == doc_id)
            )
            document = result.scalars().first()
            if document:
                document.status = "processed"
                await db.commit()

        print(f"Document {doc_id} ingestion complete.")

    except Exception as e:
        print(f"Ingestion failed for document {doc_id}: {str(e)}")
        # update status to failed

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Document).where(Document.id == doc_id)
            )
            document = result.scalars().first()
            if document:
                document.status = "failed"
                await db.commit()