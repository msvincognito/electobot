from typing import Union

from .database import Voter, get_session

def gen_token() -> str:
    """Returns a random token."""
    return str(uuid.uuid4())

def voter_from_token(token: str, session=None: Union[SQLAlchemySession, None]) -> Union[Voter, None]:
    """Returns the Voter with a given token, if exists. Otherwise, 
    returns None.
    """
    session = get_session(session)
    return session.query(Voter).filter_by(token=token).first()
