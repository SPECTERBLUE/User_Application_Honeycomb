import logging
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
from Crypto.Cipher import AES
from binascii import hexlify
from typing import Tuple

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Set to DEBUG for detailed logs
    format="%(asctime)s - %(levelname)s - %(message)s"
)

class KeyManager:
    """Manages ECDH key pair generation and retrieval."""
    
    def __init__(self):
        """Initialize KeyManager and generate a new key pair."""
        self.private_key = None
        self.public_key = None
        self.generate_key()
    
    def generate_key(self):
        """Generate a new ECDH key pair and store the private and public keys."""
        logging.debug("Starting key generation process...")
        
        try:
            private_key_obj = ec.generate_private_key(ec.SECP256R1())
            private_num = private_key_obj.private_numbers().private_value
            self.private_key = private_num.to_bytes(32, byteorder='big').hex()

            public_key_bytes = private_key_obj.public_key().public_bytes(
                encoding=serialization.Encoding.X962,
                format=serialization.PublicFormat.UncompressedPoint
            )
            self.public_key = public_key_bytes.hex()

            logging.info("Successfully generated a new ECDH key pair.")
            logging.debug(f"Generated Private Key: {self.private_key}")
            logging.debug(f"Generated Public Key : {self.public_key}")

        except Exception as e:
            logging.error(f"Error generating key pair: {e}", exc_info=True)

    def get_private_key(self):
        """Return the private key."""
        if self.private_key:
            logging.debug("Retrieving private key.")
            return self.private_key
        logging.warning("Private key is not available.")
        return None

    def get_public_key(self):
        """Return the public key."""
        if self.public_key:
            logging.debug("Retrieving public key.")
            return self.public_key
        logging.warning("Public key is not available.")
        return None

class SharedKey:
    """Handles the derivation of a shared secret using ECDH."""
    
    def __init__(self, private_key_hex: str, external_public_key_hex: str):
        """
        Derives a shared secret using ECDH.
        
        :param private_key_hex: Hexadecimal private key from this device.
        :param external_public_key_hex: Hexadecimal public key received from an external device.
        """
        logging.debug("Initializing SharedKey derivation...")
        
        try:
            # Convert hex keys to bytes
            private_key_bytes = bytes.fromhex(private_key_hex)
            public_key_bytes = bytes.fromhex(external_public_key_hex)

            # Validate public key length (must be 65 bytes for uncompressed format)
            if len(public_key_bytes) != 65:
                raise ValueError(f"Invalid public key length: {len(public_key_bytes)} bytes. Expected 65 bytes.")

            # Create private key object from bytes
            private_key_obj = ec.derive_private_key(
                int.from_bytes(private_key_bytes, byteorder='big'),
                ec.SECP256R1()
            )

            # Create public key object from received public key
            public_key_obj = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), public_key_bytes)

            # Compute shared secret using ECDH
            shared_secret = private_key_obj.exchange(ec.ECDH(), public_key_obj)
            self.shared_secret_hex = hexlify(shared_secret).decode()

            logging.info("Successfully derived shared secret.")
            logging.debug(f"Derived Shared Secret (hex): {self.shared_secret_hex}")

        except ValueError as ve:
            logging.error(f"ValueError during shared secret derivation: {ve}")
            self.shared_secret_hex = None
        except Exception as e:
            logging.error(f"Unexpected error in shared secret derivation: {e}", exc_info=True)
            self.shared_secret_hex = None

    def get_shared_secret(self):
        """Return the derived shared secret."""
        if self.shared_secret_hex:
            logging.debug("Retrieving shared secret.")
            return self.shared_secret_hex
        logging.warning("Shared secret is not available.")
        return None

class SensorCrypto:
    """Handles encryption and decryption of data using AES (CBC mode)."""
    
    def __init__(self, shared_secret_hex: str):
        """
        Initialize encryption with a derived shared secret.

        :param shared_secret_hex: Hexadecimal shared secret derived from ECDH key exchange.
        """
        try:
            logging.debug("Initializing SensorCrypto with shared secret.")
            self.shared_secret = bytes.fromhex(shared_secret_hex)[:16]  # Use only the first 16 bytes
            self.iv = bytes([0] * 16)  # Initialization Vector (IV) set to zero

            logging.info("SensorCrypto successfully initialized.")
        except Exception as e:
            logging.error(f"Error initializing SensorCrypto: {e}", exc_info=True)
            self.shared_secret = None

    def encrypt(self, plaintext: bytes) -> Tuple[bytes, str]:
        """
        Encrypts data using AES-CBC.

        :param plaintext: Data to be encrypted (bytes).
        :return: Tuple containing raw encrypted bytes and hex representation.
        """
        try:
            logging.debug("Encrypting data...")
            
            # Padding (PKCS7-style with NULL bytes)
            pad_len = 16 - (len(plaintext) % 16)
            plaintext_padded = plaintext + (b'\0' * pad_len)

            cipher = AES.new(self.shared_secret, AES.MODE_CBC, iv=self.iv)
            encrypted_bytes = cipher.encrypt(plaintext_padded)

            encrypted_hex = encrypted_bytes.hex()
            logging.info("Data encrypted successfully.")
            logging.debug(f"Encrypted Data (hex): {encrypted_hex}")

            return encrypted_bytes, encrypted_hex

        except Exception as e:
            logging.error(f"Error encrypting data: {e}", exc_info=True)
            return None, None

    def decrypt(self, encrypted_hex: str) -> bytes:
        """
        Decrypts encrypted data using AES-CBC.

        :param encrypted_hex: Hexadecimal string of encrypted data.
        :return: Decrypted data as bytes.
        """
        try:
            logging.debug("Decrypting data...")
            encrypted_bytes = bytes.fromhex(encrypted_hex)

            cipher = AES.new(self.shared_secret, AES.MODE_CBC, iv=self.iv)
            decrypted_bytes = cipher.decrypt(encrypted_bytes)

            logging.info("Data decrypted successfully.")

            return decrypted_bytes.rstrip(b'\0')  # Remove padding before returning

        except Exception as e:
            logging.error(f"Error decrypting data: {e}", exc_info=True)
            return None
