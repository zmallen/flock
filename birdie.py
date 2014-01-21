#!/usr/bin/python
import gevent
from twython import Twython, TwythonError
from ircbot import IrcNodeHead

class TwitterBot:
    def __init__(self, name, con_k, con_s, acc_k, acc_s):
        self.name = name
        self.con_k = con_k
        self.con_s = con_s
        self.acc_k = acc_k
        self.acc_s = acc_s
        self.twitter = Twython(self.con_k, self.con_s, self.acc_k, self.acc_s)

    def tweet(self,msg):
        if self.twitter is not None:
            # > 140 char detection
            if len(msg) > 140:
                msg = msg[0:139]
            self.twitter.update_status(status=msg)

def main():
    # get bot info
    with open('bots.csv', 'r') as bot_file:
        try:
            read_in = bot_file.readlines()
            # get lines and filter out comments or misconfigured lines
            lines = [ l.rstrip() for l in read_in if not l.startswith("#") and (l.startswith("bot=") or l.startswith("irc="))]
            if len(lines) <= 0:
               raise Exception("Could not load any bots from bot_file") 
            # read in irc info, will always read first one
            irc_lines = [ l for l in lines if l.startswith("irc=")]
            if len(irc_lines) <= 0:
                raise Exception("Could not load IRC info from bot_file")
            # remove irc_line from lines
            map(lambda x: lines.remove(x), irc_lines)
            print irc_lines
            irc_serv, irc_chan = irc_lines[0].split("=")[1].split(",")
            # spawn the bots, give them 45 seconds to connect to twitter then return the object 
            # we will wait and start the thread for irc as our main event loop
            jobs = [ gevent.spawn(spawn_bots, line) for line in lines ]
            gevent.joinall(jobs, timeout=45)
            # get all the twitter bots, will raise exception if oauth fails
            bot_list = [ bot.value for bot in jobs ]
            # join irc as a nodehead , this bot controls many twitter bots and runs campaigns for all
            port = "6667"
            if ":" in irc_serv:
                irc_serv,port = irc_serv.split(":")
            irc_bot = IrcNodeHead(irc_chan, name, irc_serv, port)
            irc_bot.start()

        except Exception as e:
            #syslog.syslog(syslog.LOG_ERR, 'BIRDIE: ' + str(e))
            print "ERROR: " + str(e)

# spawn bots given the config options, and return the object to jobs
def spawn_bots(bot_line):
    name, con_k, con_s, acc_k, acc_s = bot_line.split("=")[1].split(",")
    return TwitterBot(name, con_k, con_s, acc_k, acc_s)

if __name__ == "__main__":
    main()
