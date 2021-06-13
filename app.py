"""
This is a basic flask app that allows for simple one time 
registering & password changes.
"""
import re
import os

from flask import Flask, request, render_template

from electobot.database import (event_from_token, create_voter,
                                voter_from_token, poll_from_id,
                                has_voter_voted, cast_vote, get_session)
from electobot.main import (event_register_url, voting_url, poll_list,
                            poll_options, parse_vote_form, poll_url)
from electobot.exceptions import (VoteExceptionTooFew, VoteExceptionTooMany,
                         VoteExceptionWrongId, VoteExceptionNegative,
                         VoteExceptionWrongTime, VoteExceptionWrongEvent,
                         VoteExceptionAlreadyVoted, DBExceptionEmailAlreadyUsed)
from electobot.send_email import send_message

app = Flask(__name__)

@app.route('/register', methods=['GET', 'POST'])
def register():
    token = request.args.get('event_token')
    if not token:
        token = request.form.get('event_token')
    if not token:
        return render_template('register.html',
                              errors=["Please provide an event token in the URL"])
    event = event_from_token(token)
    if not event:
        return render_template('register.html',
                              errors=["Unfortunately token {} does not refer to an event.".format(
                                token)])
    if request.method == 'GET':
        return render_template('register.html',
                              event_token=event.token,
                              event_name=event.name)
    elif request.method == 'POST':
        email = request.form.get('email')
        match = re.search(event.email_pattern, email)
        if not match:
            return render_template('register.html',
                              errors=['Email address not permitted.'], 
                              event_token=event.token,
                              event_name=event.name)
        session = get_session()
        try:
            voter = create_voter(event.event_id, email, session=session)
        except DBExceptionEmailAlreadyUsed:
            return render_template('register.html',
                              warnings=['Email already used. Check your email. If you did not get an email, contact the host of the vote.'], 
                              event_token=event.token,
                              event_name=event.name)
        url = voting_url(voter, session=session)
        send_message(email, "{} voting link".format(event.name),
                     "The URL to vote is: {}".format(url))
        return render_template('blank.html', message="Voting email sent! Check your {} mail.".format(email))

@app.route('/vote', methods=['GET', 'POST'])
def vote():
    token = request.args.get('token')
    if not token:
        return render_template('available_votes.html',
                              errors=["Invalid token. Please use the link from your email."])
    voter = voter_from_token(token)
    if not voter:
        return render_template('available_votes.html',
                              errors=["Invalid token. Please use the link from your email."])
    all_votes_url_back = "<a href=\"{}\">Go back</a>".format(voting_url(voter))
    if request.method == 'GET':
        poll_id = request.args.get('poll_id')
        if not poll_id: # Send a list of possible polls
            polls = poll_list(token)
            return render_template('available_votes.html', list=polls)
        else: # Otherwise send the list of options
            poll = poll_from_id(poll_id)
            if poll is None or poll.event_id != voter.event_id:
                return render_template('available_votes.html',
                                      errors=["No poll with such id: {}. {}".format(poll_id, all_votes_url_back)])
            if has_voter_voted(voter, poll):
                return render_template('blank.html',
                                      message="You already voted in this poll. {}".format(all_votes_url_back))
            proxy_message, vote_count, option_list = poll_options(voter, poll)
            return render_template('vote_options.html',
                                  voter_token=token, poll_id=poll_id,
                                  proxy_message=proxy_message,
                                  option_list=option_list, vote_count=vote_count)
    elif request.method == 'POST':
        poll_id = request.args.get('poll_id')
        if not poll_id:
            return render_template('index.html',
                                  errors=["Broken request. No poll id. {}".format(poll_id, all_votes_url_back
                                            )])
        poll = poll_from_id(poll_id)
        if poll is None or poll.event_id != voter.event_id:
            return render_template('index.html',
                                  errors=["No poll with such id: {}. {}".format(poll_id, all_votes_url_back)])
        this_poll_url_back = "<a href="">Go back</a>".format(poll_url(token,
                                                                      poll_id))
        try:
            vote_dict = parse_vote_form(request.form)
        except ValueError:
            return render_template('index.html',
                                  errors=["Broken request. Try again. {}".format(this_poll_url_back)])
        try:
            cast_vote(voter, vote_dict)
        except VoteExceptionTooFew:
            return render_template('index.html',
                                  errors=["Not all possible votes assigned. Try again. {}".format(this_poll_url_back)])
        except VoteExceptionTooMany:
            return render_template('index.html',
                                  errors=["Too many votes assigned. Try again. {}".format(this_poll_url_back)])
        except VoteExceptionWrongId:
            return render_template('index.html',
                                  errors=["Wrong id. Try again. {}".format(all_votes_url_back)])
        except VoteExceptionWrongTime:
            return render_template('index.html',
                                  errors=["Wrong time to vote. The vote may be closed already, or has not started yet. {}".format(all_votes_url_back)])
        except VoteExceptionWrongEvent:
            return render_template('index.html',
                                  errors=["Wrong event. {}".format(all_votes_url_back)])
        except VoteExceptionNegative:
            return render_template('index.html',
                                  errors=["Can't cast negative votes. Try again. {}".format(this_poll_url_back)])
        except VoteExceptionAlreadyVoted:
            return render_template('index.html',
                                  errors=["You already voted for this poll. {}".format(all_votes_url_back)])
        return render_template('blank.html', message='Vote cast! {}'.format(all_votes_url_back))

@app.route('/', methods=['GET'])
def welcome():
    return render_template('blank.html',
                          message="Hello! Ask the vote organizers to register, or check your email if you already did.")
