
class VoteExceptionNegative(Exception):
    """Raised when a vote is cast with negative votes."""

class VoteExceptionTooFew(Exception):
    """Raised when not all available votes for a user are cast."""

class VoteExceptionTooMany(Exception):
    """Raised when too many votes cast."""

class VoteExceptionWrongId(Exception):
    """Raised when not all `poll_option_id`s refer to the same poll."""

class VoteExceptionWrongTime(Exception):
    """Raised when attempting to vote on a vote which is closed."""

class VoteExceptionWrongEvent(Exception):
    """Raised when a voter tries to vote on a poll in an event he is not signed
    up for."""

class VoteExceptionAlreadyVoted(Exception):
    """Raised when a voter tries to vote again."""

class DBExceptionEmailAlreadyUsed(Exception):
    """Email already used."""
