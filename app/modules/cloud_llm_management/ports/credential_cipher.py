from typing import Protocol

from ..domain.encrypted_credential import (
    EncryptedCredential,
)


class CredentialCipher(Protocol):
    def encrypt(
        self,
        plaintext: str,
    ) -> EncryptedCredential:
        ...

    def decrypt(
        self,
        credential: EncryptedCredential,
    ) -> str:
        ...