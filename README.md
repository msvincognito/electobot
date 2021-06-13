# Electobot
The ultimate electoral arbiter.

Supports:
 - One vote per person
 - Proxy votes!
 - Multiple votes per event

This vote was intended for Incognito events that require voting. Feel free to do whatever you want with it.

## Workflow
All data is stored in an sqlite database.

### Mail credentials
Mail credentials should be stored in a file named `mail_credentials` in this format:
```
Mail server (e.g. mail.msvincognito.nl)
port number (e.g. 465)
username (e.g. electobot)
password (e.g. hunter2)
sender email (e.g. electobot@msvincognito.nl)
```
### Management CLI
Install the requirements:
```shell
pip install -r requirements.txt
```

Setup the bot:
```shell
python electobot-cli.py setup
```
Create an event and poll
```shell
python electobot-cli.py create event <name>
python electobot-cli.py create poll [-e | --event <session>] [name]
python electobot-cli.py create poll_option [--poll_id <POLL_ID>] [name]
python electobot-cli.py open [--poll_id <POLL_ID>]
```

Listing all events:
```shell
python electobot-cli.py list events
```
Deleting an event:
```shell
python electobot-cli.py delete event <event_id>
```

Running the server locally (for testing only):
```shell
python -m flask run
```
### Database schema
 - Event - a single voting event (e.g. general assembly) which has specific people
   present and may include multiple polls
 - Poll - a single poll (or vote) connected to a session, with a name and start time.
 - Voter - a single voter at a session, who may have a number of extra (proxy) votes
 - VotesTaken - a table matching who voted, so who should not vote again on a poll
 - PollOption - an option in a poll
