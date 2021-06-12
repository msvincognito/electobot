
class VoteExceptionNegative(Exception):
    """Raised when a vote is cast with negative votes."""

class VoteExceptionTooFew(Exception):
    """Raised when not all available votes for a user are cast."""

class VoteExceptionWrongId(Exception):
    """Raised when not all `poll_option_id`s refer to the same poll."""
