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


class DB(BaseSchema):
    """Database configuration class."""

    database: str = Field(description="Database name")


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
app_config: AppConfig = AppConfig(**config)
