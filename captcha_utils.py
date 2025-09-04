import random
import string
import redis.asyncio as redis
from pydantic import BaseModel
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import os
import base64
import config


# Redis connection

redis_client = redis.Redis(
    host="localhost",
    port=6379,
    decode_responses=True
)

async def init_redis():
    """Call this during startup to verify Redis connection."""
    try:
        pong = await redis_client.ping()
        print("Redis connected:", pong)
    except Exception as e:
        print("Redis connection failed:", e)

async def close_redis():
    """Call this during shutdown."""
    await redis_client.close()

# Symmetric key setup (AES-256)

# Fixed 32-byte key (frontend must know this key)
AES_KEY = config.AES_KEY  # Must be 32 bytes for AES-256
aesgcm = AESGCM(AES_KEY)

# Request/Response Models

class CaptchaVerifyRequest(BaseModel):
    captcha_id: str
    encrypted_input: dict  # { "iv": ..., "ciphertext": ..., "tag": ... }

# Generate Captcha Text (6 chars)

def generate_captcha_text():
    digits = random.choices(string.digits, k=2)
    lower = random.choice(string.ascii_lowercase)
    upper = random.choice(string.ascii_uppercase)
    extra = random.choices(string.ascii_letters + string.digits, k=2)
    captcha_chars = digits + [lower, upper] + extra
    random.shuffle(captcha_chars)
    return "".join(captcha_chars)

# Encrypt / Decrypt using AES-GCM

def encrypt_aes_gcm(plaintext: str):
    iv = os.urandom(12)  # unique per captcha
    ciphertext = aesgcm.encrypt(iv, plaintext.encode(), None)
    return {
        "iv": base64.b64encode(iv).decode(),
        "ciphertext": base64.b64encode(ciphertext[:-16]).decode(),  # last 16 bytes = tag
        "tag": base64.b64encode(ciphertext[-16:]).decode()
    }

def decrypt_aes_gcm(encrypted: dict):
    iv = base64.b64decode(encrypted["iv"])
    ciphertext = base64.b64decode(encrypted["ciphertext"])
    tag = base64.b64decode(encrypted["tag"])
    combined = ciphertext + tag
    return aesgcm.decrypt(iv, combined, None).decode()
