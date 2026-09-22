"""Registration email rules — disposable-domain blocklist.

A cheap, offline defense against mass signups: reject known throwaway-inbox
domains. Bundled as a static list (`disposable_domains.txt`), loaded once at
import. Not exhaustive or bulletproof — it raises the floor, it isn't a wall.
Always on (no external dependency, no key needed).
"""

from pathlib import Path

_BLOCKLIST_PATH = Path(__file__).parent / "disposable_domains.txt"


def _load_domains() -> frozenset[str]:
    domains: set[str] = set()
    for line in _BLOCKLIST_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip().lower()
        if line and not line.startswith("#"):
            domains.add(line)
    return frozenset(domains)


_DISPOSABLE_DOMAINS = _load_domains()


def is_disposable(email: str) -> bool:
    """True if the email's domain is a known disposable/throwaway provider."""
    _, _, domain = email.rpartition("@")
    return domain.strip().lower() in _DISPOSABLE_DOMAINS
