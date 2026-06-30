from pydantic import BaseModel, Field

class InferRequest(BaseModel):
    task: str = Field(..., description="Kind of work, e.g. 'chat' or 'sentiment'")
    input: str = Field(..., description="The user's text")
    options: dict = Field(default_factory=dict)

class InferResponse(BaseModel):
    output: str
    backend: str
    cached: bool = False