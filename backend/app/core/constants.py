from typing import Final

USER_MAX_USERNAME_LENGTH: Final[int] = 32
USER_MAX_EMAIL_LENGTH: Final[int] = 64
# Argon2 hashes whatever it is handed, so an unbounded password field is a
# free way to make the server spend CPU on request. 128 is far past
# anything a person types and well inside what a password manager makes.
USER_MAX_PASSWORD_LENGTH: Final[int] = 128
USER_MAX_DESCRIPTION_LENGTH: Final[int] = 400

ALTCHA_MAX_PAYLOAD_LENGTH: Final[int] = 4096

CLUB_MAX_NAME_LENGTH: Final[int] = 128
CLUB_MAX_DESCRIPTION_LENGTH: Final[int] = 4000
CLUB_MAX_SUMMARY_LENGTH: Final[int] = 50

TAG_MAX_NAME_LENGTH: Final[int] = 50

ACTIVITY_MAX_NAME_LENGTH: Final[int] = 64
ACTIVITY_MAX_DESCRIPTION_LENGTH: Final[int] = 400
ACTIVITY_MAX_LOCATION_LENGTH: Final[int] = 200

ACADEMIC_TERM_MAX_LENGTH: Final[int] = 50

GENERAL_ACTIVITY_MAX_NAME_LENGTH: Final[int] = 128

JOINT_ACTIVITY_MAX_NAME_LENGTH: Final[int] = 128
JOINT_ACTIVITY_MAX_LOCATION_LENGTH: Final[int] = 200
JOINT_ACTIVITY_MIN_FINAL_SCORE: Final[int] = 6
JOINT_ACTIVITY_MAX_FINAL_SCORE: Final[int] = 8

CLUB_ACTIVITY_CHECK_IN_MAX_ROSTER_SIZE: Final[int] = 500

# ── Authentication anti-abuse ────────────────────────────────────────────
#
# Per-IP request budgets, enforced in-process by ``app.core.rate_limit``.
# Deliberately generous: a whole campus can share one NAT egress IP, so a
# tight budget locks out legitimate users long before it inconveniences an
# attacker. The per-account throttle below is what actually stops credential
# stuffing; these numbers only blunt bulk scanning from a single source.

LOGIN_IP_MAX_PER_MINUTE: Final[int] = 60
LOGIN_IP_MAX_PER_HOUR: Final[int] = 1200
REGISTER_IP_MAX_PER_HOUR: Final[int] = 15
REGISTER_IP_MAX_PER_DAY: Final[int] = 150

# ALTCHA challenge issuance. The endpoint is unauthenticated by design, so a
# per-IP budget is what keeps a single source from minting challenges in
# bulk. It must stay above the login budget: every login or registration
# attempt consumes a fresh challenge, including retries after a failure.
CHALLENGE_IP_MAX_PER_MINUTE: Final[int] = 120
CHALLENGE_IP_MAX_PER_HOUR: Final[int] = 2400

# Process-wide circuit breaker over all auth traffic. It is the only budget a
# flood from many source IPs cannot dodge, but because it is shared it also
# sheds load for everyone once tripped — so it sits well above any plausible
# legitimate peak and exists to bound resource exhaustion, not normal usage.
AUTH_GLOBAL_MAX_PER_MINUTE: Final[int] = 3000

# Per-account failed-login throttle. Failures are counted per *submitted*
# username (existent or not) over a trailing window, reset by a successful
# login. At ``LOGIN_LOCKOUT_THRESHOLD`` the account is rejected with 429 and a
# ``Retry-After`` reporting when enough of the oldest failures will have aged
# out of the window to lift the lockout (never more than the window itself).
LOGIN_FAILURE_WINDOW_MINUTES: Final[int] = 60
LOGIN_LOCKOUT_THRESHOLD: Final[int] = 10

# ``login_attempts`` rows are audit-only after the failure window elapses;
# they are pruned this many days after creation.
LOGIN_ATTEMPT_RETENTION_DAYS: Final[int] = 90

# ── Sessions ─────────────────────────────────────────────────────────────
#
# Login issues an opaque token backed by a ``user_sessions`` row rather than a
# self-contained JWT, so signing out (and, later, a password change) takes
# effect on the next request instead of whenever a signed token would have
# expired on its own.
SESSION_LIFETIME_DAYS: Final[int] = 7
SESSION_COOKIE_NAME: Final[str] = "bnd_session"

# ── Contact verification (email address / phone number) ──────────────────
#
# One six-digit code, two channels. Six digits is the most a person will
# retype from an SMS without error; the security comes from the short TTL and
# the attempt cap below, not from the code's length.
VERIFICATION_CODE_DIGITS: Final[int] = 6
VERIFICATION_CODE_MAX_ATTEMPTS: Final[int] = 5
# Longest string accepted in the "phone" field before normalization, so a
# caller cannot push megabytes through the validator. Fits "+86 138 0013 8000"
# and any punctuation a person might type.
USER_MAX_PHONE_INPUT_LENGTH: Final[int] = 24

# Email is cheap and its delivery is slow and unreliable, so the code lives
# long enough to survive a greylisting delay.
EMAIL_CODE_TTL_MINUTES: Final[int] = 15
# SMS arrives in seconds, and every message costs money, so the window is
# tight: a short TTL is what makes a stolen-handset-glance attack expensive
# and keeps the number of live codes low.
SMS_CODE_TTL_MINUTES: Final[int] = 5

# Minimum gap between two sends on the same channel for the same account.
# Stops a held-down "resend" button from becoming a bill.
VERIFICATION_RESEND_INTERVAL_SECONDS: Final[int] = 60

# Send budgets. These are DB-backed rather than handled by
# ``app.core.rate_limit``: that limiter is per-process, so with more than one
# worker each would enforce its own copy of the budget and the real cap would
# silently multiply. For SMS that difference is money.
EMAIL_SEND_MAX_PER_ACCOUNT_PER_HOUR: Final[int] = 5
EMAIL_SEND_MAX_PER_TARGET_PER_DAY: Final[int] = 10
SMS_SEND_MAX_PER_ACCOUNT_PER_HOUR: Final[int] = 3
SMS_SEND_MAX_PER_TARGET_PER_DAY: Final[int] = 5

# Deployment-wide daily SMS ceiling: the last line of defence for the bill if
# every other budget is somehow walked around (many accounts, many numbers).
# Once hit, phone verification stops working for everyone until the window
# rolls — deliberately, because an unbounded spend is the worse failure.
SMS_GLOBAL_MAX_PER_DAY: Final[int] = 500

# Codes are kept after use so the send budgets above can still see them; this
# is how long before the retention sweep removes them.
VERIFICATION_CODE_RETENTION_DAYS: Final[int] = 7
