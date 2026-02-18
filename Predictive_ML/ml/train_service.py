import pandas as pd
from datetime import datetime
from typing import Dict, Any

from Predictive_ML.ml.trainers.random_forest import train_random_forest
from Predictive_ML.ml.model_store import store_model


class TrainService:

    async def train(
        self,
        csv_path: str,
        target_column: str,
        user_model_name: str,
        algorithm: str = "random_forest",
        test_size: float = 0.2,
        random_state: int = 42
    ) -> Dict[str, Any]:

        df = pd.read_csv(csv_path)

        if target_column not in df.columns:
            raise ValueError(f"{target_column} not found in dataset")

        X = df.drop(columns=[target_column])
        y = df[target_column]

        # Train
        if algorithm == "random_forest":
            model, metrics = train_random_forest(
                X, y, test_size=test_size, random_state=random_state
            )
        else:
            raise ValueError(f"Unsupported algorithm: {algorithm}")

        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        model_name = f"{user_model_name}_{timestamp}"

        metadata = {
            "algorithm": algorithm,
            "target_column": target_column,
            "metrics": metrics,
            "trained_at": timestamp,
            "rows": len(df),
            "features": list(X.columns)
        }

        #  Store in Redis
        await store_model(
            model_name=model_name,
            model=model,
            metadata=metadata
        )

        return {
            "model_name": model_name,
            "metrics": metrics,
            "metadata": metadata
        }
