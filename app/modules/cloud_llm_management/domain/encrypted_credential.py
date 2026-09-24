# domain/encrypted_credential.py

from dataclasses import dataclass


@dataclass(frozen=True)
class EncryptedCredential:
    ciphertext: bytes
    nonce: bytes
    key_version: int
    api_key_hint: str