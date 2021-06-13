"""
This module is responsible for fetching data from and into the database.
"""
import logging
import os
from datetime import datetime
from typing import Union
import re
from copy import copy

from sqlalchemy.orm.session import Session as SQLAlchemySession
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy import create_engine as sqlalchemy_create_engine
from sqlalchemy import (Column, Integer, ForeignKey, String, Table, Float,
                        DateTime, Boolean)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql.expression import desc
from tabulate import tabulate

from .exceptions import (VoteExceptionTooFew, VoteExceptionTooMany,
                         VoteExceptionWrongId, VoteExceptionNegative,
                         VoteExceptionWrongTime, VoteExceptionWrongEvent,
                         VoteExceptionAlreadyVoted, DBExceptionEmailAlreadyUsed)
from .token import gen_token

logger = logging.getLogger('databases')

DATA_DIR = os.environ.get('ELECTOBOT_DATA_DIR', 'data')
ABSTAIN_KEY = 'abstain'

def create_engine(path=os.path.join(DATA_DIR, 'db.sqlite'), echo=False):
    if path != ":memory:" and not os.path.exists(os.path.dirname(path)):
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

def get_session(session: Union[SQLAlchemySession, None]=None) -> SQLAlchemySession:
    session = session if session else create_default_session()
    return session

def add_and_commit(thing, session: Union[SQLAlchemySession, None]=None) -> None:
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
    simpler_core = re.sub('[^A-Za-z0-9 ]+', '', name).lower()
    simpler_core = re.sub('[ ]+', ' ', simpler_core)
    simplified_core = simpler_core.replace(' ', '_')
    simplified_name = '{}-{}'.format(date_str, simplified_core)
    return simplified_name

class Event(Base):
    __tablename__ = 'events'

    event_id = Column(Integer, primary_key=True)
    simple_name = Column(String, nullable=False, unique=True)
    name = Column(String, nullable=False, unique=True)
    create_time = Column(DateTime, nullable=False)
    token = Column(String, nullable=False, unique=True)
    email_pattern = Column(String, nullable=False)

    def __init__(self, name, token, email_pattern):
        now = datetime.utcnow()
        self.name = name
        self.simple_name = simplify_event_name(name, now)
        self.create_time = now
        self.token = token
        self.email_pattern = email_pattern

def event_from_identifier(identifier: Union[str, int],
                          session: Union[SQLAlchemySession, None]=None) -> Union[Event, None]:
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

def event_from_token(token: str, session: Union[SQLAlchemySession, None]=None) -> Union[Event, None]:
    """Returns the Event with a given token, if exists. Otherwise, 
    returns None.
    """
    session = get_session(session)
    return session.query(Event).filter_by(token=token).first()

def most_recent_event(
        session: Union[SQLAlchemySession, None]=None) -> Union[Event, None]:
    session = get_session(session)
    return session.query(Event).order_by(desc('create_time')).first()

def get_event(event_identifier,
              session: Union[SQLAlchemySession, None]=None) -> Union[Event,
                                                                     None]:
    session = get_session(session)
    if event_identifier is None:
        event = most_recent_event(session=session)
    else:
        event = event_from_identifier(event_identifier, session=session)
    return event

def create_event(name: str, email_pattern: str , session: Union[SQLAlchemySession, None]=None) -> Event:
    session = get_session(session)
    token = gen_token()
    while event_from_token(token, session=session) is not None:
        token = gen_token()
    event = Event(name=name, token=token, email_pattern=email_pattern)
    add_and_commit(event, session)
    return event

def delete_event(id: int, session: Union[SQLAlchemySession, None]=None) -> Boolean:
    session = get_session(session)
    token = gen_token()
    while event_from_token(token, session=session) is not None:
        token = gen_token()
    
    event=session.query(Event).filter(Event.event_id==id).first()
    if event is not None:
        session.delete(event)
        session.commit()
        return True
    return False

class Voter(Base):
    __tablename__ = 'voters'

    voter_id = Column(Integer, primary_key=True)
    event_id = Column(ForeignKey('events.event_id', ondelete="CASCADE"),
                      nullable=False)
    email = Column(String, nullable=False)
    token = Column(String, nullable=False, unique=True)

def voter_from_email(event_identifier: Union[int, str, None],
                     email: str, session: Union[SQLAlchemySession, None]=None) -> Union[Voter, None]:
    """Returns the Voter with a given token, if exists. Otherwise, 
    returns None.
    """
    session = get_session(session)
    event = get_event(event_identifier, session=session)
    return session.query(Voter).filter_by(event_id=event.event_id,
                                          email=email).first()

