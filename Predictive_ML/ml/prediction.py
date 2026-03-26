import logging
from rich import json
from Predictive_ML import telemetry_processor
from Predictive_ML.fetch_assets_telemetry import FetchAssetsTelemetry
from Predictive_ML.telemetry_processor import TelemetryProcessor
from Predictive_ML.ml.model_store import load_model
from captcha_utils import redis_client
from Predictive_ML.ml.predition_store import store_prediction
from Predictive_ML.ml.train_service import TrainService
from Predictive_ML.ml.train_service import EQUIPMENT_LABELERS, covert_csv_to_dataframe, convert_telemetry_to_dataframe_for_prediction
import pandas as pd
import re
import numpy as np

def convert_numpy(obj):
    """
    Recursively convert numpy / pandas types to native Python types
    so they can be JSON serialized.
    """
    if isinstance(obj, dict):
        return {k: convert_numpy(v) for k, v in obj.items()}

    elif isinstance(obj, list):
        return [convert_numpy(item) for item in obj]

    elif isinstance(obj, tuple):
        return tuple(convert_numpy(item) for item in obj)

    elif isinstance(obj, (np.integer,)):
        return int(obj)

    elif isinstance(obj, (np.floating,)):
        return float(obj)

    elif isinstance(obj, (np.ndarray,)):
        return obj.tolist()

    return obj

async def predict(model_name, asset_id):

    telemetry_data = FetchAssetsTelemetry().get_telemetry_data_asset(asset_id)

    if not telemetry_data:
        logging.error(f"No telemetry data found for asset {asset_id}.")
        return None

    processor = TelemetryProcessor(telemetry_data)

    # 🔹 Window length
    window_length = await redis_client.get(f"Window_length:{asset_id}")
    window_length = int(window_length) if window_length else 10

    # 🔹 Aggregate + clean
    aggregated = processor.aggregate_window(window_length)
    processed_data = telemetry_processor.handle_missing_windows(aggregated)

    # 🔹 Thresholds
    threshold_map = await redis_client.get(f"threshold_map:{asset_id}")
    threshold_map = json.loads(threshold_map) if threshold_map else {}

    labeled_data = telemetry_processor.label_data(
        processed_data, threshold_map
    )

    # 🔹 Load model
    model, metadata = await load_model(model_name)

    # 🔹 Predict
    predictions = await TrainService.future_predict(
        labeled_data, model, metadata
    )

    # 🔹 Build response
    prediction_data = {
        "asset_id": asset_id,
        "model_name": model_name,
        "horizon": metadata.get("horizon"),
        "data": predictions
    }

    # FIX: Convert numpy → Python types
    cleaned_prediction_data = convert_numpy(prediction_data)

    # 🔹 Store in Redis
    await store_prediction(cleaned_prediction_data)

    return {
        "status": "success",
        **cleaned_prediction_data
    }

async def predict_specific(model_name, asset_id):

    # 🔹 Fetch telemetry
    telemetry_data = FetchAssetsTelemetry().get_telemetry_data_asset(asset_id)

    if not telemetry_data:
        logging.error(f"No telemetry data found for asset {asset_id}.")
        return None

    processor = TelemetryProcessor(telemetry_data)

    # =========================================================
    # 🔹 Window length
    # =========================================================
    window_length = await redis_client.get(f"Window_length:{asset_id}")
    window_length = int(window_length) if window_length else 10

    # =========================================================
    # 🔹 Aggregate + clean
    # =========================================================
    aggregated = processor.aggregate_window(window_length)
    processed_data = telemetry_processor.handle_missing_windows(aggregated)

    # =========================================================
    # 🔹 Load model
    # =========================================================
    model, metadata = await load_model(model_name)
    equipment_type = metadata.get("equipment_type")

    if not equipment_type:
        raise ValueError("Model metadata missing 'equipment_type'")

    # =========================================================
    # 🔹 Fetch sensor map from Redis
    # =========================================================
    base_model_name = re.sub(r'_\d{14}$', '', model_name)

    sensor_map_json = await redis_client.get(f"sensor_map:{base_model_name}")
    if not sensor_map_json:
        raise ValueError("Sensor map not found in Redis")

    sensor_map = json.loads(sensor_map_json)

    # =========================================================
    # 🔹 Equipment-specific thresholds
    # =========================================================
    if equipment_type == "Slipring Induction motor 60kw":

        sensor_thresholds = {
            "Vibration_avg": {"prefailure": 5.0, "failure": 7.0},
            "Temperature_avg": {"prefailure": 80.0, "failure": 90.0},
            "Stator_Current_avg": {"prefailure": 10.0, "failure": 15.0},
            "Rotor_Current_avg": {"prefailure": 8.0, "failure": 12.0}
        }

        threshold_map = {
            sensor_map[key]: value
            for key, value in sensor_thresholds.items()
            if key in sensor_map
        }

    else:
        raise ValueError(f"Unsupported equipment type: {equipment_type}")

    # =========================================================
    # 🔹 Convert → wide dataframe
    # =========================================================
    df = pd.DataFrame(processed_data)
    df = convert_telemetry_to_dataframe_for_prediction(df)

    # =========================================================
    # 🔹 Apply equipment-specific labeling
    # =========================================================
    if equipment_type not in EQUIPMENT_LABELERS:
        raise ValueError(f"Unsupported equipment type: {equipment_type}")

    label_function = EQUIPMENT_LABELERS[equipment_type]
    df = label_function(df, threshold_map)

    df = df.sort_values("window_start")

    # =========================================================
    # 🔹 Predict (USING FIXED FUNCTION)
    # =========================================================
    predictions = await TrainService.predict_future_asset(
        df, model, metadata
    )

    # =========================================================
    # 🔹 Build response
    # =========================================================
    prediction_data = {
        "asset_id": asset_id,
        "model_name": model_name,
        "horizon": metadata.get("horizon"),
        "data": predictions
    }

    # 🔹 Convert numpy → JSON safe
    cleaned_prediction_data = convert_numpy(prediction_data)

    # =========================================================
    # 🔹 Store in Redis
    # =========================================================
    await store_prediction(cleaned_prediction_data)

    # =========================================================
    # 🔹 Final response (UNIFIED)
    # =========================================================
    return {
        "status": "success",
        **cleaned_prediction_data
    }