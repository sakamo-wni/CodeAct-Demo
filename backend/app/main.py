# backend/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from langserve import add_routes
from app.agent.flow import workflow
from app.sse import router as sse_router

# ── FastAPI インスタンス ───────────────────────────────────
app = FastAPI()

# ── 共通設定を取得（env 読み込み済み）───────────────────
settings = get_settings()

# ── CORS設定 ───────────────────────────────────────────────
origins = (
    settings.allowed_origins.split(",")
    if getattr(settings, "allowed_origins", None)
    else ["*"]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── LangGraph エージェントを /agent にマウント ─────────────
add_routes(app, workflow, path="/agent")

# ── SSEルーターを追加 ─────────────────────────────────────
app.include_router(sse_router)

# ── ヘルスチェック ───────────────────────────────────────
@app.get("/health", tags=["system"])
def health():
    return {"status": "ok"}

# ── 設定確認エンドポイント ───────────────────────────────
@app.get("/config-check", tags=["system"])
def config_check():
    """現在読み込まれている主要設定を返す（開発用）"""
    return {
        "llm_provider": settings.llm_provider,
        "s3_bucket": settings.s3_bucket,
        "aws_region": settings.aws_default_region,
    }