def create_voter(event_identifier: Union[int, str, None],
                 email: str,
                 session: Union[SQLAlchemySession, None]=None) -> Voter:
    """Creates a voter for an event. If the event is None, the voter will be
    for the most recent event.
    """
    if voter_from_email(event_identifier, email, session=session):
        raise DBExceptionEmailAlreadyUsed
    token = gen_token()
    while voter_from_token(token, session=session) is not None:
        token = gen_token()
    event = get_event(event_identifier, session=session)
    voter = Voter(event_id=event.event_id, email=email, token=token)
    add_and_commit(voter, session)
    return voter

def voter_from_token(token: str, session: Union[SQLAlchemySession, None]=None) -> Union[Voter, None]:
    """Returns the Voter with a given token, if exists. Otherwise, 
    returns None.
    """
    session = get_session(session)
    return session.query(Voter).filter_by(token=token).first()

class Proxy(Base):
    __tablename__ = 'proxies'

    voter_id = Column(ForeignKey('voters.voter_id', ondelete="CASCADE"),
                      primary_key=True, nullable=False)
    email = Column(String, primary_key=True)

def create_proxy(event_identifier: Union[str, int, None],
                 voter_email: str, proxy_email: str,
                 session: Union[SQLAlchemySession, None]=None) -> Proxy:
    # TODO: Check for if the proxy exists already either as a voter or as a
    # proxy at this event.
    session = get_session(session)
    voter = voter_from_email(event_identifier, voter_email, session=session)
    proxy = Proxy(voter_id=voter.voter_id, email=proxy_email)
    add_and_commit(proxy, session)
    return proxy

def proxies_from_voter(voter: Voter,
                       session: Union[SQLAlchemySession, None]=None) -> Proxy:
    session = get_session(session)
    return session.query(Proxy).filter_by(voter_id=voter.voter_id).all()

