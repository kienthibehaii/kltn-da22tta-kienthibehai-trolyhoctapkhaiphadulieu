# security/encryption.py - Data Encryption Utilities
"""
Encryption System

Features:
- AES-256 encryption for data at rest
- Fernet symmetric encryption
- Secure key management
- Conversation history encryption
- Database field encryption
"""

import os
import base64
from typing import Optional, Union
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
from cryptography.hazmat.backends import default_backend
from dotenv import load_dotenv
import json

load_dotenv()


class EncryptionManager:
    """
    Encryption manager for data security.
    """
    
    def __init__(self, encryption_key: Optional[str] = None):
        """
        Initialize encryption manager.
        
        Args:
            encryption_key: Base64-encoded encryption key (None = use env var)
        """
        # Get encryption key from env or parameter
        key_str = encryption_key or os.getenv('ENCRYPTION_KEY')
        
        if not key_str:
            # Generate new key if not provided
            key_str = self._generate_key()
            print(f"⚠️  Generated new encryption key. Save this to .env:")
            print(f"ENCRYPTION_KEY={key_str}")
        
        # Initialize Fernet cipher
        try:
            self.key = key_str.encode() if isinstance(key_str, str) else key_str
            self.cipher = Fernet(self.key)
            print("✅ Encryption Manager initialized")
        except Exception as e:
            raise ValueError(f"Invalid encryption key: {e}")
    
    @staticmethod
    def _generate_key() -> str:
        """Generate a new Fernet key"""
        key = Fernet.generate_key()
        return key.decode()
    
    @staticmethod
    def generate_key_from_password(password: str, salt: Optional[bytes] = None) -> bytes:
        """
        Generate encryption key from password using PBKDF2.
        
        Args:
            password: Password string
            salt: Salt bytes (None = generate new)
        
        Returns:
            Encryption key bytes
        """
        if salt is None:
            salt = os.urandom(16)
        
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key
    
    def encrypt(self, data: Union[str, bytes, dict]) -> str:
        """
        Encrypt data.
        
        Args:
            data: Data to encrypt (str, bytes, or dict)
        
        Returns:
            Base64-encoded encrypted data
        """
        # Convert to bytes
        if isinstance(data, dict):
            data_bytes = json.dumps(data).encode()
        elif isinstance(data, str):
            data_bytes = data.encode()
        else:
            data_bytes = data
        
        # Encrypt
        encrypted = self.cipher.encrypt(data_bytes)
        
        # Return as base64 string
        return base64.urlsafe_b64encode(encrypted).decode()
    
    def decrypt(self, encrypted_data: str, return_type: str = 'str') -> Union[str, bytes, dict]:
        """
        Decrypt data.
        
        Args:
            encrypted_data: Base64-encoded encrypted data
            return_type: 'str', 'bytes', or 'dict'
        
        Returns:
            Decrypted data in specified type
        """
        try:
            # Decode from base64
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode())
            
            # Decrypt
            decrypted_bytes = self.cipher.decrypt(encrypted_bytes)
            
            # Convert to requested type
            if return_type == 'bytes':
                return decrypted_bytes
            elif return_type == 'dict':
                return json.loads(decrypted_bytes.decode())
            else:  # str
                return decrypted_bytes.decode()
        
        except Exception as e:
            raise ValueError(f"Decryption failed: {e}")
    
    def encrypt_conversation(self, conversation: list) -> str:
        """
        Encrypt conversation history.
        
        Args:
            conversation: List of message dicts
        
        Returns:
            Encrypted conversation string
        """
        return self.encrypt(conversation)
    
    def decrypt_conversation(self, encrypted_conversation: str) -> list:
        """
        Decrypt conversation history.
        
        Args:
            encrypted_conversation: Encrypted conversation string
        
        Returns:
            List of message dicts
        """
        return self.decrypt(encrypted_conversation, return_type='dict')
    
    def encrypt_field(self, value: str) -> str:
        """
        Encrypt a single field value.
        
        Useful for encrypting specific database fields.
        """
        return self.encrypt(value)
    
    def decrypt_field(self, encrypted_value: str) -> str:
        """
        Decrypt a single field value.
        """
        return self.decrypt(encrypted_value, return_type='str')
    
    def encrypt_dict(self, data: dict, fields_to_encrypt: list) -> dict:
        """
        Encrypt specific fields in a dictionary.
        
        Args:
            data: Dictionary with data
            fields_to_encrypt: List of field names to encrypt
        
        Returns:
            Dictionary with encrypted fields
        """
        encrypted_data = data.copy()
        
        for field in fields_to_encrypt:
            if field in encrypted_data:
                encrypted_data[field] = self.encrypt_field(str(encrypted_data[field]))
                encrypted_data[f'{field}_encrypted'] = True
        
        return encrypted_data
    
    def decrypt_dict(self, data: dict, fields_to_decrypt: list) -> dict:
        """
        Decrypt specific fields in a dictionary.
        
        Args:
            data: Dictionary with encrypted data
            fields_to_decrypt: List of field names to decrypt
        
        Returns:
            Dictionary with decrypted fields
        """
        decrypted_data = data.copy()
        
        for field in fields_to_decrypt:
            if field in decrypted_data and decrypted_data.get(f'{field}_encrypted'):
                decrypted_data[field] = self.decrypt_field(decrypted_data[field])
                decrypted_data.pop(f'{field}_encrypted', None)
        
        return decrypted_data
    
    def hash_data(self, data: str) -> str:
        """
        Create a hash of data (one-way, for verification).
        
        Args:
            data: Data to hash
        
        Returns:
            Hex-encoded hash
        """
        import hashlib
        return hashlib.sha256(data.encode()).hexdigest()
    
    def verify_hash(self, data: str, hash_value: str) -> bool:
        """
        Verify data against hash.
        
        Args:
            data: Original data
            hash_value: Hash to verify against
        
        Returns:
            True if hash matches
        """
        return self.hash_data(data) == hash_value


