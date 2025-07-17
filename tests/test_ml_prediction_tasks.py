import sys
import os
import pytest

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from src.celery_pkg.tasks.ml_prediction_tasks import load_model_task, process_single_prediction, process_batch_predictions

def test_load_model_task():
    """Test loading the ML model."""
    result = load_model_task.apply().get()
    assert result["status"] == "success"
    assert "model_path" in result
    assert "model_keys" in result

def test_process_single_prediction():
    """Test processing a single prediction."""
    person_data = {
        "id": "1",
        "sex": "male",
        "age": 30,
        "pclass": 1,
        "sibsp": 0,
        "parch": 0,
        "fare": 100.0,
        "embarked": "s",
        "survived": 1
    }
    result = process_single_prediction.apply((person_data,)).get()
    assert result["status"] == "success"
    assert result["person_id"] == person_data["id"]

def test_process_batch_predictions():
    """Test processing batch predictions."""
    persons_data = [
        {
            "id": "1",
            "sex": "male",
            "age": 30,
            "pclass": 1,
            "sibsp": 0,
            "parch": 0,
            "fare": 100.0,
            "embarked": "s",
            "survived": 1
        },
        {
            "id": "2",
            "sex": "female",
            "age": 25,
            "pclass": 2,
            "sibsp": 1,
            "parch": 0,
            "fare": 50.0,
            "embarked": "c",
            "survived": 0
        }
    ]
    result = process_batch_predictions.apply((persons_data,)).get()
    assert result["status"] == "dispatched"
    assert result["total_items"] == len(persons_data)

if __name__ == "__main__":
    pytest.main()
