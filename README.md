# Electobot
The ultimate electoral arbiter.

Supports:
 - One vote per person
 - Proxy votes!
 - Multiple votes per event

## Workflow
All data is stored in an sqlite database.

### Management CLI
```
electobot create event <name>
electobot create poll [-e | --event <session>] [name]
electobot get-register-link [event]
electobot get-voter-link [-e | --event <session>]
```

### Database schema
 - Event - a single voting event (e.g. general assembly) which has specific people
   present and may include multiple polls
 - Poll - a single poll (or vote) connected to a session, with a name and start time.
 - Voter - a single voter at a session, who may have a number of extra (proxy) votes
 - VotesTaken - a table matching who voted, so who should not vote again on a poll
 - PollOption - an option in a poll
