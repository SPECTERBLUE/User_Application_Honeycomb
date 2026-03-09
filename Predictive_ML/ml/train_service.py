import pandas as pd
import logging
from datetime import datetime, timezone
from typing import Dict, Any
from Predictive_ML.ml.trainers.random_forest import train_random_forest
from Predictive_ML.ml.model_store import store_model
from Predictive_ML.pre_trained_models import label_motor_faults
from sklearn.metrics import confusion_matrix
from Predictive_ML.ml.trainers.xgboost import train_xgboost

EQUIPMENT_LABELERS = {
    "Slipring_Induction_motor_60kw": label_motor_faults,
    # future
    # "centrifugal_pump": label_pump_faults,
    # "compressor": label_compressor_faults
}

def resolve_window_status(status_series):
    if "NOT_WORKING" in status_series.values:
        return "NOT_WORKING"
    elif "FILLED" in status_series.values:
        return "FILLED"
    else:
        return "OK"
    
def horizon_to_steps(horizon: str, freq_minutes: int) -> int:
    horizon_map = {
        "1h": 60,
        "6h": 360,
        "24h": 1440
    }

    if horizon not in horizon_map:
        raise ValueError("Invalid horizon. Use 1h, 6h, 24h")

    return horizon_map[horizon] // freq_minutes

def covert_csv_to_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    '''
    Docstring for covert_csv_to_dataframe
    
    :param df: Description
    '''
    # sensor,window_start,count,avg,min,max,status,label --- original csv columns
    # need to covert the coloums to window_start,sensor_name_n,label,status
    # where n is the sensor number (1,2,3..)
    
    '''
    sensor,window_start,count,avg,min,max,status,label
    Vibration,1771831768,1,0.754,0.754,0.754,OK,0
    Vibration,1771831772,1,1.156,1.156,1.156,OK,1
    Vibration,1771831776,1,0.064,0.064,0.064,OK,0
    Temp,1771831768,1,35.2,35.2,35.2,OK,0
    Temp,1771831772,1,36.5,36.5,36.5,OK,1
    Temp,1771831776,1,34.8,34.8,34.8,OK,0
    Pressure,1771831768,1,101.3,101.3,101.3,OK,0
    Pressure,1771831772,1,102.5,102.5,102.5,OK,1
    Pressure,1771831776,1,100.8,100.8,100.8,OK,0
    '''
    """
    Converts long-format telemetry CSV into wide ML-ready dataframe.

    Input columns:
    sensor, window_start, count, avg, min, max, status, label

    Output:
    window_start, sensor_1, sensor_2, ..., status, label
    """
    if df.empty:
        raise ValueError("Input dataframe is empty")

    # 🔹 Ensure proper sorting
    df = df.sort_values(["window_start", "sensor"])

    # 🔹 Pivot → wide format
    pivot_df = df.pivot(
        index="window_start",
        columns="sensor",
        values="avg"
    )
    
    # 🔹 Rename columns → Vibration → Vibration_avg
    pivot_df.columns = [f"{col}_avg" for col in pivot_df.columns]

    # 🔹 Bring status + label (per window)
    meta_df = df.groupby("window_start").agg({
        "status": resolve_window_status,
        "label": "first"
    })

    # 🔹 Merge
    final_df = pivot_df.join(meta_df)

    # 🔹 Reset index → make window_start a column
    final_df = final_df.reset_index()
    final_df = final_df.reindex(sorted(final_df.columns), axis=1)

    # 🔹 Sort by time
    final_df = final_df.sort_values("window_start")

    return final_df
    

