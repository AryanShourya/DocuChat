from fastapi import FastAPI
from app.config import settings
from contextlib import asynccontextmanager
from app.db.session import engine, Base 
from app.routers import documents
import app.models.document  # import this to avoid error


@asynccontextmanager
async def lifespan(app: FastAPI):
    # create all tables if they dont exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    print("Database table created")
    yield
    # shutdown dispose the connection pool
    await engine.dispose()
    print("Database connection closed")


app = FastAPI(
    title=settings.APP_NAME,
    version = settings.APP_VERSION,
    debug = settings.DEBUG,
    lifespan=lifespan,
)


# ---------- Routers --------
app.include_router(documents.router)



@app.get("/")
async def root():
    return{
        "app":settings.APP_NAME,
        "version":settings.APP_VERSION,
        "status":"running",
    }


@app.get("/health")
async def health_check():
    return{
        "status":"OK",
    }