#!/usr/bin/python
import gevent
from twython import Twython, TwythonError
from ircbot import IrcNodeHead
import json
import syslog
import settings
import random
import sys
from datetime import datetime, date, time, timedelta
from random import randint



def main():
    reload(sys)
    sys.setdefaultencoding('utf-8')
    # get bot info
    irc_chan = settings.channel
    irc_serv = settings.server
    irc_port = settings.port
    irc_name = settings.name 
    irc_bot = IrcNodeHead(
        irc_chan, irc_name, irc_serv, irc_port)
    irc_bot.start()

if __name__ == "__main__":
    main()
