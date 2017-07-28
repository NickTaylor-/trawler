# Trawler

Trawler is a Flask based web application that allows users to submit suspicious emails via an API for analysis by a SOC/CERT/IT Team/etc. Currently there is no supported submission mechanisms, but a plugin for Outlook is in the works.

Note this is currently in *very* much a pre-alpha state, and should not be expected to work, and if it does happen to work, do not expect it to stay that way.

## Installation/running

These installation instructions _should_ work (must be using Python 3):

```
pip install -r requirements.txt
chmod +x trawler.py
./trawler.py db upgrade
./trawler.py runserver
```