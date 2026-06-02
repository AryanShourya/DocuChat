from groq import AsyncGroq 
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings as ChromaSettings

from app.config import settings

# Reuse the same embeding model from ingestion
# Import it so it's not loaded twice
from app.services.ingestion import embedding_model, chroma_client


# initialise Groq client
groq_client = AsyncGroq(api_key = settings.GROQ_API_KEY)

async def get_relevant_chunks(
        question : str,
        user_id: int,
        doc_id: int,
        n_results: int = 5,
)-> list[str]:
    
    """
    Embed the question and find the most similar chunks in chromaDB
    for the given document
    """

    # Embed the question using the same model user during ingestion
    question_embedding = embedding_model.encode(question).tolist()

    # Get the uesr's collection
    collection_name = f"user_{user_id}"
    try:
        collection = chroma_client.get_collection(name = collection_name)
    except Exception:
        return []
    
    # Search for similar chunks filtered by doc_id

    results = collection.query(
        query_embeddings = [question_embedding],
        n_results= n_results,
        where = {"doc_id":doc_id},
    )

    # results["documents"] is a list of lists
    chunks = results["documents"][0] if results["documents"] else []
    return chunks



def build_prompt(
        question: str,
        chunks: list[str],
        history: list[dict],
)-> list[dict]:
    
    """
    Build the messages array for the LLM
    structure:
    - system message with context
    - previous conversation history
    - current question
    """

    # Build context string from retrieved chunks
    context = "\n\n--\n\n".join(chunks) if chunks else "No relevant context"

    system_message = {
        "role ": "system",
        "content": f"""You are a helpful assistant that answers questions based on the provided document context.
        
        Use ONLY the information from the context below to answer the question.
        If the answer is not in the context, say "I cannot find this information in the document."
        Be concise and accurate.

        CONTEXT:
        {context}"""
    }

    #Build messages: system + history + current question
    message = [system_message]

    # add conversation history
    for msg in history:
        messages.append({
            "role":msg["role"],
            "content": msg["content"]
        })

    # Add current question
    messages.append({
        "role": "user",
        "content": question
    })

    return messages


async def stream_chat_response(
        question : str,
        user_id : str,
        doc_id : int,
        history : list[dict],
):
    """
    Full RAG pipeline - retrieve, build prompt, stream response.
    Async generator - yields tokens one by one
    """

    # Step 1 - retrieve relevant chunks
    chunks = await get_relevant_chunks(
        question = question,
        user_id = user_id,
        doc_id = doc_id,
    )


    # Step 2 - build prompt
    messages = build_prompt(
        question= question,
        chunks= chunks,
        history= history,
    )

    # Step 3 - stream from Groq
    stream = await groq_client.chat.completions.create(
        model = "llama-3.3-70b-versatile",
        messages=messages,
        max_tokens=1074,
        temperature= 0.1, # more factual less creative
        stream= True,  # stream tokens as they are generated 
    )


    # Step 4 - yield tokens one by one
    async for chunk in stream:
        token = chunk.choices[0].delta.content
        if token is not None:
            yield token 