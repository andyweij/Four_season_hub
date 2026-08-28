from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from app.api.v1.router import api_v1_router
from app.middlewares.request_response_logging import (
    RequestResponseLoggingMiddleware,
)
from app.logging_config import configure_logging
from app.lifespan import lifespan
from fastapi import Request
from fastapi.responses import JSONResponse
from app.modules.llm_management.exceptions import (
    PortAllocationError,
    UnsupportedOverrideKeysError,
)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(PortAllocationError)
    async def handle_port_allocation_error(request: Request, exc: PortAllocationError):
        return JSONResponse(
            status_code=503,
            content={"detail": str(exc), "error_code": "PORT_ALLOCATION_FAILED"},
        )

    @app.exception_handler(UnsupportedOverrideKeysError)
    async def handle_unsupported_override_keys(request: Request, exc: UnsupportedOverrideKeysError):
        return JSONResponse(
            status_code=400,
            content={"detail": str(exc), "error_code": "UNSUPPORTED_OVERRIDE_KEYS"},
        )


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
    register_exception_handlers(app)
    app.include_router(
        api_v1_router,
        prefix="/v1",
    )
    app.add_middleware(RequestResponseLoggingMiddleware)
    return app


app = create_app()
