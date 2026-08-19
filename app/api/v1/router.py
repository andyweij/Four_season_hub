from fastapi import APIRouter

from app.modules.chat.llm_api_router import router as chat_router
from app.modules.llm_management.llm_mgt_router import router as llm_mgt_router

api_v1_router = APIRouter()

api_v1_router.include_router(
    chat_router,
    tags=["Chat"],
)

api_v1_router.include_router(
    llm_mgt_router,
    tags=["LLM_management"],
)
