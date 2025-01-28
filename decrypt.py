
from Crypto.Cipher import AES
from binascii import hexlify, unhexlify


class DecryptionManager:
    """
    Handles AES-CBC decryption using a precomputed shared secret.
    """
    def __init__(self, shared_secret_hex: str):
        """
        Initialize with the shared secret in hex format.

        Args:
            shared_secret_hex (str): The shared secret as a hex string.
        """
        self.shared_secret = bytes.fromhex(shared_secret_hex)[:16]  # AES-128
        self.iv = bytes([0] * 16)  # Fixed IV (used in edge device)
    
    def decrypt(self, encrypted_hex: str) -> bytes:
        """
        Decrypt an encrypted hex string back to raw bytes.

        Args:
            encrypted_hex (str): Encrypted data as a hex string.

        Returns:
            bytes: The decrypted raw data.

        Raises:
            RuntimeError: If decryption fails.
        """
        try:
            # Convert hex string to bytes
            encrypted_data = bytes.fromhex(encrypted_hex)
            
            # Create AES cipher instance
            cipher = AES.new(self.shared_secret, AES.MODE_CBC, iv=self.iv)
            
            # Decrypt the data
            decrypted_data = cipher.decrypt(encrypted_data)
            
            # Return raw bytes
            return decrypted_data
        
        except Exception as e:
            raise RuntimeError(f"Decryption failed: {str(e)}")

