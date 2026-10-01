import hashlib
import secrets
import time
from datetime import UTC, datetime, timedelta
import jwt
from pydantic import BaseModel, ConfigDict, Field
from app.modules.agent_execution.schemas.execution_request import ModelRef


class ProxyKeyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=100)
    models: dict[str, ModelRef] = Field(min_length=1)
    expires_in_days: int = Field(default=30, ge=1, le=365)
    requests_per_minute: int = Field(default=30, ge=1, le=1000)


class AccessKeyService:
    def __init__(self, database, signing_key):
        self.keys = database["model_proxy_keys"]
        self.rates = database["model_proxy_rates"]
        self.runs = database["agent_runs"]
        self.signing_key = signing_key

    async def ensure_indexes(self):
        await self.keys.create_index("token_hash", unique=True)
        await self.rates.create_index("expires_at", expireAfterSeconds=0)

    def issue_run_token(self, run_id, user_id, model_ref, expires_at):
        if not self.signing_key or len(self.signing_key) < 32:
            raise ValueError("APP_AGENT_SIGNING_KEY must contain at least 32 characters.")
        return jwt.encode({
            "iss": "four-season-hub", "aud": "model-gateway", "sub": user_id,
            "run_id": run_id, "model_ref": model_ref.model_dump(),
            "exp": expires_at, "iat": datetime.now(UTC),
        }, self.signing_key, algorithm="HS256")

    async def verify_run_token(self, token, request):
        try:
            if not self.signing_key:
                raise ValueError("Run authentication is unavailable.")
            claims = jwt.decode(token, self.signing_key, algorithms=["HS256"],
                                audience="model-gateway", issuer="four-season-hub",
                                options={"require": ["exp", "sub", "run_id", "model_ref"]})
        except (jwt.PyJWTError, ValueError) as exc:
            raise PermissionError("Invalid execution token.") from exc
        if claims["run_id"] != request.run_id or claims["model_ref"] != request.model_ref.model_dump():
            raise PermissionError("Execution token does not authorize this model or run.")
        run = await self.runs.find_one({"_id": request.run_id, "user_id": claims["sub"]})
        if run is None or run["status"] not in {"preparing", "running"}:
            raise PermissionError("Execution is no longer active.")
        deadline = run["expires_at"]
        if deadline.tzinfo is None:
            deadline = deadline.replace(tzinfo=UTC)
        if deadline <= datetime.now(UTC):
            raise PermissionError("Execution deadline expired.")
        return max(0.01, (deadline - datetime.now(UTC)).total_seconds())

    async def create_proxy_key(self, request, owner):
        key = "hub_" + secrets.token_urlsafe(32)
        key_id = secrets.token_hex(16)
        await self.keys.insert_one({
            "_id": key_id, "name": request.name, "owner": owner,
            "token_hash": hashlib.sha256(key.encode()).hexdigest(),
            "models": {alias: ref.model_dump() for alias, ref in request.models.items()},
            "requests_per_minute": request.requests_per_minute,
            "expires_at": datetime.now(UTC) + timedelta(days=request.expires_in_days),
            "enabled": True, "created_at": datetime.now(UTC),
        })
        return {"id": key_id, "api_key": key, "models": list(request.models)}

    async def authenticate_proxy(self, token, count=True):
        key = await self.keys.find_one({
            "token_hash": hashlib.sha256(token.encode()).hexdigest(),
            "enabled": True, "expires_at": {"$gt": datetime.now(UTC)},
        })
        if key is None:
            raise PermissionError("Invalid proxy key.")
        if count:
            minute = int(time.time() // 60)
            from pymongo import ReturnDocument
            from pymongo.errors import DuplicateKeyError
            query = {"_id": f"{key['_id']}:{minute}"}
            update = {"$inc": {"count": 1}, "$setOnInsert": {
                "expires_at": datetime.now(UTC) + timedelta(minutes=2),
            }}
            try:
                usage = await self.rates.find_one_and_update(
                    query, update, upsert=True, return_document=ReturnDocument.AFTER,
                )
            except DuplicateKeyError:
                usage = await self.rates.find_one_and_update(
                    query, {"$inc": {"count": 1}}, return_document=ReturnDocument.AFTER,
                )
            if usage["count"] > key["requests_per_minute"]:
                raise OverflowError("Proxy rate limit exceeded.")
        return key

    async def list_keys(self):
        return [d async for d in self.keys.find({}, {"token_hash": 0})]

    async def revoke_key(self, key_id):
        result = await self.keys.update_one({"_id": key_id}, {"$set": {"enabled": False}})
        return result.matched_count > 0
