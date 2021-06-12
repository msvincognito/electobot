FROM tiangolo/uwsgi-nginx-flask:python3.7

COPY ./requirements.txt .

RUN apt-get update && apt-get install -y python-dev libssl-dev libldap2-dev libsasl2-dev
RUN pip3 install -r requirements.txt

COPY ./app.py /app/main.py
COPY ./electobot /app/electobot
COPY ./templates /app/templates
COPY ./electobot-cli.py /usr/bin/electobot-cli.py