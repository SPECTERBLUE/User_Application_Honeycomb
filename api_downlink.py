from fastapi import FastAPI, HTTPException, status, Path
from fastapi.responses import JSONResponse
import event_fetcher_parse as efp
import User_token
from pydantic import BaseModel,EmailStr
import json
import os
import logging
import subprocess
import config
import re

# Configure logging
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

app = FastAPI()
CONFIG_FILE = "config-api.json"
JSON_FILE = "edgex_users.json"
SUPERSET_CONTAINER = "superset_app"

class UserRequest(BaseModel):
    username: str

@app.post("/downlink/get-token")
def get_token(request: UserRequest):
    """Return token for a given username from JSON file."""

    if not os.path.exists(JSON_FILE):
        raise HTTPException(status_code=500, detail="Token store not found.")

    try:
        with open(JSON_FILE, "r") as f:
            data = json.load(f)

        for entry in data:
            if entry.get("username") == request.username:
                return {"username": request.username, "token": entry.get("token", "")}

        raise HTTPException(status_code=404, detail="User not found.")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading token store: {e}")
    

@app.get("/downlink/edgex_token_list")
def get_token_list():
    """Return all tokens from JSON file."""
    if not os.path.exists(JSON_FILE):
        raise HTTPException(status_code=500, detail="Token store not found.")

    try:
        with open(JSON_FILE, "r") as f:
            data = json.load(f)
            return JSONResponse(content=data)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading token store: {e}")
    
@app.post("/downlink/edgex_token_list_update")
def update_token_list(data: dict):
    """
    Overwrite the JSON file with new token data.

    This function updates the token list stored in a JSON file. If the file does not exist,
    an HTTPException is raised. The function expects the input data to be in the following format:
    
    {
        "list": [
            {
                "username": "admin",
                "token": ""
            },
            {
                "username": "user9",
                "token": ""
            },
            {
                "username": "user1",
                "token": "1234567"
            }
        ]
    }

    Args:
        data (dict): A dictionary containing the new token list under the key "list".

    Returns:
        dict: A dictionary containing the status and a success message if the operation is successful.

    Raises:
        HTTPException: If the JSON file does not exist or if there is an error writing to the file.
    """
    """overwrite the JSON file with new data."""
    if not os.path.exists(JSON_FILE):
        raise HTTPException(status_code=500, detail="Token store not found.")

    try:
        with open(JSON_FILE, "w") as f:
            formatted_data = data.get("list", [])
            json.dump(formatted_data, f, indent=4)
            return {"status": "success", "message": "Token list updated successfully."}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error writing to token store: {e}")
    
@app.get("/downlink/honeycomb_user_list")
def get_honeycomb_user_list():
   """Returns the list of user after runing update_user_list() function."""
   try:
        # Call the function to update the user list
        User_token.update_user_list()
        
        # Read the updated JSON file
        if os.path.exists(JSON_FILE):
            with open(JSON_FILE, "r") as f:
                data = json.load(f)
                return JSONResponse(content=data)
        else:
            raise HTTPException(status_code=500, detail="Token store not found.")
    
   except Exception as e:
       raise HTTPException(status_code=500, detail=f"Error reading token store: {e}") 
   
@app.post("/downlink/jwt_rotation", status_code=status.HTTP_200_OK)
def jwt_rotation():
    """
    Endpoint to trigger JWT rotation for all users.
    """
    try:
        User_token.Jwt_rotaion_all()
        return {
            "status": "success",
            "message": "JWT rotation completed successfully."
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error during JWT rotation: {str(e)}"
        )

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
    
# Mapping container roles to their Docker names
CONTAINERS = {
    "edgex": config.CONTAINER_EDGEX_SECURITY_PROXY,     # Used for EdgeX user/password management
    "chirpstack": config.CONTAINER_CHIRPSTACK,            # ChirpStack container for CLI operations
    "root": config.CONTAINER_VAULT          # Container that holds the Vault token config
}

# Path to the Vault response JSON file inside the container
ROOT_FILE_PATH = config.VAULT_ROOT_PATH

# === FastAPI Endpoints ===

