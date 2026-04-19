from fastapi import FastAPI

from app.routes.chat import router as chat_router
from app.routes.sessions import router as sessions_router

app = FastAPI(title="LaoshiGPT API", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(sessions_router, prefix="/v1/sessions", tags=["sessions"])
app.include_router(chat_router, prefix="/v1/chat", tags=["chat"])
