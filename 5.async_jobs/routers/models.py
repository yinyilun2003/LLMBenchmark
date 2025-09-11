from pydantic import BaseModel

class TaskCreate(BaseModel):
    params: str

class TaskOut(BaseModel):
    id: str
    status: str
    result: str | None = None
