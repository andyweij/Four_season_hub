import os

from cryptography.hazmat.primitives.ciphers.aead import (
    AESGCM,
)

from ...domain.encrypted_credential import (
    EncryptedCredential,
)



class AesGcmCredentialCipher:
    def __init__(
        self,
        keys: dict[int, bytes],
        current_version: int,
    ):
        if current_version not in keys:
            raise ValueError(
                "Current encryption key version is missing"
            )

        self._keys = keys
        self._current_version = current_version

    def encrypt(
        self,
        plaintext: str,
    ) -> EncryptedCredential:
        if not plaintext:
            raise ValueError("Credential cannot be empty")

        nonce = os.urandom(12)
        key = self._keys[self._current_version]

        ciphertext = AESGCM(key).encrypt(
            nonce=nonce,
            data=plaintext.encode("utf-8"),
            associated_data=None,
        )

        return EncryptedCredential(
            ciphertext=ciphertext,
            nonce=nonce,
            key_version=self._current_version,
            api_key_hint=self._build_hint(plaintext),
        )

    def decrypt(
        self,
        credential: EncryptedCredential,
    ) -> str:
        key = self._keys.get(
            credential.key_version,
        )

        if key is None:
            raise ValueError(
                "Unknown encryption key version"
            )

        plaintext = AESGCM(key).decrypt(
            nonce=credential.nonce,
            data=credential.ciphertext,
            associated_data=None,
        )

        return plaintext.decode("utf-8")

    @staticmethod
    def _build_hint(
        plaintext: str,
    ) -> str:
        visible = plaintext[-4:]
        return f"••••{visible}"