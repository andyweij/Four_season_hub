import logging

from fastapi import APIRouter, HTTPException
from app.modules.llm_management.dependencies import (
    ModelActivationServiceDependency,
    ModelRegistryServiceDependency,
)
from app.modules.llm_management.schemas.available_models import (
    AvailableModelsResponse,
)
from app.modules.llm_management.schemas.model_mappers import to_available_model_response

from app.modules.llm_management.domain.artifact import ArtifactStatus
from app.modules.llm_management.domain.enums import ModelRuntimeStatus
from app.modules.llm_management.schemas.update_launch_config import UpdateLaunchConfigRequest
from app.modules.llm_management.schemas.run_model import RunModelRequest, RunModelResponse

logger = logging.getLogger("app")
router = APIRouter(
    prefix="/mgt/models",
    tags=["LLM Management"],
)


@router.get("", response_model=AvailableModelsResponse, )
async def get_available_models(
        registry: ModelRegistryServiceDependency,
) -> AvailableModelsResponse:
    response_models = [
        to_available_model_response(model)
        for model in registry.get_all().values()
    ]

    return AvailableModelsResponse(
        models=response_models,
        total=len(response_models),
    )


@router.post("/run", response_model=RunModelResponse)
async def run_model_app(
        request: RunModelRequest,
        registry: ModelRegistryServiceDependency,
        activation: ModelActivationServiceDependency,
) -> RunModelResponse:
    model_name = request.model_name
    model = registry.get(model_name)
    if model is None:
        raise HTTPException(status_code=404, detail=f"Unknown model_name: {model_name}")

    if model.download_status != ArtifactStatus.COMPLETE:
        raise HTTPException(
            status_code=409,
            detail=f"Model artifact not ready: {model.download_status}",
        )

    if model.instance is not None and model.instance.status in (
            ModelRuntimeStatus.READY, ModelRuntimeStatus.STARTING,
    ):
        raise HTTPException(status_code=409, detail="Model is already running")

    # llm_mgt_router.py run_model_app 內
    instance = await activation.run_model(model.catalog, model.effective_launch_config)
    model.instance = instance  # 立刻反映到 registry，不用等下一次 event

    return RunModelResponse(
        model_name=model_name,
        status=instance.status,
        endpoint=model.endpoint,
    )


ALLOWED_OVERRIDE_KEYS = {"max-model-len", "gpu-memory-utilization", "max-num-seqs", ...}


@router.patch("/launch-config")
async def update_launch_config(
        request: UpdateLaunchConfigRequest,
        registry: ModelRegistryServiceDependency,
):
    model = registry.get(request.model_name)
    if model is None:
        raise HTTPException(status_code=404, detail=f"Unknown model_name: {request.model_name}")

    unknown = set(request.config_overrides) - ALLOWED_OVERRIDE_KEYS
    if unknown:
        raise HTTPException(status_code=400, detail=f"Unsupported override keys: {unknown}")

    model.effective_launch_config.args.update(request.config_overrides)

    return {"model_name": request.model_name, "effective_launch_config": model.effective_launch_config}


@router.delete("/disable-model/{model_name}")
async def disable_model(model_name: str, registry: ModelRegistryServiceDependency,
                        activation: ModelActivationServiceDependency):
    model = registry.get(model_name)
    if model is None:
        raise HTTPException(status_code=404, detail=f"Unknown model_name: {model_name}")
    if model.instance is not None:
        logger.info("Model %s disabled and instance %s stopped", model_name, model.instance.id)
        await activation.disable_model(model.instance)
        model.instance = None

    return {"model_name": model_name, "status": "disabled"}
