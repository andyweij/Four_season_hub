from pydantic import BaseModel, ConfigDict, Field


class WebSearchOptions(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    max_iterations: int = Field(default=3, ge=1, le=10)
    max_search_calls: int = Field(default=5, ge=1, le=20)
    max_results_per_search: int = Field(default=3, ge=1, le=10)
