from app.modules.agent_execution.schemas.web_search_options import WebSearchOptions


class TaskPolicy:
    """Normalize a copy. Authorization and readiness are separate checks."""
    def __init__(self, option_schemas=None):
        self.option_schemas = option_schemas or {"web-search": WebSearchOptions}

    def prepare(self, definition, task):
        if task.agent_id != definition.id:
            raise ValueError("Task and agent IDs differ.")
        prepared = task.model_copy(deep=True)
        binding = definition.model_binding
        if binding.type == "hub_per_run":
            prepared.model_ref = prepared.model_ref or binding.default_model_ref
            if prepared.model_ref is None:
                raise ValueError("This agent requires a Hub model.")
        elif prepared.model_ref is not None:
            raise ValueError("This agent does not allow per-run model selection.")
        if prepared.parameters is not None and not definition.capabilities.generation_parameters:
            raise ValueError("This agent does not accept generation parameters.")
        schema = self.option_schemas.get(definition.id)
        if schema is None:
            if prepared.options:
                raise ValueError("No options schema is registered for this agent.")
        else:
            prepared.options = schema.model_validate(prepared.options).model_dump()
        return prepared
