from datetime import datetime

from pydantic import BaseModel


class EvalRunOut(BaseModel):
    id: str
    dataset_size: int
    metrics: dict
    results_path: str
    created_at: datetime

    model_config = {"from_attributes": True}
