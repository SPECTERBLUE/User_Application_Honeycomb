import logging
import csv

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class TrainingDatasetCSVCreator:
    def __init__(self):
        pass

    def create_csv(self, telemetry_data, output_file):
        try:
            
            if not telemetry_data:
                logging.error("No telemetry data provided to create CSV.")
                return False

            keys = telemetry_data[0].keys()
            with open(output_file, 'w', newline='') as output_csv:
                dict_writer = csv.DictWriter(output_csv, fieldnames=keys)
                dict_writer.writeheader()
                dict_writer.writerows(telemetry_data)

            logging.info(f"CSV file created successfully at {output_file}.")
            return True
        except Exception as e:
            logging.error(f"Failed to create CSV file: {e}")
            return False