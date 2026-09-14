from typing import Final

USER_MAX_USERNAME_LENGTH: Final[int] = 32
USER_MAX_EMAIL_LENGTH: Final[int] = 64
USER_MAX_DESCRIPTION_LENGTH: Final[int] = 400

CLUB_MAX_NAME_LENGTH: Final[int] = 128
CLUB_MAX_DESCRIPTION_LENGTH: Final[int] = 400
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
AUTH_GLOBAL_MAX_PER_MINUTE: Final[int] = 600

# Per-account failed-login throttle. Failures are counted per *submitted*
# username (existent or not) over a trailing window, reset by a successful
# login. At ``LOGIN_LOCKOUT_THRESHOLD`` the account is rejected with 429 and a
# ``Retry-After`` that doubles with each further failure, capped at one hour.
LOGIN_FAILURE_WINDOW_MINUTES: Final[int] = 60
LOGIN_LOCKOUT_THRESHOLD: Final[int] = 10
LOGIN_BACKOFF_BASE_SECONDS: Final[int] = 30
LOGIN_BACKOFF_MAX_SECONDS: Final[int] = 3600

# ``login_attempts`` rows are audit-only after the failure window elapses;
# they are pruned this many days after creation.
LOGIN_ATTEMPT_RETENTION_DAYS: Final[int] = 90
