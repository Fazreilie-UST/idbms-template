from typing import Optional
from pydantic import BaseModel, ConfigDict


class DimMetricOut(BaseModel):
    metric_id: int
    metric_name: str
    statement_id: int
    parent_metric_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)