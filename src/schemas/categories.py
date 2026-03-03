from pydantic import BaseModel


class CategoryCreate(BaseModel):
    name: str
    color: str = "#6366f1"
    type: str = "expense"


class CategoryOut(BaseModel):
    id: int
    name: str
    color: str
    type: str

    class Config:
        from_attributes = True
