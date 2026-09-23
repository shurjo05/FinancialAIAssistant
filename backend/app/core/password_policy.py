"""Password strength rules, enforced when a password is created or changed.

Classic composition rules: a minimum length plus one each of uppercase,
lowercase, digit, and symbol. The 64-char cap exists because bcrypt ignores
everything past 72 bytes, so two long passwords sharing a prefix would collide.

The frontend mirrors these rules as a live checklist; this is the authority.
"""

MIN_LENGTH = 8
MAX_LENGTH = 64

# (check, human-readable requirement) — order matches the signup checklist.
_RULES = (
    (lambda p: len(p) >= MIN_LENGTH, f"at least {MIN_LENGTH} characters"),
    (lambda p: any(c.isupper() for c in p), "an uppercase letter"),
    (lambda p: any(c.islower() for c in p), "a lowercase letter"),
    (lambda p: any(c.isdigit() for c in p), "a number"),
    (lambda p: any(not c.isalnum() and not c.isspace() for c in p), "a symbol"),
)


def password_problems(password: str) -> list[str]:
    """Every requirement `password` fails (empty list = acceptable)."""
    if len(password) > MAX_LENGTH:
        return [f"at most {MAX_LENGTH} characters"]
    return [msg for check, msg in _RULES if not check(password)]


def password_error(password: str) -> str | None:
    """One user-facing sentence describing what's missing, or None if valid."""
    problems = password_problems(password)
    if not problems:
        return None
    return "Password needs " + ", ".join(problems) + "."
