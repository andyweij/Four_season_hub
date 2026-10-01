class AgentManagementError(Exception):
    code = "agent_management_error"


class AgentNotFoundError(AgentManagementError):
    code = "agent_not_found"


class AgentDisabledError(AgentManagementError):
    code = "agent_disabled"


class AgentNotExecutableError(AgentManagementError):
    code = "agent_not_executable"
