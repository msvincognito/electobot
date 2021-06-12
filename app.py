"""
This is a basic flask app that allows for simple one time 
registering & password changes.
"""
import re

from flask import Flask, request

from electobot.database import (event_from_token, create_voter,
                                voter_from_token, poll_from_id, has_voter_voted)
from electobot.main import (event_register_url, voting_url, poll_list_html,
                            poll_options_html, parse_vote_form, cast_vote,
                            poll_url)
from .exceptions import (VoteExceptionTooFew, VoteExceptionTooMany,
                         VoteExceptionWrongId, VoteExceptionNegative,
                         VoteExceptionWrongTime, VoteExceptionWrongEvent,
                         VoteExceptionAlreadyVoted)
from electobot.send_email import send_message

app = Flask(__name__)
ELECTOBOT_LEGAL_EMAIL_PATTERN = r"maastrichtuniversity.nl$"

def parse_template(path, **kwargs):
    with open(path) as file_:
        str_ = file_.read() 
        for from_, to in kwargs.items():
            str_ = str_.replace("{%"+from_+"%}", to)
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
        match = re.search(ELECTOBOT_LEGAL_EMAIL_PATTERN, email)
        if not match:
            return parse_template('templates/error.html',
                                  message='Email address not permitted. Use a maastrichtuniversity.nl email')
        voter = create_voter(event.event_id, email)
        url = voting_url(voter)
        send_message(email, "{} voting link".format(event.name),
                     "The URL to vote is: {}".format(url))
        return parse_template('templates/blank.html', "Voting email sent! Check your {} mail.".format(email))

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
    all_votes_url_back = "<a href="">Go back</a>".format(voting_url(voter))
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
        return parse_template('templates/message.html', message='Vote cast! {}'.format(all_votes_url_back))

@app.route('/', methods=['GET'])
def welcome():
    return parse_template('templates/blank.html',
                          message="Hello! Ask the vote organizers to register, or check your email if you already did.")
    if request.method == 'GET':
        token = request.args.get('token')
        if not token:
            return parse_template('templates/register.html')
        elif verify_token(token) and not token_already_used(token):
            return parse_template('templates/vote.html', token=token)
        else:
            return parse_template('templates/wrong_token.html', token=token)
    if request.method == 'POST':
        token = request.form.get('token')
        email = request.form.get('email')
        print(request.form)
        votes = []
        for id_, value in request.form.items():
            if 'vote' in id_ and value == 'on':
                votes.append(id_[5:])
        if email:
            if not 'maastrichtuniversity.nl' in email:
                return parse_template('templates/not_uni_email.html',
                                      email=email)
            try:
                token = new_token(email)
            except UserAlreadyExists:
                return parse_template('templates/email_used.html')
            url = token_url(token)
            try:
                send_message(email, "Website competition vote token", 
                             "The URL to vote is: {}".format(url))
                return parse_template('templates/email_sent.html')
            except:
                return parse_template('templates/error.html')
        elif len(votes) > 0:
            if verify_token(token) and not token_already_used(token):
                if len(votes) == 3:
                    for vote in votes:
                        add_vote(vote)
                    use_token(token)
                    return parse_template('templates/voted.html')
                else:
                    return parse_template('templates/wrong_number_of_votes.html')
            else:
                return parse_template('templates/wrong_token.html', token=token)
        else:
            return parse_template('templates/error.html')