def run_command(command: str) -> dict:
    """
    Executes a shell command and returns its output.
    If it fails, raises an appropriate HTTP exception.
    """
    try:
        result = subprocess.run(command, shell=True, text=True, capture_output=True)
        if result.returncode != 0:
            logging.error(f"Command Error: {result.stderr}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Docker command failed: {result.stderr}"
            )
        return {"output": result.stdout.strip()}
    except HTTPException as he:
        raise he
    except PermissionError as pe:
        # Handle insufficient system permissions
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(pe)
        )
    except Exception as e:
        # Catch-all for unexpected errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error: " + str(e)
        )


@app.get("/downlink/generate-password/{username}", summary="Generate EdgeX Password", description="Generates a password for EdgeX.")
async def generate_password(username: str):
    """
    Creates a new EdgeX user with a password using Docker exec.
    """
    try:
        logging.info(f"Generating password for: {username}")
        # Command to create a new EdgeX user with temporary JWT token access
        cmd = (
            f"docker exec {CONTAINERS['edgex']} ./secrets-config proxy adduser "
            f"--user \"{username}\" --tokenTTL 365d --jwtTTL 1d --useRootToken"
        )
        output = subprocess.check_output(cmd, shell=True, text=True).strip()
        parsed_output = json.loads(output)

        # Return password from the Docker command output
        return {
            "status": "success",
            "message": "User password generated successfully",
            "password": parsed_output.get("password", "No password found")
        }
    except ValueError as ve:
        # Handle malformed JSON or command output
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


@app.get("/downlink/create-chirpstack-api-key/{name}", summary="Create ChirpStack API Key", description="Creates an API key in ChirpStack.")
async def create_api_key(name: str = Path(..., min_length=1, description="API key name")):
    """
    Uses the ChirpStack CLI inside the container to generate an API key.
    """
    try:
        # Validate API key name format
        if not name.strip() or name == ":name" or not re.match(r'^[a-zA-Z0-9_\-]+$', name):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or missing 'name' parameter"
            )

        logging.info(f"Creating ChirpStack API key for: {name}")

        # ChirpStack CLI command to create a new API key with the given name
        cmd = (
            f"docker exec {CONTAINERS['chirpstack']} "
            f"chirpstack --config /etc/chirpstack "
            f"create-api-key --name '{name}'"
        )
        output = subprocess.check_output(cmd, shell=True, text=True).strip()

        # Extract the token from command output using regex
        match = re.search(r'token: (\S+)', output)
        token = match.group(1) if match else "No API key found"

        return {
            "status": "success",
            "message": "API key created successfully",
            "api_key": token
        }
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


@app.get("/downlink/tokens", summary="Get Root Token", description="Extracts the last root token and returns it as JSON.")
def get_tokens():
    """
    Reads the root token from the Vault response JSON file inside the container.
    """
    try:
        logging.info("Extracting root token...")
        # Command to read the root token file using Docker
        cmd = f"docker exec {CONTAINERS['root']} cat {ROOT_FILE_PATH}"
        output = subprocess.check_output(cmd, shell=True, text=True).strip()

        # Parse the JSON output to extract the root token
        parsed_output = json.loads(output)
        root_token = parsed_output.get("root_token", "No root token found")

        return {
            "status": "success",
            "message": "Root token retrieved successfully",
            "root_token": root_token
        }
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

''' This section is for creating a new user in Apache Superset using Docker exec.
   It uses the Superset CLI to create a user with specified attributes. '''


# Custom exception to represent user conflict (already exists)
class ConflictError(Exception):
    pass

# Request model for user creation
class UserCreate(BaseModel):
    username: str
    first_name: str = "N/A"
    last_name: str = "N/A"
    email: EmailStr
    password: str
    role: str = "Admin"

