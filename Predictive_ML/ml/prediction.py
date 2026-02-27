import logging
from rich import json
from Predictive_ML import telemetry_processor
from fetch_assets_telemetry import FetchAssetsTelemetry
from telemetry_processor import TelemetryProcessor
from model_store import load_model
from captcha_utils import redis_client
from train_service import TrainService
import pandas as pd


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
    
    return {
    "status": "success",
    "asset_id": asset_id,
    "model_name": model_name,
    "horizon": metadata.get("horizon"),
    "confusion_matrix": predictions.get("confusion_matrix"),
    "data": predictions
    }