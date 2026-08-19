from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from app.api.v1.router import api_v1_router
from app.middlewares.request_response_logging import (
    RequestResponseLoggingMiddleware,
)
from app.logging_config import configure_logging
from app.lifespan import lifespan

configure_logging()

def create_app() -> FastAPI:
    app = FastAPI(
        title="Four Season Hub",
        version="1.0.0",
        lifespan=lifespan
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(
        api_v1_router,
        prefix="/v1",
    )
    app.add_middleware(RequestResponseLoggingMiddleware)
    return app


app = create_app()
