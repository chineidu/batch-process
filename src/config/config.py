from __future__ import annotations

from pathlib import Path

from omegaconf import DictConfig, OmegaConf
from pydantic import Field

from src import PACKAGE_PATH
from src.schemas import BaseSchema


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
    max_connections: int = Field(description="The maximum connections the database can connect to at a given time.")


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


class QueueConfig(BaseSchema):
    queue: str


class TaskConfig(BaseSchema):
    """Task configuration class."""

    task_serializer: str
    result_serializer: str
    timezone: str
    enable_utc: bool


class WorkerConfig(BaseSchema):
    """Worker configuration class."""

    worker_prefetch_multiplier: int
    task_acks_late: bool
    worker_max_tasks_per_child: int


class TaskAndSchedule(BaseSchema):
    """Task and schedule class."""

    task: str
    schedule: int


class BeatSchedule(BaseSchema):
    """Beat schedule class."""

    cleanup_old_records: TaskAndSchedule


class BeatConfig(BaseSchema):
    """Beat configuration class."""

    beat_schedule: BeatSchedule
    health_check: TaskAndSchedule


class OtherConfig(BaseSchema):
    """Other configuration class."""

    result_expires: int
    task_compression: str
    result_compression: str
    result_backend_always_retry: bool
    result_persistent: bool
    result_backend_max_retries: int


class CeleryConfig(BaseSchema):
    """Celery configuration class."""

    task_config: TaskConfig = Field(description="Task configuration")
    task_routes: dict[str, QueueConfig] = Field(description="Dictionary of task routes")
    worker_config: WorkerConfig = Field(description="Worker configuration")
    beat_config: BeatConfig = Field(description="Beat configuration")
    other_config: OtherConfig = Field(description="Other configuration")


class AppConfig(BaseSchema):
    """Application configuration class."""

    data: Data = Field(description="Data configuration")
    db: DB = Field(description="Database configuration")
    model: Model = Field(description="Model configuration")
    celery_config: CeleryConfig = Field(description="Celery configuration")


config_path: Path = PACKAGE_PATH / "src/config/config.yaml"
config: DictConfig = OmegaConf.load(config_path).app_config

app_config: AppConfig = AppConfig(**config)  # type: ignore
