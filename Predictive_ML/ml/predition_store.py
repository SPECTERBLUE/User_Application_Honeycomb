import logging
from captcha_utils import redis_client
import json

logging.basicConfig(level=logging.INFO)

async def store_prediction(prediction_data):
    '''
    store all the predction data with the other metadata in a redis store
    for later retrieval for the dashboard and api
    '''
    await redis_client.set(f"prediction:{prediction_data['asset_id']}:{prediction_data['model_name']}:{prediction_data['horizon']}", json.dumps(prediction_data))