class TrainService:

    async def train(
        self,
        csv_path: str,
        target_column: str,
        user_model_name: str,
        horizon: str,
        algorithm: str = "random_forest",
        test_size: float = 0.2,
        random_state: int = 42,
        freq_minutes: int = 5
    ) -> Dict[str, Any]:

        df = pd.read_csv(csv_path)
        df = covert_csv_to_dataframe(df)

        if target_column not in df.columns:
            raise ValueError(f"{target_column} not found in dataset")
        
        # Convert horizon to steps        steps = horizon_to_steps(horizon, freq_minutes)
        df = df.sort_values("window_start")
        
        # convert horizon → number of rows to shift
        steps = horizon_to_steps(horizon, freq_minutes)

        # create FUTURE label
        df[target_column] = df[target_column].shift(-steps)

        # drop rows that don’t have future label
        df = df.dropna(subset=[target_column])

        # keep only healthy windows
        if "status" in df.columns:
            df = df[df["status"] == "OK"]

        # Drop non-feature columns
        drop_cols = [target_column, "window_start"]

        if "status" in df.columns:
            drop_cols.append("status")

        X = df.drop(columns=drop_cols)
        y = df[target_column]

        if algorithm == "random_forest":
            model, metrics = train_random_forest(
                X, y, test_size=test_size, random_state=random_state
            )
        elif algorithm == "xgboost":
            model, metrics = train_xgboost(
                X, y, test_size=test_size, random_state=random_state
            )
        else:
            raise ValueError(f"Unsupported algorithm: {algorithm}")

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        model_name = f"{user_model_name}_{timestamp}"

        metadata = {
            "algorithm": algorithm,
            "target_column": target_column,
            "horizon": horizon,
            "metrics": metrics,
            "trained_at": timestamp,
            "rows": len(df),
            "features": list(X.columns)
        }

        await store_model(model_name, model, metadata)

        return {
            "model_name": model_name,
            "metrics": metrics,
            "metadata": metadata
        }
        
    async def train_specific_model(
        self,
        labeled_data: list,
        target_column: str,
        user_model_name: str,
        horizon: str,
        equipment_type: str,
        thresholds: dict,
        algorithm: str = "random_forest",
        test_size: float = 0.2,
        random_state: int = 42,
        freq_minutes: int = 5
    ) -> Dict[str, Any]:

        df = pd.DataFrame(labeled_data)

        # Convert telemetry → wide format
        df = covert_csv_to_dataframe(df)

        # ---------------------------------
        # Equipment specific labeling
        # ---------------------------------
        if equipment_type not in EQUIPMENT_LABELERS:
            raise ValueError(f"Unsupported equipment type: {equipment_type}")

        label_function = EQUIPMENT_LABELERS[equipment_type]

        df = label_function(df, thresholds)

        df = df.sort_values("window_start")

        # ---------------------------------
        # Convert horizon → prediction steps
        # ---------------------------------
        steps = horizon_to_steps(horizon, freq_minutes)

        df[target_column] = df[target_column].shift(-steps)

        df = df.dropna(subset=[target_column])

        # ---------------------------------
        # Remove unhealthy windows
        # ---------------------------------
        if "status" in df.columns:
            df = df[df["status"] == "OK"]

        drop_cols = [target_column, "window_start"]

        if "status" in df.columns:
            drop_cols.append("status")

        X = df.drop(columns=drop_cols)
        y = df[target_column]

        # ---------------------------------
        # Model selection
        # ---------------------------------
        if algorithm == "random_forest":
            model, metrics = train_random_forest(
                X, y, test_size=test_size, random_state=random_state
            )

        elif algorithm == "xgboost":
            model, metrics = train_xgboost(
                X, y, test_size=test_size, random_state=random_state
            )

        else:
            raise ValueError(f"Unsupported algorithm: {algorithm}")

        # ---------------------------------
        # Store model
        # ---------------------------------
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")

        model_name = f"{user_model_name}_{timestamp}"

        metadata = {
            "algorithm": algorithm,
            "equipment_type": equipment_type,
            "target_column": target_column,
            "horizon": horizon,
            "metrics": metrics,
            "trained_at": timestamp,
            "rows": len(df),
            "features": list(X.columns)
        }

        await store_model(model_name, model, metadata)

        return {
            "model_name": model_name,
            "metrics": metrics,
            "metadata": metadata
        }

    @staticmethod
    async def future_predict(data,model,metadata):
        # This function can be used for future real-time predictions
        # It would preprocess incoming data in the same way as training data
        # and then call model.predict() to get predictions
         
        if not data:
                logging.error("No data received for prediction.")
                return None

        # 🔹 Convert to DataFrame
        df = pd.DataFrame(data)

        # 🔹 Apply SAME transformation used during training
        df = covert_csv_to_dataframe(df)
        
        # 🔹 Ensure sorted (important for latest window selection)
        df = df.sort_values("window_start")

        expected_features = metadata.get("features", [])
        horizon = metadata.get("horizon")
        freq_minutes = metadata.get("freq_minutes", 5)
        
        # 🔹 Validate features
        missing_features = [
            col for col in expected_features if col not in df.columns
        ]

        if missing_features:
            raise ValueError(
                f"Missing features for prediction: {missing_features}"
            )
        
        X = df[expected_features].reindex(columns=expected_features)

        # 🔹 True labels (if present → for confusion matrix)
        y_true = df["label"].tolist() if "label" in df.columns else None

        # 🔹 Predict
        y_pred = model.predict(X)

        if hasattr(model, "predict_proba"):
            y_prob = model.predict_proba(X).tolist()
        else:
            y_prob = None

        # 🔹 Time handling
        timestamps = df["window_start"].tolist()

        # future timestamps for horizon graphs
        steps = horizon_to_steps(horizon, freq_minutes)
        future_timestamps = [
            ts + steps * freq_minutes * 60 for ts in timestamps
        ]
        cm = confusion_matrix(y_true, y_pred).tolist() if y_true else None

        return {
            "timestamps": timestamps,
            "future_timestamps": future_timestamps,
            "y_true": y_true,
            "y_pred": y_pred.tolist(),
            "probabilities": y_prob,
            "confusion_matrix": cm,
            "horizon": horizon
        }