from datetime import UTC, datetime


TERMINAL = {"completed", "failed", "cancelled", "disconnected", "timed_out"}


class AgentRunRepository:
    """Mongo keeps ownership, cancellation and terminal state across Hub workers."""
    def __init__(self, database):
        self.collection = database["agent_runs"]

    async def ensure_indexes(self):
        await self.collection.create_index([("user_id", 1), ("created_at", -1)])
        await self.collection.create_index([("agent_id", 1), ("status", 1)])

    async def create(self, run):
        await self.collection.insert_one(run)

    async def get(self, run_id, user_id=None):
        query = {"_id": run_id}
        if user_id is not None:
            query["user_id"] = user_id
        return await self.collection.find_one(query)

    async def update_active(self, run_id, values):
        result = await self.collection.update_one(
            {"_id": run_id, "status": {"$nin": list(TERMINAL)}}, {"$set": values},
        )
        return result.modified_count > 0

    async def request_cancel(self, run_id):
        return await self.update_active(run_id, {"cancel_requested": True})

    async def terminal(self, run_id, status, **fields):
        return await self.update_active(run_id, {
            "status": status, "finished_at": datetime.now(UTC), **fields,
        })

    async def expire_stale(self):
        # A crashed worker cannot resume runs. Never claim remote cancellation.
        await self.collection.update_many(
            {"status": {"$nin": list(TERMINAL)}, "expires_at": {"$lte": datetime.now(UTC)}},
            {"$set": {"status": "timed_out", "finished_at": datetime.now(UTC),
                      "remote_status": "unconfirmed"}},
        )

    async def active_for_agent(self, agent_id):
        await self.expire_stale()
        return await self.collection.count_documents({
            "agent_id": agent_id, "status": {"$nin": list(TERMINAL)},
        })
