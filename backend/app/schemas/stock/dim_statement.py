from pydantic import BaseModel, ConfigDict


class DimStatementOut(BaseModel):
    statement_id: int
    statement_name: str

    model_config = ConfigDict(from_attributes=True)