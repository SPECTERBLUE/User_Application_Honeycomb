from fastapi import FastAPI, HTTPException, status, Path, Request, Depends, Body
from fastapi.responses import JSONResponse
import event_fetcher_parse as efp
import User_token
from SMTP_init import LoginAlertMailer
from pydantic import BaseModel, Field, field_validator, EmailStr
from pydantic import FieldValidationInfo
from fastapi.exceptions import RequestValidationError
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from auth import models,schemas,database,auth
from typing import Optional
import pyotp
import qrcode
import base64
from io import BytesIO
import json
import os
import logging
import subprocess
import config
import re
import uuid
from captcha_utils import (
    redis_client,
    generate_captcha_text,
    encrypt_aes_gcm,
    decrypt_aes_gcm,
    decrypt_aes_gcm_downlink_login
)

# Configure logging
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

app = FastAPI(
    #docs_url=None,      # Disables Swagger UI (/docs)
    #redoc_url=None,     # Disables ReDoc (/redoc)
    #openapi_url=None    # Disables OpenAPI schema (/openapi.json)
)
CONFIG_FILE = "config-api.json"
JSON_FILE = "edgex_users.json"
SUPERSET_CONTAINER = "superset_app"

#AUTH_API ------------------------------------------------------------------

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/downlink/register", response_model=schemas.UserResponse)
def register(user: schemas.UserCreate,current_user = Depends(auth.get_current_user) ,db: Session = Depends(get_db)):
    
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    hashed_password = auth.get_password_hash(user.secret)
    new_user = models.User(email=user.email, secret=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

class MFAEnableReq(BaseModel):
    email: EmailStr


@app.post("/downlink/mfa/enable", summary="Enable MFA for a user by email")
def enable_mfa(
    req: MFAEnableReq,
    current_user = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Enables MFA for the given user (provided by email in request).
    """

    # get target user
    db_user = db.query(models.User).filter(models.User.email == req.email).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    # if already enabled
    if db_user.mfa_secret:
        raise HTTPException(status_code=400, detail="MFA already enabled for this user")

    # generate secret + URI
    mfa_secret = pyotp.random_base32()
    totp = pyotp.TOTP(mfa_secret)
    provisioning_uri = totp.provisioning_uri(req.email, issuer_name="Honeycomb DL")

    # QR image
    qr_img = qrcode.make(provisioning_uri)
    buf = BytesIO()
    qr_img.save(buf, format='PNG')
    qr_base64 = base64.b64encode(buf.getvalue()).decode()

    # store secret
    db_user.mfa_secret = mfa_secret
    db.commit()

    return {
        "message": "MFA enabled successfully",
        "email": req.email,
        "mfa_secret": mfa_secret,
        "mfa_uri": provisioning_uri,
        "mfa_qr_base64_png": f"data:image/png;base64,{qr_base64}"
    }

    

@app.post("/downlink/mfa/status", summary="To check mfa status")
def status_mfa(current_user = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    """
    Returns whether MFA is enabled for the currently authenticated user.
    """

    is_enabled = bool(current_user.mfa_secret)

    return {
        "email": current_user.email,
        "mfa_enabled": is_enabled,
        "message": "MFA is enabled" if is_enabled else "MFA is disabled"
    }

class LoginRequest(BaseModel):
    captcha_id: str
    encrypted_input: dict  # { "iv": ..., "ciphertext": ..., "tag": ... }
    identity: dict
    secret: dict
    mfa_code: Optional[str] = None

@app.post("/downlink/login", response_model=schemas.Token)
async def login(
    data: LoginRequest = Body(...),
    db: Session = Depends(get_db)
):
    # 1. Verify captcha
    stored_captcha = await redis_client.get(data.captcha_id)
    try:
        decrypted_input = decrypt_aes_gcm(data.encrypted_input)
    except Exception:
        await redis_client.delete(data.captcha_id)
        return JSONResponse(status_code=400, content={"status":"error","message":"Invalid captcha input."})

    if not stored_captcha or stored_captcha != decrypted_input:
        await redis_client.delete(data.captcha_id)
        return JSONResponse(status_code=400, content={"status":"error","message":"Captcha mismatch or null input."})

    # Delete captcha after successful verification (single-use)
    await redis_client.delete(data.captcha_id)

    # 2. Decrypt username and password
    username = decrypt_aes_gcm_downlink_login(data.identity)
    password = decrypt_aes_gcm_downlink_login(data.secret)
    if not username or not password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid encrypted credentials")

    # 4. Authenticate
    user = auth.authenticate_user(db, username, password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials. Request a new captcha.")
    
    # MFA logic
    if user.mfa_secret:  # MFA enabled
        if not data.mfa_code:
            raise HTTPException(status_code=400, detail="MFA code required")
        totp = pyotp.TOTP(user.mfa_secret)
        if not totp.verify(data.mfa_code):
            raise HTTPException(status_code=401, detail="Invalid MFA code")
    # else → MFA disabled → skip OTP

    # 5. Create access token
    access_token = auth.create_access_token(data={"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/downlink/mfa/reset")
def reset_mfa(current_user = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    
    new_secret = pyotp.random_base32()
    totp = pyotp.TOTP(new_secret)
    provisioning_uri = totp.provisioning_uri(current_user.email, issuer_name="Honeycomb DL")

    qr_img = qrcode.make(provisioning_uri)
    buf = BytesIO()
    qr_img.save(buf, format='PNG')
    qr_base64 = base64.b64encode(buf.getvalue()).decode()

    # update DB
    user = db.query(models.User).filter(models.User.id == current_user.id).first()
    user.mfa_secret = new_secret
    db.commit()
    db.refresh(user)

    return {
        "status": "ok",
        "message": "MFA secret regenerated",
        "mfa_secret": new_secret,
        "mfa_uri": provisioning_uri,
        "mfa_qr_base64_png": f"data:image/png;base64,{qr_base64}"
    }

class MFADisableRequest(BaseModel):
    mfa_code: str

@app.post("/downlink/mfa/disable")
def disable_mfa(body: MFADisableRequest, current_user = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    
    user = db.query(models.User).filter(models.User.id == current_user.id).first()

    if not user.mfa_secret:
        raise HTTPException(status_code=400, detail="MFA not enabled")

    totp = pyotp.TOTP(user.mfa_secret)
    if not totp.verify(body.mfa_code):
        raise HTTPException(status_code=401, detail="Invalid MFA code")

    user.mfa_secret = None
    db.commit()
    db.refresh(user)

    return {"status":"ok","message":"MFA disabled successfully"}

# APIs for login alerts and notifications can be added here
@app.post("/downlink/login-alert", summary="Set login alert email")
def set_login_alert_email(email: EmailStr, current_user = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    """
    Sets the login alert email for the currently authenticated user.
    """
    user = db.query(models.User).filter(models.User.id == current_user.id).first()
    user.login_alert_email = email
    db.commit()
    db.refresh(user)

    return {
        "status": "success",
        "message": f"Login alert email set to {email}"
    }

@app.get("/downlink/login-alert", summary="Get login alert email")
def get_login_alert_email(current_user = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    """
    Retrieves the login alert email for the currently authenticated user.
    """
    user = db.query(models.User).filter(models.User.id == current_user.id).first()
    if not user.login_alert_email:
        return {
            "status": "info",
            "message": "No login alert email set."
        }

    return {
        "status": "success",
        "login_alert_email": user.login_alert_email
    }

@app.post("/downlink/send_login-alert", summary="Send login alert email")
def send_login_alert(current_user = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    """
    Sends a login alert email to the user's configured email address.
    """
    user = db.query(models.User).filter(models.User.id == current_user.id).first()
    if not user.login_alert_email:
        raise HTTPException(status_code=400, detail="No login alert email set.")

    mailer = LoginAlertMailer()
    mailer.send_alert(user.login_alert_email)

    return {
        "status": "success",
        "message": f"Login alert email sent to {user.login_alert_email}"
    }

@app.post("/downlink/disable_login-alert", summary="Disable login alert email")
def disable_login_alert(current_user = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    """
    Disables the login alert email for the currently authenticated user.
    """
    user = db.query(models.User).filter(models.User.id == current_user.id).first()

    if not user.login_alert_email:
        return {
            "status": "info",
            "message": "Login alert email is already disabled."
        }

    user.login_alert_email = None
    db.commit()
    db.refresh(user)

    return {
        "status": "success",
        "message": "Login alert email has been disabled."
    }

@app.get("/downlink/me", response_model=schemas.UserResponse)
def read_users_me(current_user = Depends(auth.get_current_user)):
    return current_user

@app.put("/downlink/secret", response_model=schemas.UserResponse)
def update_secret(update: schemas.SecretUpdate, current_user = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    # Query the user again within the current session
    user = db.query(models.User).filter(models.User.id == current_user.id).first()
    
    if not auth.verify_password(update.old_secret, user.secret):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Old password is incorrect")

    user.secret = auth.get_password_hash(update.new_secret)    
    db.commit()
    db.refresh(user)
    return user
    
@app.put("/downlink/identity", response_model=schemas.UserResponse)
def update_identity(update: schemas.IdentityUpdate, current_user = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    # Query the user again within the current session
    user = db.query(models.User).filter(models.User.id == current_user.id).first()
    
    existing_user = db.query(models.User).filter(models.User.email == update.new_email).first()
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already in use")

    user.email = update.new_email
    db.commit()
    db.refresh(user)
    return user

@app.get("/protected-data")
def protected_data(current_user = Depends(auth.validate_token)):
    return {"message": f"Hello, {current_user.email}! This is protected data."}


class UserRequestToken(BaseModel):
    username_enc: dict

@app.post("/downlink/get-token")
def get_token(request: UserRequestToken, auth: str = Depends(auth.validate_token)):
    """Return token for a given username from JSON file."""
    
    username = decrypt_aes_gcm_downlink_login(request.username_enc)

    if not os.path.exists(JSON_FILE):
        raise HTTPException(status_code=500, detail="Token store not found.")

    try:
        with open(JSON_FILE, "r") as f:
            data = json.load(f)

        for entry in data:
            if entry.get("username") == username:
                return {"token": entry.get("token", "")}

        raise HTTPException(status_code=404, detail="User not found.")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading token store: {e}")
    

@app.get("/downlink/edgex_token_list")
def get_token_list(auth: str = Depends(auth.validate_token)):
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
def update_token_list(data: dict, auth: str = Depends(auth.validate_token)):
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
def get_honeycomb_user_list( auth: str = Depends(auth.validate_token)):
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
def jwt_rotation( auth: str = Depends(auth.validate_token)):
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
async def resetkeyrotation(data: dict, auth: str = Depends(auth.validate_token)):
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
async def update_frequency(update_frequency: int, dev_euid: str, auth: str = Depends(auth.validate_token)):
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
async def device_reboot(dev_euid: str, auth: str = Depends(auth.validate_token)):
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
async def device_status(dev_euid: str, auth: str = Depends(auth.validate_token)):
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
async def log_level(dev_euid: str,level: int, auth: str = Depends(auth.validate_token)):
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
async def time_sync(dev_euid: str, auth: str = Depends(auth.validate_token)):
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
async def reset_device(dev_euid: str, auth: str = Depends(auth.validate_token)):
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

# Regex pattern for validating username
SAFE_USERNAME_PATTERN = re.compile(r"^[a-zA-Z0-9](?:[a-zA-Z0-9_-]*[a-zA-Z0-9])?$")

class UserRequest(BaseModel):
    username: str

def validate_username(username: str):
    if '\x00' in username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Null byte in username is not allowed."
        )
    if not SAFE_USERNAME_PATTERN.fullmatch(username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid username format. Only letters, digits, '-', '_' are allowed."
        )

@app.post(
    "/downlink/generate-password",
    summary="Generate EdgeX Password",
    description="Generates a password for EdgeX.",
    response_description="The generated password for the user"
)
async def generate_password(user_req: UserRequest, auth: str = Depends(auth.validate_token)):
    username = user_req.username
    validate_username(username)

    try:

        # Secure, parameterized Docker command
        cmd = [
            "docker", "exec", CONTAINERS["edgex"],
            "./secrets-config", "proxy", "adduser",
            "--user", username,
            "--tokenTTL", "3650d",
            "--jwtTTL", "1d",
            "--useRootToken"
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        output = result.stdout.strip()

        parsed_output = json.loads(output)

        return {
            "status": "success",
            "message": "User password generated successfully",
            "password": parsed_output.get("password", "No password found")
        }

    except json.JSONDecodeError as je:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to parse Docker output: {output}"
        )
        
    except subprocess.CalledProcessError as cpe:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Docker command failed: {cpe}"
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

@app.post("/downlink/create-chirpstack-api-key/{name}", summary="Create ChirpStack API Key", description="Creates an API key in ChirpStack.")
async def create_api_key(name: str = Path(..., min_length=1, description="API key name"), auth: str = Depends(auth.validate_token)):
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

        # Parameterized Docker command (safe)
        cmd = [
            "docker", "exec",
            CONTAINERS["chirpstack"],
            "chirpstack",
            "--config", "/etc/chirpstack",
            "create-api-key",
            "--name", name
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        output = result.stdout.strip()

        # Extract the token from command output
        match = re.search(r'token: (\S+)', output)
        token = match.group(1) if match else "No API key found"

        return {
            "status": "success",
            "message": "API key created successfully",
            "api_key": token
        }

    except subprocess.CalledProcessError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create API key: {e.stderr.strip()}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error: " + str(e)
        )

@app.get("/downlink/tokens", summary="Get Root Token", description="Extracts the last root token and returns it as JSON.")
def get_tokens( auth: str = Depends(auth.validate_token)):
    """
    Reads the root token from the Vault response JSON file inside the container.
    """
    try:

        # Parameterized docker exec command as list
        cmd = ["docker", "exec", CONTAINERS["root"], "cat", ROOT_FILE_PATH]

        output = subprocess.check_output(cmd, text=True).strip()

        parsed_output = json.loads(output)
        root_token = parsed_output.get("root_token")
        if not root_token:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Root token not found in the JSON file."
            )

        return {
            "status": "success",
            "message": "Root token retrieved successfully",
            "root_token": root_token
        }

    except json.JSONDecodeError as je:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to parse JSON from Vault response."
        )
    except subprocess.CalledProcessError as cpe:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Docker command failed: {cpe}"
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

class ConflictError(Exception):
    pass


class UserCreate(BaseModel):
    username: str = Field(..., example="string")
    first_name: str = Field("", example="string")
    last_name: str = Field("", example="string")
    email: str = Field(..., example="string")   
    password: str = Field(..., example="string")
    role: str = Field(..., example="Admin")

    @field_validator('email')
    @classmethod
    def validate_email(cls, v: str) -> str:
        email_regex = re.compile(
            r'^[a-zA-Z0-9]+([._-][a-zA-Z0-9]+)*@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        )
        if not email_regex.match(v):
            raise ValueError("Invalid email format")
        return v

    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str, info: FieldValidationInfo) -> str:
        values = info.data
        email = values.get('email', '').lower()
        password = v.lower()

        # Identity restriction for @gmail.com
        if email.endswith('@gmail.com'):
            local_part = email.split('@')[0]

            if any(sep in local_part for sep in ['.', '-', '_']):
                parts = re.split(r'[._-]', local_part)
                for part in parts:
                    if part and part in password:
                        raise ValueError(
                            f"Password must not contain parts of your email address: '{part}'"
                        )
            else:
                if local_part in password:
                    raise ValueError(
                        f"Password must not contain the email local part: '{local_part}'"
                    )

        # Password strength checks
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')

        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')

        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')

        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one digit')

        if not re.search(r'\W', v):
            raise ValueError('Password must contain at least one special character')

        return v


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError, auth: str = Depends(auth.validate_token)):
    errors = exc.errors()
    error_messages = []

    for error in errors:
        loc = " -> ".join(str(i) for i in error['loc'] if i != 'body')
        msg = error['msg']
        error_messages.append(f"{loc}: {msg}")

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "status": "error",
            "code": 400,
            "detail": "Validation Failed",
            "errors": error_messages
        }
    )


@app.post("/downlink/create_superset_user", status_code=status.HTTP_200_OK)
async def create_superset_user(user: UserCreate, auth: str = Depends(auth.validate_token)):
    try:
        if not user.username or not user.email or not user.password:
            raise ValueError("Username, email, and password are required.")

        docker_command = [
            "docker", "exec", SUPERSET_CONTAINER,
            "superset", "fab", "create-user",
            "--username", user.username,
            "--firstname", user.first_name,
            "--lastname", user.last_name,
            "--email", user.email,
            "--password", user.password,
            "--role", user.role
        ]

        result = subprocess.run(docker_command, capture_output=True, text=True)
        stdout = result.stdout.strip().lower()
        stderr = result.stderr.strip().lower()

        if "no such container" in stderr or "not found" in stderr:
            raise FileNotFoundError("Superset container or command not found.")

        if "already exists" in stdout or "already exists" in stderr:
            raise ConflictError(f"User with email '{user.email}' already exists.")

        if result.returncode != 0:
            raise RuntimeError(
                f"Docker command failed.\nSTDOUT: {stdout}\nSTDERR: {stderr}"
            )

        return {
            "status": "success",
            "code": 200,
            "message": f"User '{user.username}' created successfully.",
            "stdout": result.stdout.strip()
        }

    except PermissionError as pe:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(pe)
        )

    except FileNotFoundError as fnfe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(fnfe)
        )

    except ConflictError as ce:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(ce)
        )

    except RuntimeError as re_err:
        clean_msg = str(re_err).replace('\n', ' ')
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error: " + clean_msg
        )


class PasswordChangeRequest(BaseModel):
    email: EmailStr
    old_password: str 
    new_password: str 
    confirm_password: str


@app.post("/downlink/change_password", status_code=status.HTTP_200_OK)
async def change_password(body: PasswordChangeRequest, auth: str = Depends(auth.validate_token)):
    # 1. Password pattern: At least 8 chars, one uppercase, one lowercase, one digit, one special char
    password_pattern = re.compile(
        r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)"
        r"(?=.*[!@#$%^&*()_\-+=\[{\]};:'\",<.>/?\\|`~]).{8,}$"
    )
    if not password_pattern.match(body.new_password):
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 8 characters long, "
                   "contain at least one uppercase letter, one lowercase letter, "
                   "one digit, and one special character."
        )

    # 2. Confirm new_password and confirm_password match
    if body.new_password != body.confirm_password:
        raise HTTPException(
            status_code=400,
            detail="New password and confirm password do not match."
        )

    # 3. Prevent reusing the old password
    if body.old_password == body.new_password:
        raise HTTPException(
            status_code=400,
            detail="New password cannot be the same as the old password."
        )

    # 4. Gmail-specific logic: Reject if new password contains local part or any split parts
    email = body.email.lower()
    new_password_lower = body.new_password.lower()

    if email.endswith("@gmail.com"):
        local_part = email.split("@")[0]

        # Full local part not allowed in password
        if local_part in new_password_lower:
            raise HTTPException(
                status_code=400,
                detail="Password cannot contain your emal username."
            )

        # If contains '.', '_', or '-', check individual parts
        if any(sep in local_part for sep in ['.', '_', '-']):
            parts = re.split(r"[._-]", local_part)
            for part in parts:
                if part and part in new_password_lower:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Password cannot contain parts of your email address: '{part}'"
                    )

    # 5. Docker command to change Superset user password
    superset_password_change_script = """
from superset import create_app
from superset.extensions import db, security_manager
from werkzeug.security import check_password_hash
import sys

email = sys.argv[1]
old_password = sys.argv[2]
new_password = sys.argv[3]

app = create_app()
with app.app_context():
    user = security_manager.find_user(email=email)
    if not user or not check_password_hash(user.password, old_password):
        print('Old password is incorrect')
        sys.exit(1)
    security_manager.reset_password(user.id, new_password)
    db.session.commit()
    print('Password updated')
"""

    try:
        result = subprocess.run(
            [
                "docker", "exec", SUPERSET_CONTAINER,
                "python3", "-c", superset_password_change_script,
                body.email, body.old_password, body.new_password
            ],
            capture_output=True,
            text=True,
            check=False,
        )
    except subprocess.CalledProcessError:
        raise HTTPException(
            status_code=404,
            detail=f"Docker container '{SUPERSET_CONTAINER}' not found or failed to exec command."
        )

    if result.returncode != 0:
        if "old password is incorrect" in result.stdout.lower():
            raise HTTPException(status_code=401, detail="Old password is incorrect.")
        raise HTTPException(
            status_code=500,
            detail="Docker exec error: " + (result.stderr.strip() or result.stdout.strip())
        )

    output = result.stdout.strip()

    if "password updated" in output.lower():
        return {
            "status": "success",
            "code": 200,
            "message": f"Password updated for '{body.email}'.",
            "stdout": output
        }

    raise HTTPException(
        status_code=500,
        detail="Unexpected output: " + output
    )
class CaptchaVerifyRequest(BaseModel):
    captcha_id: str
    encrypted_input: dict  # { "iv": ..., "ciphertext": ..., "tag": ... }
    
@app.post("/downlink/captcha")

async def generate_captcha():
    try:
        captcha_text = generate_captcha_text()
        captcha_id = str(uuid.uuid4())

        # Save captcha in Redis (expires in 5 minutes)
        await redis_client.setex(captcha_id, 300, captcha_text)
        logger.info(f"Generated CAPTCHA: id={captcha_id}")
        # Encrypt captcha
        encrypted = encrypt_aes_gcm(captcha_text)

        return JSONResponse(
            status_code=200,
            content={
                "status": "ok",
                "message": "Captcha generated successfully",
                "captcha_id": captcha_id,
                "encrypted_captcha": encrypted
            }
        )

    except ValueError as ve:
        logger.warning(f"ValueError during CAPTCHA generation: {ve}")
        return JSONResponse(
            status_code=400,
            content={"status": "error", "detail": str(ve)}
        )

    except PermissionError as pe:
        logger.warning(f"PermissionError during CAPTCHA generation: {pe}")
        return JSONResponse(
            status_code=403,
            content={"status": "error", "detail": str(pe)}
        )

    except Exception as e:
        logger.error(f"Unexpected error during CAPTCHA generation: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"status": "error", "detail": "Internal Server Error: " + str(e)}
        )

# ---------------------------
# Verify Captcha Endpoint
# ---------------------------
@app.post("/downlink/captcha/verify")
async def verify_captcha(request: CaptchaVerifyRequest, auth: str = Depends(auth.validate_token)):
    try:
        stored_captcha = await redis_client.get(request.captcha_id)
        if not stored_captcha:
            logger.info(f"Captcha expired or invalid: id={request.captcha_id}")
            raise ValueError("Captcha expired or invalid")

        decrypted_input = decrypt_aes_gcm(request.encrypted_input)

        if not decrypted_input or stored_captcha != decrypted_input:
    # Generate new captcha if mismatch or null input
            new_captcha = generate_captcha_text()
            await redis_client.setex(request.captcha_id, 300, new_captcha)
            encrypted_new = encrypt_aes_gcm(new_captcha)
            logger.info(f"Captcha mismatch or null input for id={request.captcha_id}. New captcha generated.")

            return JSONResponse(
            status_code=400,  
            content={
                "status": "error",
                "message": "Captcha mismatch or null input. New captcha generated.",
                "captcha_id": request.captcha_id,
                "encrypted_captcha": encrypted_new
            }
        )

        # Success: delete captcha from Redis
        await redis_client.delete(request.captcha_id)
        logger.info(f"Captcha verified successfully: id={request.captcha_id}")
        return {"status": "ok", "message": "Captcha verified successfully"}

    except ValueError as ve:
        logger.warning(f"Captcha verification failed: {ve}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve)
        )
    except PermissionError as pe:
        logger.warning(f"Permission error during captcha verification: {pe}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(pe)
        )
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Unexpected error during captcha verification: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error: " + str(e)
        )
