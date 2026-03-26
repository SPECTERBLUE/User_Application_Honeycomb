import pandas as pd
import logging
from datetime import datetime, timezone
from typing import Dict, Any
from Predictive_ML.ml.trainers.random_forest import train_random_forest
from Predictive_ML.ml.model_store import store_model
from Predictive_ML.pre_trained_models import label_motor_faults
from sklearn.metrics import confusion_matrix
from Predictive_ML.ml.trainers.xgboost import train_xgboost
from Predictive_ML.ml.trainers.lstm import train_lstm
import numpy as np
import torch
from sklearn.metrics import confusion_matrix

def create_sequences(df, feature_cols, target_col, seq_length, horizon_steps, prediction_type):
    X, y = [], []

    for i in range(len(df) - seq_length - horizon_steps + 1):
        seq_x = df.iloc[i:i+seq_length][feature_cols].values

        if prediction_type == "fault":
            future = df.iloc[i+seq_length:i+seq_length+horizon_steps][target_col]
            seq_y = int(future.max() > 0)

        else:  # sensor
            seq_y = df.iloc[
                i+seq_length:i+seq_length+horizon_steps
            ][target_col].values

        X.append(seq_x)
        y.append(seq_y)

    return np.array(X), np.array(y)

EQUIPMENT_LABELERS = {
    "Slipring Induction motor 60kw": label_motor_faults,
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

def convert_telemetry_to_dataframe_for_prediction(df: pd.DataFrame) -> pd.DataFrame:
    """
    Converts long-format telemetry into wide ML-ready dataframe for PREDICTION.
    
    Unlike covert_csv_to_dataframe(), this does NOT require a 'label' column,
    since labels don't exist yet during prediction — they are generated 
    afterwards by the equipment-specific labeling function.

    Input columns:
    sensor, window_start, count, avg, min, max, status

    Output:
    window_start, sensor_1_avg, sensor_2_avg, ..., status
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

    # 🔹 Bring status (per window) — NO label
    meta_df = df.groupby("window_start").agg({
        "status": resolve_window_status
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

        # 🔹 Load + preprocess
        df = pd.read_csv(csv_path)
        df = covert_csv_to_dataframe(df)

        if target_column not in df.columns:
            raise ValueError(f"{target_column} not found in dataset")

        df = df.sort_values("window_start")

        steps = horizon_to_steps(horizon, freq_minutes)

        prediction_type = "sensor" if target_column != "label" else "fault"

        # 🔹 Filter valid rows
        if "status" in df.columns:
            df = df[df["status"] == "OK"]

        # 🔹 Feature columns
        feature_cols = [
            col for col in df.columns
            if col not in ["window_start", "status", target_column]
        ]

        # =========================================================
        #  LSTM (SEQUENCE MODEL)
        # =========================================================
        if algorithm == "lstm":
            

            seq_length = 20  # can be made configurable

            X_seq, y_seq = create_sequences(
                df,
                feature_cols=feature_cols,
                target_col=target_column,
                seq_length=seq_length,
                horizon_steps=steps,
                prediction_type=prediction_type
            )

            if len(X_seq) == 0:
                raise ValueError("Not enough data to create sequences")

            model = train_lstm(X_seq, y_seq, prediction_type)

            metrics = {
                "info": "LSTM trained (basic metrics not implemented)"
            }

            features_used = feature_cols

        # =========================================================
        #  TABULAR MODELS (RF / XGBOOST)
        # =========================================================
        else:
            # 🔹 create FUTURE label (only for tabular models)
            df[target_column] = df[target_column].shift(-steps)
            df = df.dropna(subset=[target_column])

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

            features_used = list(X.columns)

        # =========================================================
        #  MODEL METADATA
        # =========================================================
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        model_name = f"{user_model_name}_{timestamp}"

        metadata = {
            "algorithm": algorithm,
            "target_column": target_column,
            "horizon": horizon,
            "metrics": metrics,
            "trained_at": timestamp,
            "prediction_type": prediction_type,
            "freq_minutes": freq_minutes,
            "rows": len(df),
            "features": features_used
        }

        #  Extra metadata for LSTM
        if algorithm == "lstm":
            metadata.update({
                "sequence_length": seq_length,
                "horizon_steps": steps
            })

        #  Store model
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

        # 🔹 Convert telemetry → wide format
        df = covert_csv_to_dataframe(df)

        # ---------------------------------
        # 🔹 Equipment specific labeling
        # ---------------------------------
        if equipment_type not in EQUIPMENT_LABELERS:
            raise ValueError(f"Unsupported equipment type: {equipment_type}")

        label_function = EQUIPMENT_LABELERS[equipment_type]
        df = label_function(df, thresholds)

        df = df.sort_values("window_start")

        steps = horizon_to_steps(horizon, freq_minutes)

        prediction_type = "sensor" if target_column != "label" else "fault"

        # ---------------------------------
        # 🔹 Filter valid rows
        # ---------------------------------
        if "status" in df.columns:
            df = df[df["status"] == "OK"]

        # 🔹 Feature columns
        feature_cols = [
            col for col in df.columns
            if col not in ["window_start", "status", target_column]
        ]

        # =========================================================
        # LSTM (SEQUENCE MODEL)
        # =========================================================
        if algorithm == "lstm":

            seq_length = 20

            X_seq, y_seq = create_sequences(
                df,
                feature_cols=feature_cols,
                target_col=target_column,
                seq_length=seq_length,
                horizon_steps=steps,
                prediction_type=prediction_type
            )

            if len(X_seq) == 0:
                raise ValueError("Not enough data to create sequences")

            model = train_lstm(X_seq, y_seq, prediction_type)

            metrics = {
                "info": "LSTM trained (basic metrics not implemented)"
            }

            features_used = feature_cols

        # =========================================================
        # TABULAR MODELS (RF / XGBOOST)
        # =========================================================
        else:

            # 🔹 create FUTURE label (ONLY for tabular models)
            df[target_column] = df[target_column].shift(-steps)
            df = df.dropna(subset=[target_column])

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

            features_used = list(X.columns)

        # =========================================================
        # 🔹 MODEL METADATA
        # =========================================================
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        model_name = f"{user_model_name}_{timestamp}"

        metadata = {
            "algorithm": algorithm,
            "equipment_type": equipment_type,
            "target_column": target_column,
            "horizon": horizon,
            "metrics": metrics,
            "prediction_type": prediction_type,
            "trained_at": timestamp,
            "freq_minutes": freq_minutes,
            "rows": len(df),
            "features": features_used
        }

        # 🔹 Extra metadata for LSTM
        if algorithm == "lstm":
            metadata.update({
                "sequence_length": seq_length,
                "horizon_steps": steps
            })

        # 🔹 Store model
        await store_model(model_name, model, metadata)

        return {
            "model_name": model_name,
            "metrics": metrics,
            "metadata": metadata
        }

    @staticmethod
    async def future_predict(data, model, metadata):

        if not data:
            logging.error("No data received for prediction.")
            return None

        # 🔹 Convert
        df = pd.DataFrame(data)
        df = covert_csv_to_dataframe(df)
        df = df.sort_values("window_start")

        expected_features = metadata.get("features", [])
        horizon = metadata.get("horizon")
        freq_minutes = metadata.get("freq_minutes", 5)
        algorithm = metadata.get("algorithm")
        prediction_type = metadata.get("prediction_type")

        # 🔹 Validate features
        missing_features = [
            col for col in expected_features if col not in df.columns
        ]
        if missing_features:
            raise ValueError(f"Missing features: {missing_features}")

        steps = horizon_to_steps(horizon, freq_minutes)

        # =========================================================
        # LSTM
        # =========================================================
        if algorithm == "lstm":

            seq_len = metadata.get("sequence_length")

            if len(df) < seq_len:
                raise ValueError("Not enough data for LSTM")

            seq = df.iloc[-seq_len:][expected_features].values
            X = torch.tensor(seq, dtype=torch.float32).unsqueeze(0)

            model.eval()
            with torch.no_grad():
                output = model(X).numpy().flatten()

            base_ts = df["window_start"].iloc[-1]

            timestamps = [
                base_ts + (i + 1) * freq_minutes * 60
                for i in range(steps)
            ]

            # 🔹 Fault
            if prediction_type == "fault":
                probs = torch.sigmoid(torch.tensor(output)).numpy().tolist()
                values = [1 if p > 0.5 else 0 for p in probs]
                confidence = [abs(p - 0.5) * 2 for p in probs]
                cm = None

            # 🔹 Sensor
            else:
                values = output.tolist()
                probs = None
                confidence = [1.0] * len(values)
                cm = None

            return {
                "timestamps": timestamps,
                "values": values,
                "probabilities": probs,
                "confidence": confidence,
                "confusion_matrix": cm,
                "meta": {
                    "type": prediction_type,
                    "mode": "multi_step",
                    "horizon": horizon
                }
            }

        # =========================================================
        # RF / XGBOOST
        # =========================================================
        else:

            latest_row = df.iloc[-1:]
            X = latest_row[expected_features]

            y_pred = model.predict(X)

            if hasattr(model, "predict_proba"):
                y_prob = model.predict_proba(X)
            else:
                y_prob = None

            timestamp = latest_row["window_start"].iloc[0]

            timestamps = [
                timestamp + (i + 1) * freq_minutes * 60
                for i in range(steps)
            ]

            # 🔹 Expand prediction
            values = [y_pred[0]] * steps

            # 🔹 Fault
            if prediction_type == "fault" and y_prob is not None:
                base_prob = y_prob[0]
                probs = [base_prob.tolist()] * steps
                confidence = [max(base_prob)] * steps
            else:
                probs = None
                confidence = [1.0] * steps

            # 🔹 Confusion Matrix (optional)
            cm = None
            if prediction_type == "fault" and "label" in df.columns:
                try:
                    y_true = df["label"].iloc[-steps:].tolist()
                    y_pred_expanded = values[:len(y_true)]
                    cm = confusion_matrix(y_true, y_pred_expanded).tolist()
                except Exception:
                    cm = None

            return {
                "timestamps": timestamps,
                "values": values,
                "probabilities": probs,
                "confidence": confidence,
                "confusion_matrix": cm,
                "meta": {
                    "type": prediction_type,
                    "mode": "single_step",
                    "horizon": horizon
                }
            }

    
    @staticmethod
    async def predict_future_asset(df: pd.DataFrame, model, metadata: dict) -> dict:


        if df.empty:
            logging.error("Empty DataFrame received for asset prediction.")
            return None

        df = df.sort_values("window_start")

        expected_features = metadata.get("features", [])
        horizon = metadata.get("horizon")
        freq_minutes = metadata.get("freq_minutes", 5)
        algorithm = metadata.get("algorithm")
        prediction_type = metadata.get("prediction_type")

        # 🔹 Validate features
        missing_features = [
            col for col in expected_features if col not in df.columns
        ]
        if missing_features:
            raise ValueError(f"Missing features: {missing_features}")

        steps = horizon_to_steps(horizon, freq_minutes)

        # =========================================================
        # 🔵 LSTM
        # =========================================================
        if algorithm == "lstm":

            seq_len = metadata.get("sequence_length")

            if len(df) < seq_len:
                raise ValueError("Not enough data for LSTM prediction")

            seq = df.iloc[-seq_len:][expected_features].values
            X = torch.tensor(seq, dtype=torch.float32).unsqueeze(0)

            model.eval()
            with torch.no_grad():
                output = model(X).numpy().flatten()

            base_ts = df["window_start"].iloc[-1]

            timestamps = [
                base_ts + (i + 1) * freq_minutes * 60
                for i in range(steps)
            ]

            if prediction_type == "fault":
                probs = torch.sigmoid(torch.tensor(output)).numpy().tolist()
                values = [1 if p > 0.5 else 0 for p in probs]
                confidence = [abs(p - 0.5) * 2 for p in probs]
                cm = None
            else:
                values = output.tolist()
                probs = None
                confidence = [1.0] * len(values)
                cm = None

            return {
                "timestamps": timestamps,
                "values": values,
                "probabilities": probs,
                "confidence": confidence,
                "confusion_matrix": cm,
                "meta": {
                    "type": prediction_type,
                    "mode": "multi_step",
                    "horizon": horizon
                }
            }

        # =========================================================
        # 🟢 RF / XGBOOST
        # =========================================================
        else:

            latest_row = df.iloc[-1:]
            X = latest_row[expected_features]

            y_pred = model.predict(X)

            if hasattr(model, "predict_proba"):
                y_prob = model.predict_proba(X)
            else:
                y_prob = None

            timestamp = latest_row["window_start"].iloc[0]

            timestamps = [
                timestamp + (i + 1) * freq_minutes * 60
                for i in range(steps)
            ]

            values = [y_pred[0]] * steps

            if prediction_type == "fault" and y_prob is not None:
                base_prob = y_prob[0]
                probs = [base_prob.tolist()] * steps
                confidence = [max(base_prob)] * steps
            else:
                probs = None
                confidence = [1.0] * steps

            # 🔹 Optional confusion matrix
            cm = None
            if prediction_type == "fault" and "label" in df.columns:
                try:
                    y_true = df["label"].iloc[-steps:].tolist()
                    y_pred_expanded = values[:len(y_true)]
                    cm = confusion_matrix(y_true, y_pred_expanded).tolist()
                except Exception:
                    cm = None

            return {
                "timestamps": timestamps,
                "values": values,
                "probabilities": probs,
                "confidence": confidence,
                "confusion_matrix": cm,
                "meta": {
                    "type": prediction_type,
                    "mode": "single_step",
                    "horizon": horizon
                }
            }