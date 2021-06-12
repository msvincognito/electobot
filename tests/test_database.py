import pytest
from datetime import datetime, timedelta

from electobot.database import (create_engine, create_all_tables,
                                create_session, create_event,
                                most_recent_event, event_from_identifier,
                                simplify_event_name, create_voter,
                                voter_from_token, voter_from_email,
                                create_proxy, votes_for_voter, create_poll,
                                polls_from_event, create_poll_option,
                                poll_options_from_poll, cast_vote,
                                render_table, Event)
from electobot.exceptions import VoteExceptionTooFew, VoteExceptionNegative

def create_test_engine():
    return create_engine(path=":memory:", echo=True)

@pytest.fixture
def clean_session():
    engine = create_test_engine()
    create_all_tables(engine)
    session = create_session(engine)
    return session

def _expected_date_prefix(now=None):
    if now is None:
        now = datetime.utcnow()
    date_str = now.strftime("%Y-%m-%d")
    return date_str

def test_simplify_event_name():
    name = "Capybaras and Reptiles 2021 - which are better? Which are worse?"
    expected_simple_postfix = "capybaras_and_reptiles_2021_which_are_better_which_are_worse"
    now = datetime.utcnow()
    expected_simple_name = (_expected_date_prefix(now=now)
                              + '-' + expected_simple_postfix)
    assert simplify_event_name(name, datetime=now)  == expected_simple_name

def test_create_and_query_event(clean_session):
    event = most_recent_event(session=clean_session)
    assert event is None

    name = "General Assembly 2020/2021"
    expected_simple_postfix = "general_assembly_20202021"
    expected_simple_name = (_expected_date_prefix()
                              + '-' + expected_simple_postfix)
    create_event(name, session=clean_session)
    event = most_recent_event(session=clean_session)
    assert event is not None
    assert event.simple_name == expected_simple_name

    name_2 = "General Reassembly 2020/2021"
    expected_simple_postfix_2 = "general_reassembly_20202021"
    expected_simple_name_2 = (_expected_date_prefix()
                              + '-' + expected_simple_postfix_2)
    create_event(name_2, session=clean_session)
    event = most_recent_event(session=clean_session)
    assert event is not None
    assert event.simple_name == expected_simple_name_2

    event = event_from_identifier('1', session=clean_session)
    assert event.name == name
    event = event_from_identifier(name_2, session=clean_session)
    assert event.name == name_2
    event = event_from_identifier(expected_simple_name, session=clean_session)
    assert event.name == name

def test_create_and_query_voter(clean_session):
    name = "General Assembly 2020/2021"
    create_event(name, session=clean_session)
    event = most_recent_event(session=clean_session)
    identifier = event.simple_name

    email = 'someone@someplace.eu'
    voter = create_voter(identifier, email, session=clean_session)
    token = voter.token

    assert voter_from_token(token, session=clean_session).email == email
    assert (voter_from_email(identifier, email, session=clean_session).token
            == token)

def test_create_proxy(clean_session):
    name = "General Assembly 2020/2021"
    create_event(name, session=clean_session)
    event = most_recent_event(session=clean_session)
    identifier = event.simple_name

    email = 'someone@someplace.eu'
    create_voter(identifier, email, session=clean_session)

    # query the voter like we would in the real application
    voter = voter_from_email(identifier, email, session=clean_session)
    assert votes_for_voter(voter, session=clean_session) == 1
    
    create_proxy(identifier, email, 'proxyboi@someplace.eu',
                 session=clean_session)
    create_proxy(identifier, email, 'proxygirl@someplace.eu',
                 session=clean_session)
    assert votes_for_voter(voter, session=clean_session) == 3

def test_create_and_query_poll(clean_session):
    name = "General Assembly 2020/2021"
    create_event(name, session=clean_session)
    event = most_recent_event(session=clean_session)
    identifier = event.simple_name

    poll_name = "Who wins?"
    poll_name_2 = "Soup people: trust them or not?"
    now = datetime.utcnow()
    earlier = now - timedelta(hours=1)
    poll = create_poll(identifier, poll_name, start_time=earlier,
                       session=clean_session)
    create_poll(identifier, poll_name_2, start_time=now,
                session=clean_session)

    # Now query
    polls = polls_from_event(identifier, session=clean_session)
    ## Earlier one should be further down the list
    assert polls[1].name == poll_name
    assert polls[0].name == poll_name_2

    # Poll options!
    poll_options = {"Old Board", "New Board"}
    poll = polls[0]
    for option in poll_options:
        create_poll_option(poll.poll_id, option, session=clean_session)

    # Query and see if we can get poll options again
    poll = polls_from_event(identifier, session=clean_session)[0]
    poll_options_queried = set(
        [
            poll_option.name for poll_option
            in poll_options_from_poll(poll.poll_id, session=clean_session)
        ]
    )
    assert poll_options == poll_options_queried

def perform_vote(clean_session):
    event_name = "General Assembly 2020/2021"
    event = create_event(event_name, session=clean_session)
    identifier = event.simple_name

    poll_name = "Is the new board elected?"
    now = datetime.utcnow()
    later = now + timedelta(hours=1)
    slightly_later = now + timedelta(minutes=5)
    poll = create_poll(identifier, poll_name, start_time=now,
                       session=clean_session)
    poll_options = ["Yes", "No"]
    poll_option_ids = []
    for option in poll_options:
        poll_option = create_poll_option(poll.poll_id, option, session=clean_session)
        poll_option_ids.append(poll_option.poll_option_id)
    poll_map = {
        poll_option_name: poll_option_id
        for poll_option_name, poll_option_id in zip(poll_options,
                                                    poll_option_ids)
    }

    email = 'someone@someplace.eu'
    voter_with_proxies = create_voter(identifier, email, session=clean_session)
    create_proxy(identifier, email, 'proxyboi@someplace.eu',
                 session=clean_session)
    create_proxy(identifier, email, 'proxygirl@someplace.eu',
                 session=clean_session)
    vote_dict = {
        poll_map['Yes']: 1,
        poll_map['No']: 1,
        'abstain': 0
    }
    try:
        cast_vote(voter_with_proxies, vote_dict, time=slightly_later,
                  session=clean_session)
        assert False
    except VoteExceptionTooFew:
        assert True
    vote_dict = {
        poll_map['Yes']: -1,
        poll_map['No']: 1,
        'abstain': 3
    }
    try:
        cast_vote(voter_with_proxies, vote_dict, time=slightly_later,
                  session=clean_session)
        assert False
    except VoteExceptionNegative:
        assert True
    vote_dict = {
        poll_map['Yes']: 2,
        poll_map['No']: 1,
        'abstain': 0
    }
    cast_vote(voter_with_proxies, vote_dict, time=slightly_later,
              session=clean_session)
    try:
        cast_vote(voter_with_proxies, vote_dict, time=slightly_later,
                  session=clean_session)
        assert False
    except VoteExceptionAlreadyVoted:
        assert True

def test_render_table(clean_session):
    # Just test for crash
    create_event("Anything", session=clean_session)
    print(render_table(Event, clean_session))
