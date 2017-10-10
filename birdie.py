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


class TwitterBot:

    def __init__(self, name, con_k, con_s, acc_k, acc_s):
        self.name = name
        self.con_k = con_k
        self.con_s = con_s
        self.acc_k = acc_k
        self.acc_s = acc_s
        self.twitter = Twython(self.con_k, self.con_s, self.acc_k, self.acc_s)
        self.last_intervals = []
        self.last_tweet = ""

    def tweet(self, msg):
        if self.twitter is not None:
            # > 140 char detection
            if len(msg) > 140:
                msg = msg[0:139]
            syslog.syslog('%s is tweeting %s' % (self.name, msg))
            try:
                self.twitter.update_status(status=msg)
                self.last_tweet = msg
            except Exception as e:
                syslog.syslog('%s error tweeting -> %s' % (self.name, str(e)))


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
