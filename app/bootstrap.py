from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncEngine

from app.infrastructure.keycloak.admin_client import KeycloakAdminClient
from app.infrastructure.keycloak.token_verifier import KeycloakTokenVerifier
from app.modules.cloud_llm_management.bootstrap import build_cloud_llm_management_service, CloudLlmManagementServices, \
    decode_aes_256_key
from app.modules.llm_management.bootstrap import build_llm_management_services, LlmManagementServices, \
    shutdown_llm_management

from app.infrastructure.config.settings import Settings
import httpx
from motor.motor_asyncio import AsyncIOMotorClient

from app.core.database import build_mongo_client, get_mongo_database
from app.modules.llm_inference.services.inference_client import InferenceClient
from app.modules.chat.bootstrap import build_chat_services, ChatServices
from app.core.postgre import build_postgres_engine, build_session_factory


@dataclass
class AppServices:
    llm_management: LlmManagementServices
    chat: ChatServices
    mongo_client: AsyncIOMotorClient
    http_client: httpx.AsyncClient
    token_verifier: KeycloakTokenVerifier
    postgres_engine: AsyncEngine
    cloud_llm: CloudLlmManagementServices
    keycloak_admin_client: KeycloakAdminClient


async def build_app_services(settings: Settings) -> AppServices:
    llm_management = await build_llm_management_services(settings)
    mongo_client = build_mongo_client(settings)
    postgres_engine = build_postgres_engine(settings)
    session_factory = build_session_factory(postgres_engine)

    current_key_version = settings.credential_encryption_key_current_version
    encryption_key_v1 = decode_aes_256_key(
        settings.credential_encryption_key_v1
    )

    encryption_keys: dict[int, bytes] = {
        1: encryption_key_v1,
    }

    if current_key_version not in encryption_keys:
        raise ValueError(
            "Current Cloud LLM encryption key "
            f"version {current_key_version} is missing"
        )

    cloud_llm = build_cloud_llm_management_service(
        session_factory=session_factory,
        encryption_keys=encryption_keys,
        current_key_version=current_key_version,
    )
    database = get_mongo_database(mongo_client, settings)
    http_client = httpx.AsyncClient()
    inference_client = InferenceClient(http_client)
    token_verifier = KeycloakTokenVerifier(
        http_client=http_client,
        jwks_url=settings.keycloak_jwks_url,
        issuer=settings.keycloak_issuer,
        audience=settings.keycloak_audience,
    )

    keycloak_admin_client = KeycloakAdminClient(
        http_client=http_client,
        base_url=settings.keycloak_base_url,
        realm=settings.keycloak_realm,
        client_id=settings.keycloak_admin_client_id,
        client_secret=(
            settings.keycloak_admin_client_secret
            .get_secret_value()
        ),
    )
    chat = await build_chat_services(
        database=database,
        registry_service=llm_management.registry_service,
        inference_client=inference_client,
    )
    return AppServices(
        llm_management=llm_management,
        chat=chat,
        mongo_client=mongo_client,
        http_client=http_client,
        token_verifier=token_verifier,
        keycloak_admin_client=keycloak_admin_client,
        postgres_engine=postgres_engine,
        cloud_llm=cloud_llm,
    )


async def shutdown_app_services(services: AppServices) -> None:
    await shutdown_llm_management(services.llm_management)
    await services.http_client.aclose()
    await services.postgres_engine.dispose()
    services.mongo_client.close()
