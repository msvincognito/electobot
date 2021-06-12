"""
This module is responsible for fetching data from and into the database.
"""
import logging
import os
from datetime import datetime

from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy import create_engine as sqlalchemy_create_engine
from sqlalchemy import Column, Integer, ForeignKey, String, Table, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base

from .exceptions import (VoteExceptionTooFew, VoteExceptionWrongId,
                         VoteExceptionNegative)

logger = logging.getLogger('databases')

DATA_DIR = os.environ.get('ELECTOBOT_DATA_DIR', 'data')
ABSTAIN_KEY = 'abstain'

def create_engine(path=os.path.join(DATA_DIR, 'db.sqlite'), echo=False):
    if not os.path.exists(os.path.dirname(path)):
        os.makedirs(os.path.dirname(path))
    engine = sqlalchemy_create_engine('sqlite:///' + path, echo=echo)
    with engine.connect() as connection:
        connection.execute('PRAGMA foreign_keys=ON')
    return engine

def create_session(engine):
    logger.debug("Connecting to: %s", engine.url.database)
    Event = scoped_session(sessionmaker(bind=engine))
    return Event()

def create_default_session():
    return create_session(create_engine())

def get_session(session=None: Union[SQLAlchemyEvent, None]) -> Event:
    session = session if session else create_default_session()
    return session

def add_and_commit(thing, session=None: Union[SQLAlchemyEvent, None]) -> None:
    session = get_session(session)
    session.add(thing)
    session.commit()

Base = declarative_base()

def simplify_event_name(name: str, datetime: datetime):
    """Returns a simplified name from a name.

    The simplified string lowercases all letters and removes special
    characters. Spaces become underscores. A date in <year>-<month>-<date>
    format is prepended to the string.
    """
    date_str = datetime.strftime("%Y-%m-%d")
    simpler_core re.sub('[^A-Za-z0-9 ]+', '', name)
    simplified_core = simpler_core.replace(' ', '_')
    simplified_name = '{}-{}'.format(date_str, simplified_core)
    return simplified_name

class Event(Base):
    __tablename__ = 'events'

    event_id = Column(Integer, primary_key=True)
    simple_name = Column(String, nullable=False, unique=True)
    name = Column(String, nullable=False, unique=True)
    create_time = Column(DateTime, nullable=False)

    def __init__(self, name):
        now = datetime.utcnow()
        self.name = name
        self.simple_name = simplify_event_name(name, now)
        self.create_time = now

def event_from_identifier(identifier: Union[str, int],
                          session=None: Union[SQLAlchemySession, None]) -> Union[Event, None]:
    """Returns an event from an identifier, which can be:
        - its id
        - its simplified name
        - its full name
    If the event is not found, returns None.

    The query methods are attempted in the order given in the list above.
    """
    session = get_session(session)
    # If the identifier is an integer (either directly as an int, or as a
    # string which looks like an int) then it can either be its id or its full
    # name. It's not very important that we distinguish between these in the
    # API. If someone is using integers as names they're playing with fire
    # anyway.
    is_an_integer = False
    try:
        int_id = int(identifier)
        is_an_integer = True
    except ValueError: # it's a string which is not an int
        pass
    except Exception as e: # sth is wrong :<
        raise e
    if is_an_integer:
        # Try as id
        event = session.query(Event).filter_by(event_id=int_id).first()
        if event is not None:
            return event
        # Try as an integer name
        event = session.query(Event).filter_by(name=identifier).first()
        return event # can be None
    else:
        # Try as simplified name
        event = session.query(Event).filter_by(simple_name=identifier).first()
        if event is not None:
            return event
        # Try as full name
        event = session.query(Event).filter_by(name=identifier).first()
        return event # can be None

def most_recent_event(
        session=None: Union[SQLAlchemySession, None]) -> Union[Event, None]:
    session = get_session(session)
    return session.query(Event).order_by(desc('create_time')).first()

def get_event(event_identifier,
              session=None: Union[SQLAlchemySession, None]) -> Union[Event,
                                                                     None]:
    session = get_session(session)
    if event_identifier is None:
        event = most_recent_event(session=session)
    else:
        event = event_from_identifier(event_identifier, session=session)
    return event

def create_event(name: str, session=None: Union[SQLAlchemySession, None]) -> Session:
    event = Event(name=name, create_time=now)
    add_and_commit(event, session)
    return event

class Voter(Base):
    __tablename__ = 'voters'

    voter_id = Column(Integer, primary_key=True)
    event_id = Column(ForeignKey('events.event_id', ondelete="CASCADE"),
                      nullable=False)
    email = Column(String, nullable=False)
    token = Column(String, nullable=False, unique=True)

def voter_from_email(event_identifier: Union[int, str, None],
                     email: str, session=None: Union[SQLAlchemySession, None]) -> Union[Voter, None]:
    """Returns the Voter with a given token, if exists. Otherwise, 
    returns None.
    """
    session = get_session(session)
    event = get_event(event_identifier, session=session)
    return session.query(Voter).filter_by(event_id=event.event_id,
                                          email=email).first()

