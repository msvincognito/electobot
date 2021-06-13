# Electobot
The ultimate electoral arbiter.

Supports:
 - One vote per person
 - Proxy votes!
 - Multiple votes per event

This vote was intended for Incognito events that require voting. Feel free to do whatever you want with it.

## Usage
### Running locally
To set up the service locally, install requirements in your favourive virtual
environment `pip install -r requirements.txt`. Then, you need to make a
`mail_credentials` file in your current working directory with contents as follows,
line by line:
```
Mail server (e.g. mail.msvincognito.nl)
port number (e.g. 465)
username (e.g. electobot)
password (e.g. hunter2)
sender email (e.g. electobot@msvincognito.nl)
```
With that done, now you can use the `./electobot-cli.py` script to manage the votes.
Before you can launch the server itself, run these commands. They will set up the
database and give you a register link you can send out to people:
```shell
# Create the sqlite database with tables
./electobot-cli.py setup
# Create an event. Running the line below returns a reigster link, which you can send
# out to people to sign up once you start the server itself
./electobot-cli.py create event "General Assembly"
```
Now that there is an event, you can launch the server for testing locally as
```shell
python -m flask run
```
Now the flask server is running (presumably at `localhost:5000`), so you can check it
out there. To open a vote, do the following:
```shell
./electobot-cli.py create poll "Is the new president elected?"
./electobot-cli.py create poll_option "Yes"
./electobot-cli.py create poll_option "No"
./electobot-cli.py open
```

Once people are done voting, you can do
```shell
./electobot-cli.py tally
```

By default commands refer to the most recent event/poll, but you can change that by
using the `--event` or `--poll_id` argument. You can see a list of all polls/events
in the database by running
```shell
./electobot-cli.py print_table polls
```
or
```shell
./electobot-cli.py print_table events
```
the output is a bit messy, because it's literally the entire SQL table. Sorry about
that.

To get a list of events with register links for them, do
```shell
./electobot-cli.py list events
```

You can also delete events as follows:
```shell
python electobot-cli.py delete event <event_id>
```

### Running on a server
When running this on a server, you should be sure to use SSL. This way people's email
addresses won't fly through the cyberspace in plaintext. To do that, we provided a
docker setup which runs an nginx server that accepts SSL encrypted requests and
forwards them to the electobot backend. Before you can use this, you need to get some
certificates. We recommend letsencrypt. Look into `certbot` for how to obtain them.

Once you have these certificates, you need to have Docker and `docker-compose`
installed. Then go to the `docker-infrastructure` directory and modify the `.env`
config file with parameters of choice. Then, run `docker-compose up -d`. This will
build the electobot Docker image and launch the app. There is a `./electobot-cli.py`
helper script in the `docker-infrastructure` directory which talks to the
`./electobot-cli.py` script on the Docker container for managing the service. Make
sure you have a `mail_credentials` file in the root directory of the repo, like
described in the `Running locally` section.

Good luck.
