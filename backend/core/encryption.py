"""
PHI/PII encryption using Fernet (symmetric encryption).
HIPAA compliance requirement: encrypt data at rest.
"""

from cryptography.fernet import Fernet
from typing import Optional
import os
import logging

logger = logging.getLogger(__name__)


class PHIEncryption:
    """
    Handles encryption/decryption of Protected Health Information.
    Uses Fernet (symmetric encryption) with AES-128 in CBC mode.
    """
    
    def __init__(self, encryption_key: Optional[str] = None):
        """
        Initialize encryption with key from environment.
        
        Args:
            encryption_key: Base64-encoded Fernet key. If None, reads from ENCRYPTION_KEY env var.
        
        Raises:
            ValueError: If encryption key is missing or invalid.
        """
        key = encryption_key or os.getenv("ENCRYPTION_KEY")
        
        if not key:
            raise ValueError(
                "ENCRYPTION_KEY environment variable not set. "
                "Generate with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
            )
        
        try:
            self.cipher = Fernet(key.encode() if isinstance(key, str) else key)
        except Exception as e:
            raise ValueError(f"Invalid encryption key: {e}")
    
    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt plaintext string.
        
        Args:
            plaintext: Text to encrypt
        
        Returns:
            Base64-encoded encrypted string
        """
        if not plaintext:
            return ""
        
        try:
            encrypted = self.cipher.encrypt(plaintext.encode())
            return encrypted.decode()
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise
    
    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt ciphertext string.
        
        Args:
            ciphertext: Encrypted text
        
        Returns:
            Decrypted plaintext
        
        Raises:
            cryptography.fernet.InvalidToken: If decryption fails
        """
        if not ciphertext:
            return ""
        
        try:
            decrypted = self.cipher.decrypt(ciphertext.encode())
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise
    
    def encrypt_dict(self, data: dict, fields: list) -> dict:
        """
        Encrypt specific fields in a dictionary.
        
        Args:
            data: Dictionary with data
            fields: List of field names to encrypt
        
        Returns:
            Dictionary with encrypted fields
        """
        encrypted_data = data.copy()
        
        for field in fields:
            if field in encrypted_data and encrypted_data[field]:
                encrypted_data[field] = self.encrypt(str(encrypted_data[field]))
        
        return encrypted_data
    
    def decrypt_dict(self, data: dict, fields: list) -> dict:
        """
        Decrypt specific fields in a dictionary.
        
        Args:
            data: Dictionary with encrypted data
            fields: List of field names to decrypt
        
        Returns:
            Dictionary with decrypted fields
        """
        decrypted_data = data.copy()
        
        for field in fields:
            if field in decrypted_data and decrypted_data[field]:
                decrypted_data[field] = self.decrypt(decrypted_data[field])
        
        return decrypted_data


# Global encryption instance
try:
    phi_encryption = PHIEncryption()
except ValueError as e:
    logger.warning(f"PHI encryption not initialized: {e}")
    phi_encryption = None


def encrypt_field(value: str) -> str:
    """Convenience function to encrypt a single field"""
    if phi_encryption is None:
        raise RuntimeError("PHI encryption not initialized")
    return phi_encryption.encrypt(value)


def decrypt_field(value: str) -> str:
    """Convenience function to decrypt a single field"""
    if phi_encryption is None:
        raise RuntimeError("PHI encryption not initialized")
    return phi_encryption.decrypt(value)