def votes_for_voter(voter: Voter,
                    session: Union[SQLAlchemySession, None]=None) -> Proxy:
    """
    Returns the number of votes that a voter must give, defined as
    1 + number of proxies. If voter doesn't exist, return 0.
    """
    if voter is None:
        return 0
    proxies = proxies_from_voter(voter,
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
    is_open = Column(Boolean, default=False)

def create_poll(event_identifier: Union[int, str, None],
                name: str, start_time: Union[datetime, None]=None,
                end_time: Union[datetime, None]=None,
                session: Union[SQLAlchemySession, None]=None) -> Voter:
    session = get_session(session)
    if start_time is None:
        start_time = datetime.utcnow()
    event = get_event(event_identifier, session=session)
    poll = Poll(event_id=event.event_id, name=name, start_time=start_time,
                end_time=end_time)
    add_and_commit(poll, session)
    return poll

def polls_from_event(event_identifier: Union[int, str, None],
                     session: Union[SQLAlchemySession, None]=None):
    """Returns poll for an event, sorted by start time (most recent is first)."""
    session = get_session(session)
    event = get_event(event_identifier, session=session)
    return session.query(Poll).filter_by(event_id=event.event_id).order_by(desc('start_time')).all()

def poll_from_id(poll_id: Union[str, int],
                 session: Union[SQLAlchemySession, None]=None):
    """Returns poll for an event, sorted by start time (most recent is first)."""
    session = get_session(session)
    try:
        int_id = int(poll_id)
        return session.query(Poll).filter_by(poll_id=int_id).first()
    except:
        return None

def most_recent_poll(session: Union[SQLAlchemySession, None]=None):
    """Returns poll for an event, sorted by start time (most recent is first)."""
    session = get_session(session)
    return session.query(Poll).order_by(desc('start_time')).first()

class PollOption(Base):
    __tablename__ = 'poll_options'

    poll_option_id = Column(Integer, primary_key=True)
    name = Column(String)
    poll_id = Column(ForeignKey('polls.poll_id', ondelete="CASCADE"),
                     nullable=False)
    total_votes = Column(Integer, default=0)

def create_poll_option(poll_id: int, name: str,
                       session: Union[SQLAlchemySession, None]=None) -> PollOption:
    poll_option = PollOption(poll_id=poll_id, name=name)
    add_and_commit(poll_option, session)
    return poll_option

def poll_options_from_poll(poll_id: int,
                           session: Union[SQLAlchemySession, None]=None):
    session = get_session(session)
    return session.query(PollOption).filter_by(poll_id=poll_id).all()

def close_poll(poll_id: int, time: Union[datetime, None]=None,
               session: Union[SQLAlchemySession, None]=None):
    session = get_session(session)
    if time is None:
        time = datetime.utcnow()
    poll = session.query(Poll).filter_by(poll_id=poll_id).first()
    assert poll.start_time <= time
    poll.end_time = time
    poll.is_open = False
    session.commit()

def open_poll(poll_id: int, time: Union[datetime, None]=None,
               session: Union[SQLAlchemySession, None]=None):
    session = get_session(session)
    poll = session.query(Poll).filter_by(poll_id=poll_id).first()
    poll.end_time = None
    poll.is_open = True
    session.commit()

class VoteCast(Base):
    __tablename__ = 'votes_cast'

    voter_id = Column(ForeignKey('voters.voter_id', ondelete="CASCADE"), primary_key=True)
    poll_id = Column(ForeignKey('polls.poll_id', ondelete="CASCADE"), primary_key=True)

def is_voter_registered_for_poll(voter: Voter, poll: Poll,
                                 session: Union[SQLAlchemySession, None]=None) -> bool:
    return voter.event_id == poll.event_id

def has_voter_voted(voter: Voter, poll: Poll,
                    session: Union[SQLAlchemySession, None]=None) -> bool:
    session = get_session(session)
    cast = session.query(VoteCast).filter_by(
        voter_id=voter.voter_id, poll_id=poll.poll_id).first()
    if cast is None:
        return False
    else:
        return True

def _cast_vote_into_table(voter: Voter, poll: Poll,
                          session: Union[SQLAlchemySession, None]=None) -> VoteCast:
    vote_cast = VoteCast(voter_id=voter.voter_id, poll_id=poll.poll_id)
    add_and_commit(vote_cast, session)
    return vote_cast

def cast_vote(voter: Voter, vote_dict: dict,
              time: Union[datetime, None]=None,
              session: Union[SQLAlchemySession, None]=None) -> None:
    """Casts a vote. The vote_dict is a dictionary of 
        <poll_option_id>: <number of votes>.
    
    The vote is validated:
        - The total number of votes must be equal to the number of available
          votes for a voter. There is a possible option "None" for abstaining.
        - The votes must be nonnegative.
        - The `poll_option_id`s must refer to options from a single poll.
        - The `time` is after the start time of the poll and before the end
          time. If it's not given, it's taken to be `datetime.utcnow()`
        - The voter did not yet cast a vote in this poll.
        - The voter is registered for the event where this poll is.
    """
    session = get_session(session)
    if time is None:
        time = datetime.utcnow()
    # Validate
    if sum(vote_dict.values()) < votes_for_voter(voter, session=session):
        raise VoteExceptionTooFew
    if sum(vote_dict.values()) > votes_for_voter(voter, session=session):
        raise VoteExceptionTooMany
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
    poll = session.query(Poll).filter_by(poll_id=poll_id).first()
    if not is_voter_registered_for_poll(voter, poll, session=session):
        raise VoteExceptionWrongEvent
    if has_voter_voted(voter, poll, session=session):
        raise VoteExceptionAlreadyVoted
    if time < poll.start_time:
        raise VoteExceptionWrongTime
    elif poll.end_time is not None and time >= poll.end_time:
        raise VoteExceptionWrongTime
    elif not poll.is_open:
        raise VoteExceptionWrongTime
    # Update vote counts
    for key, votes in vote_dict.items():
        if key == ABSTAIN_KEY or key is None:
            continue
        key_int = int(key)
        poll_option = session.query(PollOption).filter_by(poll_option_id=key_int).first()
        poll_option.total_votes += votes
    _cast_vote_into_table(voter, poll, session=session)
    session.commit()

def create_all_tables(engine):
    Base.metadata.create_all(engine)

def render_table(table_obj, session: Union[SQLAlchemySession, None]=None,
                 **tabulate_kwargs):
    """Renders a string representation of a table."""
    session = get_session(session)
    query = session.query(table_obj).all()
    if len(query) == 0:
        return "Empty table"
    cols = [
        col for col in query[0].__dict__.keys()
        if col != '_sa_instance_state'
    ]
    rows = [
        [
            getattr(elem, col) for col in cols
        ]
        for elem in query
    ]
    return tabulate(rows, headers=cols, **tabulate_kwargs)

def votes_to_table(poll_id, session: Union[SQLAlchemySession, None]=None,
                  **tabulate_kwargs):
    poll_options = poll_options_from_poll(poll_id, session=session)
    cols = [
        'name',
        'total_votes'
    ]
    nice_cols = ['Option', 'Votes']
    rows = []
    for poll_option in poll_options:
        rows.append([
            getattr(poll_option, col)
            for col in cols
        ])
    return tabulate(rows, headers=nice_cols, **tabulate_kwargs)
