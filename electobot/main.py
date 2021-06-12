import logging
from typing import Union

from .database import (create_default_session, Event, Voter, Proxy,
                       add_and_commit, event_from_identifier, most_recent_event)
from .token import gen_token, voter_from_token


logger = logging.getLogger('main')


