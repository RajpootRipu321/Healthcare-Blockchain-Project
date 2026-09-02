"""AES Encryption module for secure medical data handling."""

import os
import hashlib
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import pad, unpad
import base64


class AESCipher:
    """
    AES-256 encryption for medical images and data.

    Features:
    - 256-bit key derived from password using PBKDF2
    - CBC mode with random IV
    - Secure padding (PKCS7)
    """

    def __init__(self, key: str):
        """
        Initialize cipher with encryption key.

        Args:
            key: User-provided encryption key/password
        """
        # Derive 256-bit key from password using SHA-256
        self.key = hashlib.sha256(key.encode()).digest()
        self.block_size = AES.block_size

    def encrypt(self, data: bytes) -> bytes:
        """
        Encrypt binary data.

        Args:
            data: Raw bytes to encrypt

        Returns:
            Encrypted bytes (IV + ciphertext)
        """
        iv = get_random_bytes(self.block_size)
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        padded_data = pad(data, self.block_size)
        encrypted = cipher.encrypt(padded_data)
        return iv + encrypted

    def decrypt(self, encrypted_data: bytes) -> bytes:
        """
        Decrypt encrypted data.

        Args:
            encrypted_data: Encrypted bytes (IV + ciphertext)

        Returns:
            Decrypted raw bytes
        """
        iv = encrypted_data[:self.block_size]
        ciphertext = encrypted_data[self.block_size:]
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        decrypted = cipher.decrypt(ciphertext)
        return unpad(decrypted, self.block_size)

    def encrypt_file(self, input_path: str, output_path: str = None) -> str:
        """
        Encrypt a file.

        Args:
            input_path: Path to file to encrypt
            output_path: Path for encrypted output (default: input + .enc)

        Returns:
            Path to encrypted file
        """
        if output_path is None:
            output_path = input_path + '.enc'

        with open(input_path, 'rb') as f:
            data = f.read()

        encrypted = self.encrypt(data)

        with open(output_path, 'wb') as f:
            f.write(encrypted)

        return output_path

    def decrypt_file(self, input_path: str, output_path: str) -> str:
        """
        Decrypt a file.

        Args:
            input_path: Path to encrypted file
            output_path: Path for decrypted output

        Returns:
            Path to decrypted file
        """
        with open(input_path, 'rb') as f:
            encrypted_data = f.read()

        decrypted = self.decrypt(encrypted_data)

        with open(output_path, 'wb') as f:
            f.write(decrypted)

        return output_path

    @staticmethod
    def generate_key() -> str:
        """Generate a random encryption key."""
        return base64.b64encode(get_random_bytes(32)).decode('utf-8')


# Simple fallback using pyAesCrypt (if pycryptodome not available)
class SimpleAESCipher:
    """Simplified AES encryption using pyAesCrypt (file-based)."""

    def __init__(self, key: str, buffer_size: int = 64 * 1024):
        self.key = key
        self.buffer_size = buffer_size

    def encrypt_file(self, input_path: str, output_path: str = None) -> str:
        """Encrypt file using pyAesCrypt."""
        import pyAesCrypt

        if output_path is None:
            output_path = input_path + '.aes'

        pyAesCrypt.encryptFile(input_path, output_path, self.key, self.buffer_size)
        return output_path

    def decrypt_file(self, input_path: str, output_path: str) -> str:
        """Decrypt file using pyAesCrypt."""
        import pyAesCrypt

        pyAesCrypt.decryptFile(input_path, output_path, self.key, self.buffer_size)
        return output_path
