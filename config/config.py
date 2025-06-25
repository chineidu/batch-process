from __future__ import annotations

from pathlib import Path
from typing import Any

from omegaconf import DictConfig, OmegaConf
from pydantic import Field

from schemas import BaseSchema
from src import PACKAGE_PATH


class Data(BaseSchema):
    """Data configuration class.

    Attributes
    ----------
    data_path : str
        Training data path
    """

    data_path: str = Field(description="Training data path")
    batch_data: BatchData = Field(description="Batch data configuration")
    num_vars: list[str] = Field(description="Numeric variables")
    cat_vars: list[str] = Field(description="Categorical variables")

    @property
    def important_columns(self) -> list[str]:
        """Get important columns."""
        return self.num_vars + self.cat_vars


class DB(BaseSchema):
    """Database configuration class."""

    db_path: str = Field(description="Database name")
    max_connections: int = Field(
        description="The maximum connections the database can connect to at a given time."
    )


class Model(BaseSchema):
    """Model configuration class."""

    hyperparams: ModelHyperparams = Field(description="Model hyperparameters")
    artifacts: Artifacts = Field(description="Model artifacts")


class Artifacts(BaseSchema):
    """Model artifacts configuration class."""

    model_path: str = Field(description="Model path")


class ModelHyperparams(BaseSchema):
    """Model hyperparameters configuration class."""

    n_splits: int = Field(description="Number of splits")
    n_estimators: int = Field(description="Number of estimators")
    max_depth: int = Field(description="Maximum depth")
    random_state: int = Field(description="Random state")
    test_size: float = Field(description="Test size")


class BatchData(BaseSchema):
    """Batch data configuration class."""

    is_remote: bool = Field(description="Whether the data is remote")
    remote_data_id: str = Field(description="Remote data id")
    download_path: str = Field(description="Download path")
    batch_mode: bool = Field(description="Whether to use batch mode")
    batch_size: int = Field(description="Batch size")


class Celery(BaseSchema):
    """Celery configuration class."""

    broker_url: str = Field(description="Broker URL")
    result_backend: str = Field(description="Result backend")

    task_configuration: TaskConfiguration = Field(description="Task configuration")
    task_routes: dict[str, Any] = Field(description="Task routes")
    worker_configuration: WorkerConfiguration = Field(description="Worker configuration")
    beat_configuration: BeatConfiguration = Field(description="Beat configuration")


class TaskConfiguration(BaseSchema):
    """Task configuration class."""

    task_serializer: str
    result_serializer: str
    timezone: str
    enable_utc: str


class WorkerConfiguration(BaseSchema):
    worker_prefetch_multiplier: int
    task_acks_late: bool
    worker_max_tasks_per_child: int


class BeatConfiguration(BaseSchema):
    beat_schedule: dict[str, Any]
    health_check: dict[str, Any]


class AppConfig(BaseSchema):
    """Application configuration class.

    Attributes
    ----------
    data : Data
        Data configuration
    db : DB
        Database configuration
    model : Model
        Model configuration
    """

    data: Data = Field(description="Data configuration")
    db: DB = Field(description="Database configuration")
    model: Model = Field(description="Model configuration")


config_path: Path = PACKAGE_PATH / "config/config.yaml"
config: DictConfig = OmegaConf.load(config_path).app_config
app_config: AppConfig = AppConfig(**config)  # type: ignore
