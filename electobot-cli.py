#!/usr/bin/env python3
import argparse

from electobot.database import (create_event, create_poll,
                                Event, Voter, Poll, PollOption, VoteCast,
                                Proxy, render_table, create_engine,
                                create_default_session, create_session,
                                create_all_tables, create_voter,
                                most_recent_poll, create_poll_option,
                                create_proxy, event_from_identifier,
                                votes_to_table)

NAME_TYPE_MAPPING = {
    'events': Event,
    'voters': Voter,
    'polls': Poll,
    'poll_options': PollOption,
    'vote_casts': VoteCast,
    'proxies': Proxy
}

def main():
    parser = argparse.ArgumentParser(description='Manage elections.')
    parser.add_argument('-p', '--path', default=None,
                                    help='sqlite database path')
    subparsers = parser.add_subparsers(help='commands', dest='command')
    
    # Setup
    setup_parser = subparsers.add_parser('setup')

    # Create
    create_parser = subparsers.add_parser('create')
    create_subparsers = create_parser.add_subparsers(help='commands',
                                                     dest='object')
    ## Create event
    create_event_parser = create_subparsers.add_parser('event')
    create_event_parser.add_argument('name')
    ## Create poll
    create_poll_parser = create_subparsers.add_parser('poll')
    create_poll_parser.add_argument('name')
    create_poll_parser.add_argument('-e', '--event', default=None)
    ## Create poll option
    create_voter_parser = create_subparsers.add_parser('poll_option')
    create_voter_parser.add_argument('name')
    create_voter_parser.add_argument('--poll_id', default=None)
    ## Create voter
    create_voter_parser = create_subparsers.add_parser('voter')
    create_voter_parser.add_argument('email')
    create_voter_parser.add_argument('-e', '--event', default=None)
    ## Create voter proxy
    create_voter_parser = create_subparsers.add_parser('proxy')
    create_voter_parser.add_argument('present_voter_email')
    create_voter_parser.add_argument('proxy_email')
    create_voter_parser.add_argument('-e', '--event', default=None)

    # List
    list_parser = subparsers.add_parser('print_table')
    list_parser.add_argument('object')
    # Tally
    list_parser = subparsers.add_parser('tally', help="Count votes for a poll")
    list_parser.add_argument('--poll_id', default=None)

    args = parser.parse_args()
    if args.path is None:
        session = create_default_session()
    else:
        engine = create_engine(path=args.path)
        session = create_session(engine)
    if args.command == 'setup':
        if args.path is None:
            engine = create_engine()
        else:
            engine = create_engine(path=args.path)
        create_all_tables(engine)
    elif args.command == 'create':
        if args.object == 'event':
            create_event(args.name, session=session)
        elif args.object == 'poll':
            create_poll(args.event, args.name, session=session)
        elif args.object == 'poll_option':
            if args.poll_id is None:
                poll = most_recent_poll(session=session)
                poll_id = poll.poll_id
            else:
                poll_id = args.poll_id
                poll = session.query(Poll).filter_by(poll_id=poll_id).first()
            create_poll_option(poll_id, args.name, session=session)
            print("Poll option {} created for poll {}".format(args.name,
                                                              poll.name))
        elif args.object == 'voter':
            event = event_from_identifier(args.event)
            voter = create_voter(args.event, args.email, session=session)
            print("Voter {} created for event {}".format(voter.email,
                                                         event.name))
            print("Token: {}".format(voter.token))
        elif args.object == 'proxy':
            create_proxy(args.event, args.present_voter_email,
                         args.proxy_email, session=session)
            print("Proxy created: {} will vote for {}".format(args.present_voter_email, args.proxy_email))
    elif args.command == 'print_table':
        if args.object not in NAME_TYPE_MAPPING:
            print("Unknown object. Possible values:", list(NAME_TYPE_MAPPING))
            exit(1)
        print(render_table(NAME_TYPE_MAPPING[args.object], session=session))
    elif args.command == 'tally':
        if args.poll_id is None:
            poll = most_recent_poll(session=session)
        else:
            poll = session.query(Poll).filter_by(poll_id=int(args.poll_id)).first()
        print(votes_to_table(poll.poll_id, session=session))
    else:
        exit(1)
        print("Unknown command")

if __name__ == '__main__':
    main()
