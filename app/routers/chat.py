from fastapi import APIRouter, Depends, HTTPException, status 
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import json 

from app.db.session import get_db
from app.models.document import Document, ChatSession, Message
from app.schemas.document import ChatResquest, ChatSessionResponse
from app.auth import get_current_user
from app.services.rag import stream_chat_response

router = APIRouter(
    prefix="/chat",
    tags=["chat"],
)

# --------- Start or continue a chat session --------
@router.post("/{doc_id}/message")
async def chat_message(
    doc_id: int,
    body: ChatResquest,
    db : AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    # Verify document exists and belongs to user
    result = await db.execute(
        select(Document).where(
            Document.id == doc_id,
            Document.user_id == user_id,
        )
    )
    document = result.scalars().first()
    if not document:
        raise HTTPException(
            status_code = status.HTTP_404_NOT_FOUND,
            detail = "Document not found",
        )

    # check document is processed
    if document.status != "processed":
        raise HTTPException(
            status_code= status.HTTP_400_BAD_REQUEST,
            detail= f"Document is not ready yet. Status:{document.status}",
        )
    
    # Get or create chat session
    if body.session_id:
        result = await db.execute(
            select(ChatSession).where(
                ChatSession.id == body.session_id,
                ChatSession.user_id == user_id,
            )
        )

        session = result.scalars().first()
        if not session:
            raise HTTPException(
                status_code= status.HTTP_404_NOT_FOUND,
                detail= "Chat session not found"
            )
        
    else:
        # create new session
        session = ChatSession(
            user_id = user_id,
            document_id = doc_id,
        )

        db.add(session)
        await db.flush()
        await db.refresh(session)

    # Load conversation history (last 10 messages)
    history_result = await db.execute(
        select(Message)
        .where(Message.session_id == session.id)
        .order_by(Message.created_at.asc())
        .limit(10)
    )
    history_messages = history_result.scalars().all()
    history = [
        {"role" : msg.role, "content" : msg.content}
        for msg in history_messages
    ]

    # Save user message to DB
    user_message = Message(
        session_id = session.id,
        role = "user",
        content = body.question,
    )
    db.add(user_message)
    await db.commit()


    # Stream the response
    async def generate():
        full_response = ""

        # First yield the session_id so client knows session
        yield f"data: {json.dumps({'session_id' :session.id})}\n\n"

        # Stream tokens
        async for token in stream_chat_response(
            question= body.question,
            user_id= user_id,
            doc_id= doc_id,
            history= history,
        ):
            full_response += token 
            yield f"data: {json.dumps({'token': token})}\n\n"

        # Save assistant response to DB after streaming completes
        async with db.begin():
            assitant_message = Message(
                session_id = session.id,
                role = "assistant",
                content = full_response,
            )
            db.add(assitant_message)

        # Signal stream is done
        yield f"date : {json.dumps({'done' : True})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        }
    )


@router.get("/{doc_id}/sessions", response_model=list[ChatSessionResponse])
async def get_sessions(
    doc_id : int,
    db: AsyncSession = Depends(get_db),
    user_id : str = Depends(get_current_user),
):
    result = await db.execute(
        select(ChatSession).where(
            ChatSession.document_id == doc_id,
            ChatSession.user_id == user_id,
        )
    )

    sessions = result.scalars().all()
    return sessions 

    