class SecureStorage:
    """
    Secure storage wrapper for encrypted data.
    """
    
    def __init__(self, encryption_manager: EncryptionManager):
        """Initialize secure storage"""
        self.encryption = encryption_manager
    
    def save_encrypted(self, data: dict, filepath: str):
        """
        Save encrypted data to file.
        
        Args:
            data: Data to save
            filepath: File path
        """
        encrypted = self.encryption.encrypt(data)
        
        with open(filepath, 'w') as f:
            f.write(encrypted)
    
    def load_encrypted(self, filepath: str) -> dict:
        """
        Load encrypted data from file.
        
        Args:
            filepath: File path
        
        Returns:
            Decrypted data
        """
        with open(filepath, 'r') as f:
            encrypted = f.read()
        
        return self.encryption.decrypt(encrypted, return_type='dict')
    
    def encrypt_mongodb_document(self, document: dict, sensitive_fields: list) -> dict:
        """
        Encrypt sensitive fields in MongoDB document.
        
        Args:
            document: MongoDB document
            sensitive_fields: List of field names to encrypt
        
        Returns:
            Document with encrypted fields
        """
        return self.encryption.encrypt_dict(document, sensitive_fields)
    
    def decrypt_mongodb_document(self, document: dict, sensitive_fields: list) -> dict:
        """
        Decrypt sensitive fields in MongoDB document.
        
        Args:
            document: MongoDB document with encrypted fields
            sensitive_fields: List of field names to decrypt
        
        Returns:
            Document with decrypted fields
        """
        return self.encryption.decrypt_dict(document, sensitive_fields)


# Test code
if __name__ == "__main__":
    print("="*60)
    print("TESTING ENCRYPTION MANAGER")
    print("="*60)
    
    # Create encryption manager
    encryption = EncryptionManager()
    
    # Test string encryption
    print("\n# Test String Encryption")
    original = "This is sensitive data"
    encrypted = encryption.encrypt(original)
    decrypted = encryption.decrypt(encrypted)
    
    print(f"Original: {original}")
    print(f"Encrypted: {encrypted[:50]}...")
    print(f"Decrypted: {decrypted}")
    print(f"Match: {original == decrypted}")
    
    # Test dict encryption
    print("\n# Test Dict Encryption")
    data = {
        'username': 'testuser',
        'email': 'test@example.com',
        'api_key': 'secret_key_12345'
    }
    
    encrypted_data = encryption.encrypt_dict(data, ['api_key'])
    print(f"Original: {data}")
    print(f"Encrypted: {encrypted_data}")
    
    decrypted_data = encryption.decrypt_dict(encrypted_data, ['api_key'])
    print(f"Decrypted: {decrypted_data}")
    
    # Test conversation encryption
    print("\n# Test Conversation Encryption")
    conversation = [
        {'role': 'user', 'content': 'What is data mining?'},
        {'role': 'assistant', 'content': 'Data mining is...'}
    ]
    
    encrypted_conv = encryption.encrypt_conversation(conversation)
    decrypted_conv = encryption.decrypt_conversation(encrypted_conv)
    
    print(f"Original: {conversation}")
    print(f"Encrypted: {encrypted_conv[:50]}...")
    print(f"Decrypted: {decrypted_conv}")
    print(f"Match: {conversation == decrypted_conv}")
    
    # Test hashing
    print("\n# Test Hashing")
    data = "sensitive_data"
    hash_value = encryption.hash_data(data)
    is_valid = encryption.verify_hash(data, hash_value)
    
    print(f"Data: {data}")
    print(f"Hash: {hash_value}")
    print(f"Verification: {is_valid}")
