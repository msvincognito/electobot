#!/bin/bash
# This script is a shorthand for communicating with electobot-cli.py

docker-compose exec electobot electobot-cli.py "$@"

