"""
This is a basic flask app that allows for simple one time 
registering & password changes.
"""
import re
import os

from flask import Flask, request

from electobot.database import (event_from_token, create_voter,
                                voter_from_token, poll_from_id,
                                has_voter_voted, cast_vote, get_session)
from electobot.main import (event_register_url, voting_url, poll_list_html,
                            poll_options_html, parse_vote_form, poll_url)
from electobot.exceptions import (VoteExceptionTooFew, VoteExceptionTooMany,
                         VoteExceptionWrongId, VoteExceptionNegative,
                         VoteExceptionWrongTime, VoteExceptionWrongEvent,
                         VoteExceptionAlreadyVoted, DBExceptionEmailAlreadyUsed)
from electobot.send_email import send_message

app = Flask(__name__)

def parse_template(path, **kwargs):
    with open(path) as file_:
        str_ = file_.read() 
        for from_, to in kwargs.items():
            str_ = str_.replace("{% "+from_+" %}", to)
            str_ = str_.replace("{%"+from_+"%}", to) # quite a messy solution but whatever
        return str_

@app.route('/register', methods=['GET', 'POST'])
def register():
    token = request.args.get('event_token')
    if not token:
        return parse_template('templates/error.html',
                              message="Please provide an event token")
    event = event_from_token(token)
    if not event:
        return parse_template('templates/error.html',
                              message="Unfortunately token {} does not refer to an event.".format(
                                token))
    if request.method == 'GET':
        return parse_template('templates/register.html',
                              event_token=event.token,
                              event_name=event.name)
    elif request.method == 'POST':
        email = request.form.get('email')
        print(event.email_pattern)
        match = re.search(event.email_pattern, email)
        if not match:
            return parse_template('templates/error.html',
                                  message='Email address not permitted.')
        session = get_session()
        try:
            voter = create_voter(event.event_id, email, session=session)
        except DBExceptionEmailAlreadyUsed:
            return parse_template('templates/error.html',
                                  message='Email already used. Check your email. If you did not get an email, contact the host of the vote.')
        url = voting_url(voter, session=session)
        send_message(email, "{} voting link".format(event.name),
                     "The URL to vote is: {}".format(url))
        return parse_template('templates/blank.html', message="Voting email sent! Check your {} mail.".format(email))

@app.route('/vote', methods=['GET', 'POST'])
def vote():
    token = request.args.get('token')
    if not token:
        return parse_template('templates/error.html',
                              message="Invalid token. Please use the link from your email.")
    voter = voter_from_token(token)
    if not voter:
        return parse_template('templates/error.html',
                              message="Invalid token. Please use the link from your email.")
    all_votes_url_back = "<a href=\"{}\">Go back</a>".format(voting_url(voter))
    print(all_votes_url_back)
    if request.method == 'GET':
        poll_id = request.args.get('poll_id')
        if not poll_id: # Send a list of possible polls
            html_list = poll_list_html(token)
            return parse_template('templates/available_votes.html', list=html_list)
        else: # Otherwise send the list of options
            poll = poll_from_id(poll_id)
            if poll is None or poll.event_id != voter.event_id:
                return parse_template('templates/error.html',
                                      message="No poll with such id: {}. {}".format(poll_id, all_votes_url_back))
            if has_voter_voted(voter, poll):
                return parse_template('templates/blank.html',
                                      message="You already voted in this poll. {}".format(all_votes_url_back))
            proxy_html, options_list_html = poll_options_html(voter, poll)
            return parse_template('templates/vote_options.html',
                                  voter_token=token, poll_id=poll_id,
                                  proxy_html=proxy_html,
                                  options_list_html=options_list_html)
    elif request.method == 'POST':
        poll_id = request.args.get('poll_id')
        if not poll_id:
            return parse_template('templates/error.html',
                                  message="Broken request. No poll id. {}".format(poll_id, all_votes_url_back
                                            ))
        poll = poll_from_id(poll_id)
        if poll is None or poll.event_id != voter.event_id:
            return parse_template('templates/error.html',
                                  message="No poll with such id: {}. {}".format(poll_id, all_votes_url_back))
        this_poll_url_back = "<a href="">Go back</a>".format(poll_url(token,
                                                                      poll_id))
        try:
            vote_dict = parse_vote_form(request.form)
        except ValueError:
            return parse_template('templates/error.html',
                                  message="Broken request. Try again. {}".format(this_poll_url_back))
        try:
            cast_vote(voter, vote_dict)
        except VoteExceptionTooFew:
            return parse_template('templates/error.html',
                                  message="Not all possible votes assigned. Try again. {}".format(this_poll_url_back))
        except VoteExceptionTooMany:
            return parse_template('templates/error.html',
                                  message="Too many votes assigned. Try again. {}".format(this_poll_url_back))
        except VoteExceptionWrongId:
            return parse_template('templates/error.html',
                                  message="Wrong id. Try again. {}".format(all_votes_url_back))
        except VoteExceptionWrongTime:
            return parse_template('templates/error.html',
                                  message="Wrong time to vote. The vote may be closed already, or has not started yet. {}".format(all_votes_url_back))
        except VoteExceptionWrongEvent:
            return parse_template('templates/error.html',
                                  message="Wrong event. {}".format(all_votes_url_back))
        except VoteExceptionNegative:
            return parse_template('templates/error.html',
                                  message="Can't cast negative votes. Try again. {}".format(this_poll_url_back))
        except VoteExceptionAlreadyVoted:
            return parse_template('templates/error.html',
                                  message="You already voted for this poll. {}".format(all_votes_url_back))
        return parse_template('templates/blank.html', message='Vote cast! {}'.format(all_votes_url_back))

@app.route('/', methods=['GET'])
def welcome():
    return parse_template('templates/blank.html',
                          message="Hello! Ask the vote organizers to register, or check your email if you already did.")
