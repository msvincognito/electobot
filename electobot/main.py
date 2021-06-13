import logging
from datetime import datetime
from typing import Union
import os

from sqlalchemy.orm.session import Session as SQLAlchemySession

from .database import (event_from_identifier, get_session, Voter,
                       polls_from_event, voter_from_token, polls_from_event,
                       Poll, proxies_from_voter, votes_for_voter,
                       poll_options_from_poll)

# TODO: Implement things

logger = logging.getLogger('main')

URL_ROOT = os.environ.get('ELECTOBOT_URL_ROOT', 'http://localhost:5000/')

def form_url(path, args, root=URL_ROOT):
    # root has to end with /
    if len(args) == 0:
        return path
    else:
        strs = [
            '{}={}'.format(key, val)
            for key, val in args.items()
        ]
        return '{}{}?{}'.format(root, path, '&'.join(strs))

def event_register_url(event_identifier: Union[int, str, None],
                       session: Union[SQLAlchemySession, None]=None):
    session = get_session(session)
    event = event_from_identifier(event_identifier, session=session)
    if event is None:
        raise ValueError("No event with such identifier: {}".format(event_identifier))
    token = event.token
    return form_url('register', {'event_token': token})

def voting_url(voter: Voter,
               session: Union[SQLAlchemySession, None]=None):
    session = get_session(session)
    token = voter.token
    return form_url('vote', {'token': token})

def poll_url(voter_token, poll_id):
    return form_url('vote', {'token': voter_token,
                             'poll_id': poll_id})

def poll_list(voter_token,
                   session: Union[SQLAlchemySession, None]=None):
    # list of polls in the event that the voter is taking part in
    session = get_session(session)
    voter = voter_from_token(voter_token, session=session)
    # whether this voter exists should have been validated already
    polls = polls_from_event(voter.event_id, session=session)
    list_entries = [{"href": poll_url(voter_token, poll.poll_id),
                          "name": poll.name}
        for poll in polls
        if poll.is_open
    ]
    return list_entries

def poll_list_html(voter_token,
                   session: Union[SQLAlchemySession, None]=None):
    # list of polls in the event that the voter is taking part in
    session = get_session(session)
    voter = voter_from_token(voter_token, session=session)
    # whether this voter exists should have been validated already
    polls = polls_from_event(voter.event_id, session=session)
    html_list_entries = [
        "<li><a href=\"{}\">{}</a></li>".format(poll_url(voter_token,
                                                       poll.poll_id),
                                              poll.name)
        for poll in polls
        if poll.is_open
    ]
    return '\n'.join(html_list_entries)

def _vote_option_entry(poll_option_id_str, poll_option_name, vote_count):
    return """
<li><label for="vote${}">{}:</label><input type="number" id="vote${}" name="vote${}" min="0" max="{}" value="0"></li>
""".format(poll_option_id_str, poll_option_name, poll_option_id_str,
           poll_option_id_str, vote_count)

def poll_options(voter: Voter, poll: Poll,
                       session: Union[SQLAlchemySession, None]=None):
    proxies = proxies_from_voter(voter, session=session)
    if len(proxies) > 0:
        proxy_str = "You have {} proxy votes. You are voting for yourself and for: {}. ".format(
            len(proxies), ", ".join([
                proxy.email for proxy in proxies
            ]))
    else:
        proxy_str = "You have no proxy votes. "
    vote_count = votes_for_voter(voter, session=session)
    if vote_count == 1:
        vote_count_str = "So, you have only 1 vote."
    else:
        vote_count_str = "So, you have {} votes.".format(vote_count)
    proxy_message = proxy_str + vote_count_str
    option_list = poll_options_from_poll(poll.poll_id, session=session)
    
    return proxy_message, vote_count, option_list

def poll_options_html(voter: Voter, poll: Poll,
                       session: Union[SQLAlchemySession, None]=None):
    proxies = proxies_from_voter(voter, session=session)
    if len(proxies) > 0:
        proxy_str = "You have {} proxy votes. You are voting for yourself and for: {}. ".format(
            len(proxies), ", ".join([
                proxy.email for proxy in proxies
            ]))
    else:
        proxy_str = "You have no proxy votes. "
    vote_count = votes_for_voter(voter, session=session)
    if vote_count == 1:
        vote_count_str = "So, you have only 1 vote."
    else:
        vote_count_str = "So, you have {} votes.".format(vote_count)
    proxy_html = proxy_str + vote_count_str
    poll_options = poll_options_from_poll(poll.poll_id, session=session)
    html_list_entries = []
    for option in poll_options:
        poll_option_id_str = option.poll_option_id
        poll_option_name = option.name
        html_entry = _vote_option_entry(poll_option_id_str, poll_option_name,
                                        vote_count)
        html_list_entries.append(html_entry)
    html_list_entries.append(
        _vote_option_entry('abstain', 'Abstain',
                           vote_count)
    )
    return proxy_html, '\n'.join(html_list_entries)

def _parse_vote_form_key(vote_form_key):
    if 'vote$' in vote_form_key:
        shortened = vote_form_key.replace('vote$', '')
        try:
            return int(shortened)
        except:
            return shortened # 'abstain'
    else:
        raise ValueError('Invalid string form')

def parse_vote_form(vote_form):
    vote_entries = {}
    for key, value in vote_form.items():
        try:
            parsed_key = _parse_vote_form_key(key)
        except ValueError:
            continue
        vote_entries[parsed_key] = int(value)
    return vote_entries
