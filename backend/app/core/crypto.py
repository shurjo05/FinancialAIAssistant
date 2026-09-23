"""Symmetric encryption for secrets at rest (Fernet).

Used to encrypt Plaid access tokens before they touch the database — the DB only
ever holds ciphertext, decrypted just-in-time to call Plaid. Fernet is
authenticated (tamper-evident) symmetric encryption; the key comes from
`PLAID_ENCRYPTION_KEY`.

If no key is configured we fall back to an ephemeral per-process key so local dev
and tests work with zero setup — but that key dies on restart, so PRODUCTION MUST
set `PLAID_ENCRYPTION_KEY` or previously-stored tokens become undecryptable.
"""

from functools import lru_cache

from cryptography.fernet import Fernet

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("app.crypto")


@lru_cache(maxsize=1)
def _fernet() -> Fernet:
    key = settings.plaid_encryption_key
    if key:
        return Fernet(key.encode())
    logger.warning(
        "PLAID_ENCRYPTION_KEY is not set; using an ephemeral key (dev/test only). "
        "Set it in production or stored tokens can't be decrypted after a restart."
    )
    return Fernet(Fernet.generate_key())


def encrypt(plaintext: str) -> str:
    """Encrypt a secret for storage. Returns a URL-safe ciphertext string."""
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    """Decrypt a value produced by `encrypt`."""
    return _fernet().decrypt(ciphertext.encode()).decode()
