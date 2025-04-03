from fastapi import FastAPI, HTTPException, status
import event_fetcher_parse as efp
import json
import os
import logging

# Configure logging
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

app = FastAPI()
CONFIG_FILE = "config-api.json"

@app.post("/downlink/reset-keyrotation", status_code=status.HTTP_200_OK)
async def resetkeyrotation(data: dict):
    """
    Endpoint to send downlink data for resetting key rotation.
    """
    try:
        if efp.key_manager:
            efp.key_manager.rotate_keys()
            return {
                "status": "success",
                "message": "Key rotation triggered successfully",
                "data": data
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE, 
                detail="KeyRotationManager not initialized"
            )

    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=str(ve)
        )
    except PermissionError as pe:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail=str(pe)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Internal Server Error: " + str(e)
        )
        
def save_update_config(update_frequency, dev_euid):
    """Save update frequency and dev_euid to a JSON file with exception handling."""
    try:
        data = {"update_frequency": update_frequency, "dev_euid": dev_euid}
        with open(CONFIG_FILE, "w") as f:
            json.dump(data, f)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save configuration: {str(e)}"
        )


def get_update_info():
    """Read the update frequency and dev_euid from the JSON file with exception handling."""
    try:
        if not os.path.exists(CONFIG_FILE):
            raise FileNotFoundError("Configuration file not found.")
        
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuration file not found."
        )
    
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Configuration file is corrupted."
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read configuration: {str(e)}"
        )


@app.post("/downlink/update-frequency", status_code=status.HTTP_200_OK)
async def update_frequency(update_frequency: int, dev_euid: str):
    """
    Endpoint to send downlink data for updating frequency.
    """
    try:
        # Validate update_frequency (must be greater than 1 minute)
        if not isinstance(update_frequency, int):
            raise TypeError("Update frequency must be an integer.")
        if update_frequency <= 1:
            raise ValueError("Invalid update frequency value. It must be greater than 1.")
        logger.info(f"update_frequency,{update_frequency}")

        # Check if efp.key_manager exists and has the method
        if hasattr(efp, "key_manager") and hasattr(efp.key_manager, "send_update_frequency"):
            efp.key_manager.send_update_frequency(dev_euid, update_frequency)
        else:
            logger.error("Key manager is not available or method is missing.")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Key manager service is unavailable."
            )

        # Save configuration
        save_update_config(update_frequency, dev_euid)

        return {
            "status": "success",
            "message": "Update frequency set successfully",
            "data_cycle": update_frequency,
            "dev_euid": dev_euid
        }

    except ValueError as ve:
        logger.error(f"Validation error: {ve}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve)
        )

    except TypeError as te:
        logger.error(f"Type error: {te}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid data type. Frequency must be an integer."
        )

    except AttributeError as ae:
        logger.error(f"Attribute error: {ae}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal configuration error. Missing required attributes."
        )

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again later."
        )


@app.get("/downlink/get-config", status_code=status.HTTP_200_OK)
async def get_config():
    """Endpoint to retrieve stored update frequency and dev_euid."""
    return get_update_info()

@app.post("/downlink/device-reboot", status_code=status.HTTP_200_OK)
async def device_reboot(dev_euid: str):
    """
    Endpoint to send downlink data for device reboot.
    """
    try:
        # software reboot
        if efp.key_manager:
            efp.key_manager.send_reboot_command(dev_euid)
            return {
                "status": "success",
                "message": "Device reboot command sent successfully",
                "dev_euid": dev_euid
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="KeyRotationManager not initialized"
            )

    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve)
        )
    except PermissionError as pe:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(pe)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error: " + str(e)
        )
   
@app.post("/downlink/device-status", status_code=status.HTTP_200_OK)
async def device_status(dev_euid: str):
    """
    Endpoint to send downlink data for device status.
    """
    try:
        # current status of the connected device
        if efp.key_manager:
            efp.key_manager.send_device_status(dev_euid)
            return {
                "status": "success",
                "message": "Device status command sent successfully",
                "dev_euid": dev_euid
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="KeyRotationManager not initialized"
            )

    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve)
        )
    except PermissionError as pe:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(pe)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error: " + str(e)
        )
        
@app.post("/downlink/log-level", status_code=status.HTTP_200_OK)
async def log_level(dev_euid: str,level: int):
    """
    Endpoint to set the logging level.
    """
    try:
        # Set the logging level
        if level > 4 :
            raise ValueError("Invalid log level. It must be between 0 and 4.")
        
        if efp.key_manager:
            efp.key_manager.set_log_level(dev_euid, level)
            return {
                "status": "success",
                "message": "Log level set successfully",
                "dev_euid": dev_euid,
                "level": level
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="KeyRotationManager not initialized"
            )
        
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve)
        )
    except PermissionError as pe:   
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(pe)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error: " + str(e)
        )
        
@app.post("/downlink/time-sync", status_code=status.HTTP_200_OK)
async def time_sync(dev_euid: str):
    """
    Endpoint to send downlink data for time synchronization.
    """
    try:
        # Time synchronization
        if efp.key_manager:
            efp.key_manager.send_time_sync(dev_euid)
            return {
                "status": "success",
                "message": "Time sync command sent successfully",
                "dev_euid": dev_euid
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="KeyRotationManager not initialized"
            )

    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve)
        )
    except PermissionError as pe:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(pe)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error: " + str(e)
        )
    
@app.post("/downlink/reset-device", status_code=status.HTTP_200_OK)
async def reset_device(dev_euid: str):
    """
    Endpoint to send downlink data for device reset.(factory reset)
    """
    try:
        # Reset device
        if efp.key_manager:
            efp.key_manager.send_reset_factory(dev_euid)
            return {
                "status": "success",
                "message": "Device reset command sent successfully-factory reset",
                "dev_euid": dev_euid
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="KeyRotationManager not initialized"
            )

    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve)
        )
    except PermissionError as pe:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(pe)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error: " + str(e)
        )