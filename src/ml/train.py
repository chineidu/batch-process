from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import polars as pl
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold
from sklearn.base import BaseEstimator
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import MinMaxScaler, OneHotEncoder
from sklearn import set_config
from sklearn.model_selection import train_test_split
from tqdm import tqdm

from src import PACKAGE_PATH


set_config(transform_output="polars")


n_splits: int = 5
n_estimators: int = 100
max_depth: int = 5
random_state: int = 42
num_vars: list[str] = ["age", "pclass", "sibsp", "parch", "fare", "survived"]
cat_vars: list[str] = ["sex", "embarked"]
PACKAGE_PATH

def load_data(fp: str) -> pl.DataFrame:
    """Load data from a parquet file.

    Parameters
    ----------
    fp : str
        File path to the parquet file.

    Returns
    -------
    pl.DataFrame
        DataFrame containing the selected important columns.
    """
    important_columns: list[str] = [
        "sex",
        "age",
        "pclass",
        "sibsp",
        "parch",
        "fare",
        "embarked",
        "survived",
    ]
    data: pl.DataFrame = pl.read_parquet(fp).select(important_columns)

    return data


def transform_age(column: str, value: float = 30.00) -> pl.Expr:
    """Transform age column by filling null values.

    Parameters
    ----------
    column : str
        Name of the column to transform.
    value : float, optional
        Value to fill null values with, by default 30.00.

    Returns
    -------
    pl.Expr
        Transformed column expression.
    """
    return (
        pl.when(pl.col(column).is_null())
        .then(pl.lit(value))
        .otherwise(pl.col(column))
        .alias(column)
    )


def prepare_features(data: pl.DataFrame, processor: Pipeline) -> pl.DataFrame:
    """Prepare features by applying the transformation pipeline.

    Parameters
    ----------
    data : pl.DataFrame
        Input DataFrame to transform.
    processor : Pipeline
        Scikit-learn pipeline for feature transformation.

    Returns
    -------
    pl.DataFrame
        Transformed features.
    """
    trnsf_data: pl.DataFrame = processor.fit_transform(data)

    return trnsf_data


def get_transformer(num_vars: list[str], cat_vars: list[str]) -> Pipeline:
    """Create a transformation pipeline for numerical and categorical variables.

    Parameters
    ----------
    num_vars : list[str]
        List of numerical variable names.
    cat_vars : list[str]
        List of categorical variable names.

    Returns
    -------
    Pipeline
        Scikit-learn pipeline with transformers.
    """
    col_transf: ColumnTransformer = ColumnTransformer(
        transformers=[
            ("num_vars", MinMaxScaler(clip=False), num_vars),
            (
                "cat_vars",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                cat_vars,
            ),
        ],
        remainder="drop",
    )
    processor: Pipeline = Pipeline(steps=[("col_transf", col_transf)])

    return processor


def train_model(X_train: pl.DataFrame, X_test: pl.DataFrame) -> BaseEstimator:
    """Train a Random Forest model using cross-validation.

    Parameters
    ----------
    X_train : pl.DataFrame
        Training data including features and target.
    X_test : pl.DataFrame
        Test data including features and target.

    Returns
    -------
    BaseEstimator
        Trained Random Forest model.
    """
    model: RandomForestClassifier = RandomForestClassifier(
        n_estimators=n_estimators, max_depth=max_depth, random_state=random_state
    )
    folds = StratifiedKFold(n_splits=n_splits, random_state=random_state, shuffle=True)

    X_train_: pd.DataFrame = X_train.drop(["num_vars__survived"]).to_pandas()
    X_test_: pd.DataFrame = X_test.drop(["num_vars__survived"]).to_pandas()
    y_train_: pd.DataFrame = X_train["num_vars__survived"].to_pandas()
    y_test_: pd.DataFrame = X_test["num_vars__survived"].to_pandas()

    auc_vals: list[float] = []
    test_auc_vals: list[float] = []

    for train_idx, valid_idx in tqdm(
        folds.split(X_train_, y_train_), desc="Training the model"
    ):
        try:
            X_train_fold, y_train_fold = (
                X_train_.iloc[train_idx],
                y_train_.iloc[train_idx],
            )
            X_test_fold, y_test_fold = (
                X_train_.iloc[valid_idx],
                y_train_.iloc[valid_idx],
            )

            model.fit(
                X_train_fold,
                y_train_fold,
            )

            y_pred_val: np.ndarray = model.predict_proba(X_test_fold)[:, 1]
            y_pred_test: np.ndarray = model.predict_proba(X_test_)[:, 1]
            auc_val: float = roc_auc_score(y_test_fold, y_pred_val)
            auc_vals.append(auc_val)
            test_auc_vals.append(roc_auc_score(y_test_, y_pred_test))

        except Exception as err:
            print(f"{err}")

    mean_auc_seen = np.mean(auc_vals)
    mean_auc_unseen = np.mean(test_auc_vals)
    print(
        f"Mean AUC [Seen]: {mean_auc_seen:.4f} | "
        f"Mean AUC [Unseen]: {mean_auc_unseen:.4f}",
    )

    return model


def main() -> None:
    """Main function to execute the model training pipeline.

    This function loads data, prepares features, trains the model,
    and saves the model and processor to disk.
    """
    print("Loading data and creating features...")
    fp: Path = PACKAGE_PATH / "data/train.parquet"
    data: pl.DataFrame = load_data(fp)
    data = data.with_columns(transform_age("age")).drop_nulls()
    processor: Pipeline = get_transformer(num_vars, cat_vars)
    data_features: pl.DataFrame = prepare_features(data, processor)
    X_train, X_test = train_test_split(
        data_features,
        test_size=0.2,
        stratify=data_features["num_vars__survived"],
        random_state=random_state,
    )
    print("Training model...")
    model: BaseEstimator = train_model(X_train=X_train, X_test=X_test)
    model_dict: dict[str, Any] = {"processor": processor, "model": model}

    with open("model.pkl", "wb") as f:
        joblib.dump(model_dict, f)
    print("Model saved successfully...")

if __name__ == "__main__":
    main()