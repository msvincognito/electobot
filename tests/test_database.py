import pytest
from datetime import datetime

from electobot.database import (create_engine, create_all_tables,
                                create_session, create_event,
                                most_recent_event, event_from_identifier)

def create_test_engine():
    return create_engine(path=":memory:")

@pytest.fixture
def clean_session():
    engine = create_test_engine()
    create_all_tables(engine)
    session = create_session(engine)
    return session

def _expected_date_prefix():
    now = datetime.utcnow()
    date_str = now.strftime("%Y-%m-%d")
    return date_str

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
