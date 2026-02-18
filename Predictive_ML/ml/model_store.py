import pickle
import json
from typing import Optional, Tuple, Dict, Any, List
from captcha_utils import redis_client  

MODEL_KEY = "ml:model:{name}"
META_KEY = "ml:model:meta:{name}"
MODEL_LIST_KEY = "ml:model:list"


# ---------------- STORE MODEL ---------------- #

async def store_model(
    model_name: str,
    model: Any,
    metadata: Dict[str, Any]
):
    """
    Stores trained ML model + metadata in Redis
    """

    model_blob = pickle.dumps(model)

    # store binary model
    await redis_client.set(
        MODEL_KEY.format(name=model_name),
        model_blob
    )

    # store metadata as JSON
    await redis_client.set(
        META_KEY.format(name=model_name),
        json.dumps(metadata)
    )

    # add to model registry
    await redis_client.sadd(MODEL_LIST_KEY, model_name)


# ---------------- LOAD MODEL ---------------- #

async def load_model(
    model_name: str
) -> Tuple[Optional[Any], Optional[Dict[str, Any]]]:

    model_blob = await redis_client.get(
        MODEL_KEY.format(name=model_name)
    )

    if not model_blob:
        return None, None

    metadata_raw = await redis_client.get(
        META_KEY.format(name=model_name)
    )

    model = pickle.loads(model_blob)
    metadata = json.loads(metadata_raw) if metadata_raw else {}

    return model, metadata


# ---------------- DELETE MODEL ---------------- #

async def delete_model(model_name: str):

    await redis_client.delete(
        MODEL_KEY.format(name=model_name)
    )

    await redis_client.delete(
        META_KEY.format(name=model_name)
    )

    await redis_client.srem(MODEL_LIST_KEY, model_name)


# ---------------- LIST MODELS ---------------- #

async def list_models() -> List[str]:
    models = await redis_client.smembers(MODEL_LIST_KEY)
    return list(models)
