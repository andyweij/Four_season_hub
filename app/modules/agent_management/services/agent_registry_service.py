from app.modules.agent_management.exceptions import (
    AgentNotFoundError, AgentDisabledError, AgentNotExecutableError,
)


class AgentRegistryService:
    def __init__(self, catalog, database=None):
        self.catalog = catalog
        self.overrides = database["agent_settings"] if database is not None else None

    async def get_definition(self, agent_id):
        agent = await self.catalog.get(agent_id)
        if agent is None:
            raise AgentNotFoundError("Agent was not found.")
        if self.overrides is not None:
            override = await self.overrides.find_one({"_id": agent_id})
            if override:
                agent.enabled = override["enabled"]
        return agent

    async def list_definitions(self):
        return [await self.get_definition(a.id) for a in await self.catalog.list_all()]

    async def get_executable_definition(self, agent_id):
        agent = await self.get_definition(agent_id)
        if not agent.enabled:
            raise AgentDisabledError("Agent is disabled.")
        if agent.integration.type == "registration_only" or not agent.capabilities.task_submission:
            raise AgentNotExecutableError("Agent has no task integration.")
        return agent

    async def set_enabled(self, agent_id, enabled):
        await self.get_definition(agent_id)
        if self.overrides is None:
            raise AgentNotExecutableError("Persistent settings are unavailable.")
        await self.overrides.update_one(
            {"_id": agent_id}, {"$set": {"enabled": enabled}}, upsert=True,
        )
        return await self.get_definition(agent_id)
