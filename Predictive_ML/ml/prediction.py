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


async def predict(model_name,asset_id):
    '''
    Docstring for predict
    
    :param model: Description
    :param telemetry_data: Description
    '''
    telemetry_data = FetchAssetsTelemetry().get_telemetry_data_asset(asset_id)
    
    if not telemetry_data:
        logging.error(f"No telemetry data found for asset {asset_id}. Cannot make prediction.")
        return None
    
    processor = TelemetryProcessor(telemetry_data)
    
    window_length = await redis_client.get(f"Window_length:{asset_id}")
    if not window_length:
        logging.warning(f"No window length found for asset {asset_id}. Using default window length of 10.")
        window_length = 10
    else:
        window_length = int(window_length)
    
    aggregated = processor.aggregate_window(window_length)
    
    #handle missing windows by forward filling last known value (up to a limit)
    
    processed_data = telemetry_processor.handle_missing_windows(aggregated)
    
    threshold_map = await redis_client.get(f"threshold_map:{asset_id}")
    
    if threshold_map:
        threshold_map = json.loads(threshold_map)
    else:
        logging.warning(f"No threshold map found for asset {asset_id}. Using empty map.")
        threshold_map = {}
        
    labeled_data = telemetry_processor.label_data(
        processed_data, threshold_map
    )
        
    model, metadata = await load_model(model_name)  # async call to Redis
    
    predictions = await TrainService.future_predict(labeled_data,model,metadata)  # preprocess + model.predict()
    
    # need data for the api for confution matrix and metrics dashboard, so we return it here. In a real system, we might store this in a DB instead.
    await store_prediction({
        "asset_id": asset_id,
        "model_name": model_name,
        "horizon": metadata.get("horizon"),
        "confusion_matrix": predictions.get("confusion_matrix"),
        "data": predictions
    })  # async store in Redis for later retrieval
    
    return {
    "status": "success",
    "asset_id": asset_id,
    "model_name": model_name,
    "horizon": metadata.get("horizon"),
    "confusion_matrix": predictions.get("confusion_matrix"),
    "data": predictions
    }

async def predict_specific(model_name,asset_id):
    '''
    Docstring for predict_specific
    
    :param model: Description
    :param telemetry_data: Description
    '''
    telemetry_data = FetchAssetsTelemetry().get_telemetry_data_asset(asset_id)
    
    if not telemetry_data:
        logging.error(f"No telemetry data found for asset {asset_id}. Cannot make prediction.")
        return None
    
    processor = TelemetryProcessor(telemetry_data)
    
    window_length = await redis_client.get(f"Window_length:{asset_id}")
    if not window_length:
        logging.warning(f"No window length found for asset {asset_id}. Using default window length of 10.")
        window_length = 10
    else:
        window_length = int(window_length)
    
    aggregated = processor.aggregate_window(window_length)
    
    #handle missing windows by forward filling last known value (up to a limit)
    
    processed_data = telemetry_processor.handle_missing_windows(aggregated)
    model, metadata = await load_model(model_name)  # async call to Redis
    equipment_type = metadata.get("equipment_type")
    
    # Threshold map according to the model_name for each sensor present in the asset for its monitoring.
    ggoi = re.sub(r'_\d{14}$', '', model_name)
    print("entered into redis")
    sensor_map_json = await redis_client.get(f"sensor_map:{ggoi}")
    print(sensor_map_json)
    sensor_map = json.loads(sensor_map_json)
    print(sensor_map)
        # sensor_map = {"vibration": "Vibration", "temperature": "Temperature", "stator_current": "Stator_Current", ...}
        # 🔹 Define thresholds per sensor (values are model-specific)
    if equipment_type== "Slipring Induction motor 60kw":
        sensor_thresholds = {
            "Vibration_avg": {"prefailure": 5.0, "failure": 7.0},
                "Temperature_avg": {"prefailure": 80.0, "failure": 90.0},
                "Stator_Current_avg": {"prefailure": 10.0, "failure": 15.0},
                "Rotor_Current_avg": {"prefailure": 8.0, "failure": 12.0}
            }
            # 🔹 Build threshold_map using only sensors registered in Redis
        threshold_map = {
            sensor_map[key]: value
            for key, value in sensor_thresholds.items()
            if key in sensor_map
        }
        
    print (threshold_map)        
    equipment_type = metadata.get("equipment_type")

    df = pd.DataFrame(processed_data)

    df = convert_telemetry_to_dataframe_for_prediction(df)

    if equipment_type not in EQUIPMENT_LABELERS:
        raise ValueError(f"Unsupported equipment type: {equipment_type}")

    label_function = EQUIPMENT_LABELERS[equipment_type]

    df = label_function(df, threshold_map)

    df = df.sort_values("window_start")

    predictions = await TrainService.predict_future_asset(df, model, metadata)
    
    store_prediction({
        "asset_id": asset_id,
        "model_name": model_name,
        "horizon": metadata.get("horizon"),
        "confusion_matrix": predictions.get("confusion_matrix"),
        "data": predictions
    })  # async store in Redis for later retrieval

    return {
        "status": "success",
        "asset_id": asset_id,
        "model_name": model_name,
        "horizon": metadata.get("horizon"),
        "confusion_matrix": predictions.get("confusion_matrix"),
        "data": predictions
    }