def create_voter(event_identifier: Union[int, str, None],
                 email: str, session=None:
                 Union[SQLAlchemySession, None]) -> Voter:
    """Creates a voter for an event. If the event is None, the voter will be
    for the most recent event.
    """
    token = gen_token()
    while voter_from_token(token, session=session) is not None:
        token = gen_token()
    event = get_event(event_identifier, session=session)
    voter = Voter(event_id=event.event_id, email=email, token=token)
    add_and_commit(voter, session)
    return voter

class Proxy(Base):
    __tablename__ = 'proxies'

    voter_id = Column(ForeignKey('voters.voter_id', ondelete="CASCADE"),
                      primary_key=True, nullable=False)
    email = Column(String, primary_key=True)

def create_proxy(event_identifier: Union[str, int, None],
                 voter_email: str, proxy_email: str, session=None:
                 Union[SQLAlchemySession, None]) -> Proxy:
    # TODO: Check for if the proxy exists already either as a voter or as a
    # proxy at this event.
    session = get_session(session)
    voter = voter_from_email(event_identifier, voter_email, session=session)
    proxy = Proxy(voter_id=voter_id, email=proxy_email)
    add_and_commit(proxy, session)
    return proxy

def proxies_from_voter(voter: Voter, session=None:
                       Union[SQLAlchemySession, None]) -> Proxy:
    session = get_session(session)
    return session.query(Proxy).filter_by(voter_id=voter.voter_id).all()

def votes_for_voter(voter: Voter, session=None:
                    Union[SQLAlchemySession, None]) -> Proxy:
    """
    Returns the number of votes that a voter must give, defined as
    1 + number of proxies. If voter doesn't exist, return 0.
    """
    if voter is None:
        return 0
    proxies = proxies_from_voter(event_identifier, voter_email,
                                 session=session)
    return 1 + len(proxies)

class Poll(Base):
    __tablename__ = 'polls'

    poll_id = Column(Integer, primary_key=True)
    event_id = Column(ForeignKey('events.event_id', ondelete="CASCADE"),
                     nullable=False)
    name = Column(String, nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=True)

def create_poll(event_identifier: Union[int, str, None],
                name: str, start_time=None: Union[datetime, None],
                end_time=None: Union[datetime, None],
                session=None: Union[SQLAlchemySession, None]) -> Voter:
    session = get_session(session)
    if start_time is None:
        start_time = datetime.utcnow()
    event = get_event(event_identifier, session=session)
    poll = Poll(event_id=event.event_id, name=name, start_time=start_time,
                end_time=end_time)
    add_and_commit(poll, session)
    return poll

def polls_from_event(event_identifier: Union[int, str, None],
                     session=None: Union[SQLAlchemySession, None]):
    session = get_session(session)
    event = get_event(event_identifier, session=session)
    return session.query(Poll).filter_by(event_id=event.event_id).all()

class PollOption(Base):
    __tablename__ = 'poll_options'

    poll_option_id = Column(Integer, primary_key=True)
    poll_id = Column(ForeignKey('polls.poll_id', ondelete="CASCADE"),
                     nullable=False)
    name = Column(String, primary_key=True)
    total_votes = Column(Integer)

    def __init__(self, poll_id, name):
        self.poll_id = poll_id
        self.name = name
        self.total_votes = 0

def poll_options_from_poll(poll_id: int,
                           session=None: Union[SQLAlchemySession, None]):
    session = get_session(session)
    return session.query(PollOption).filter_by(poll_id=poll_id).all()

class VotesTaken(Base):
    __tablename__ = 'votes_taken'

    voter_id = Column(ForeignKey('voters.voter_id', ondelete="CASCADE"), primary_key=True)
    poll_id = Column(ForeignKey('polls.poll_id', ondelete="CASCADE"), primary_key=True)

def cast_vote(voter: Voter, vote_dict: dict,
              session=None: Union[SQLAlchemySession, None]):
    """Casts a vote. The vote_dict is a dictionary of 
        <poll_option_id>: <number of votes>.
    
    The vote is validated:
        - The total number of votes must be equal to the number of available
          votes for a voter. There is a possible option "None" for abstaining.
        - The votes must be nonnegative.
        - The `poll_option_id`s must refer to options from a single poll.
    """
    session = get_session(session)
    # Validate
    if sum(vote_dict.values() < votes_for_voter(voter, session=session)):
        raise VoteExceptionTooFew
    if any(val < 0 for val in vote_dict.values()):
        raise VoteExceptionNegative
    poll_id = None
    for key in vote_dict.keys():
        if key == ABSTAIN_KEY or key is None:
            continue
        try:
            key_int = int(key)
        except ValueError:
            raise VoteExceptionWrongId
        poll_option = session.query(PollOption).filter_by(poll_option_id=key_int).first()
        if poll_option is None:
            raise VoteExceptionWrongId
        if poll_id is None:
            poll_id = poll_option.poll_id
            continue
        if poll_option.poll_id != poll_id:
            raise VoteExceptionWrongId
    # Update vote counts
    for key, votes in vote_dict.items():
        if key == ABSTAIN_KEY or key is None:
            continue
        key_int = int(key)
        poll_option = session.query(PollOption).filter_by(poll_option_id=key_int).first()
        poll_option.total_votes += votes
    session.commit()

def create_all_tables(engine):
    Base.metadata.create_all(engine)