@app.post("/downlink/create_superset_user", status_code=status.HTTP_200_OK)
async def create_superset_user(user: UserCreate):
    try:
        # 400 Bad Request: Missing required input fields
        if not user.username or not user.email or not user.password:
            raise ValueError("Username, email, and password are required.")

        #  Docker Command Explanation:
        # Executes the superset fab create-user command inside the running Superset container.
        # This uses Docker CLI to run the Superset CLI tool and create a user.
        # The container must be named 'superset_app', and Superset must be installed within it.
        command = [
            "docker", "exec", "superset_app",  # Docker exec on running container 'superset_app'
            "superset", "fab", "create-user",  # Superset CLI user creation
            "--username", user.username,
            "--firstname", user.first_name,
            "--lastname", user.last_name,
            "--email", user.email,
            "--password", user.password,
            "--role", user.role
        ]

        # Run the command and capture both stdout and stderr
        result = subprocess.run(command, capture_output=True, text=True)
        stdout = result.stdout.strip().lower()
        stderr = result.stderr.strip().lower()


        # 404 Not Found: Docker container doesn't exist or command isn't found
        if "no such container" in stderr or "not found" in stderr:
            raise FileNotFoundError("Superset container or command not found.")

        # 409 Conflict: Superset CLI indicates the user already exists
        if "already exists" in stdout or "already exists" in stderr:
            raise ConflictError(f"User with email '{user.email}' already exists.")

        # 500 Internal Server Error: General failure in command execution
        if result.returncode != 0:
            raise RuntimeError(f"Docker command failed.\nSTDOUT: {stdout}\nSTDERR: {stderr}")

        # 200 OK: Success — user created
        return {
            "status": "success",
            "code": 200,
            "message": f"User '{user.username}' created successfully.",
            "stdout": result.stdout.strip()
        }

    # 400: Missing required fields or bad input
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve)
        )

    # 403: Not expected here, but reserved for permission-related issues
    except PermissionError as pe:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(pe)
        )

    # 404: Docker container or command missing
    except FileNotFoundError as fnfe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(fnfe)
        )

    # 409: User already exists
    except ConflictError as ce:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(ce)
        )
        
    # 500: Docker failure or conatiner doent exist
    except RuntimeError as re:
        clean_msg = str(re).replace('\n', ' ')
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error: " + clean_msg
        )
        

class PasswordChangeRequest(BaseModel):
    username: str
    old_password: str
    new_password: str
    confirm_password: str

@app.post("/downlink/change_password", status_code=status.HTTP_200_OK)
async def change_password(body: PasswordChangeRequest):
    if body.new_password != body.confirm_password:
        raise HTTPException(
            status_code=400,
            detail="New password and confirm password do not match."
        )
    if body.old_password == body.new_password:
        raise HTTPException(
            status_code=400,
            detail="New password cannot be the same as the old password."
        )

    # Single-line script string (escape quotes, use \n for new lines)
    superset_password_change = (
    "from superset import create_app\n"
    "from superset.extensions import db, security_manager\n"
    "from werkzeug.security import check_password_hash\n"
    "app = create_app()\n"
    "with app.app_context():\n"
    f" user = security_manager.get_user_by_username('{body.username}')\n"
    f" if not user or not check_password_hash(user.password, '{body.old_password}'):\n"
    "  print('Old password is incorrect')\n"
    " else:\n"
    f"  security_manager.reset_password(user.id, '{body.new_password}')\n"
    "  db.session.commit()\n"
    "  print('Password updated')"
)

    try:
        result = subprocess.run(
            ["docker", "exec", SUPERSET_CONTAINER, "python3", "-c", superset_password_change],
            capture_output=True,
            text=True
        )
    except subprocess.CalledProcessError:
        raise HTTPException(
            status_code=404,
            detail=f"Docker container '{SUPERSET_CONTAINER}' not found or failed to exec command."
        )

    if result.returncode != 0:
        raise HTTPException(
            status_code=500,
            detail="Docker exec error: " + result.stderr.strip().replace('\n', ' ')
        )

    output = result.stdout.strip()

    if "password updated" in output.lower():
        return {
            "status": "success",
            "code": 200,
            "message": f"Password updated for '{body.username}'.",
            "stdout": output
        }

    elif "old password is incorrect" in output.lower():
        raise HTTPException(
            status_code=401,
            detail="Old password is incorrect."
        )

    raise HTTPException(
        status_code=500,
        detail="Unexpected output: " + output
    )
