import os
import pandas as pd
from datetime import datetime, timezone

from Predictive_ML.ml.trainers.random_forest import train_random_forest
from Predictive_ML.ml.model_store import store_model


class TrainService:

    def __init__(self, model_dir: str = "saved_models"):
        self.model_dir = model_dir
        os.makedirs(self.model_dir, exist_ok=True)

    def train(
        self,
        csv_path: str,
        target_column: str,
        user_model_name: str,
        algorithm: str = "random_forest",
        test_size: float = 0.2,
        random_state: int = 42
    ):
        """
        Main training orchestration
        """

        # Load dataset
        df = pd.read_csv(csv_path)

        if target_column not in df.columns:
            raise ValueError(f"{target_column} not found in dataset")

        X = df.drop(columns=[target_column])
        y = df[target_column]

        # Select algorithm
        if algorithm == "random_forest":
            model, metrics = train_random_forest(
                X, y, test_size=test_size, random_state=random_state
            )
        else:
            raise ValueError(f"Unsupported algorithm: {algorithm}")

        # Build model metadata
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")

        model_name = f"{user_model_name}_{timestamp}.pkl"
        model_path = os.path.join(self.model_dir, model_name)

        # Save model
        store_model(model, model_path)

        return {
            "model_name": model_name,
            "model_path": model_path,
            "algorithm": algorithm,
            "metrics": metrics
        }
