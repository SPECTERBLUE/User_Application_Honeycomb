import csv
import os
from datetime import datetime, timezone
import logging

BASE_DATASET_DIR = "data/training_datasets"

def create_training_dataset_csv(
    processed_data: list,
    asset_id: str,
    window_length: int
):
    """
    Stores processed telemetry into a CSV file for ML training.
    Returns the file path.
    """

    if not processed_data:
        raise ValueError("Processed data is empty")

    os.makedirs(BASE_DATASET_DIR, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"{asset_id}_window_{window_length}_{timestamp}.csv"
    file_path = os.path.join(BASE_DATASET_DIR, filename)

    try:
        with open(file_path, mode="w", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=processed_data[0].keys()
            )
            writer.writeheader()
            writer.writerows(processed_data)

        logging.info(f"Training dataset created: {file_path}")
        return file_path

    except Exception as e:
        logging.error(f"Failed to write CSV: {e}")
        raise
