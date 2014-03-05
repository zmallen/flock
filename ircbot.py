import irc.bot
import irc.strings
import json
import syslog
import requests 
import gevent
import string
import random

class IrcNodeHead(irc.bot.SingleServerIRCBot):
    def __init__(self, channel, nickname, server, port, bot_list):
        irc.bot.SingleServerIRCBot.__init__(self, [(server, port)], nickname, nickname)
        self.channel = channel
        self.post_url = "https://www.googleapis.com/urlshortener/v1/url"
        self.bot_list = bot_list

    def on_nicknameinuse(self, c, e):
        c.nick(c.get_nickname() + "_")

    def on_welcome(self, c, e):
        c.join(self.channel)

    def msg_channel(self, c, msg):
        if(len(msg) > 512):
            for chunk in self.chunk_msg(msg):
                print 'chunk: ' + str(len(chunk)) + " ->" + chunk
                c.privmsg(self.channel, chunk)
        else:
            c.privmsg(self.channel, msg)

    # need a lazy generator here because irc wont take anything over 512 bytes / message        
    def chunk_msg(self, msg):
        for i in xrange(0, len(msg), 511):
            yield msg[i:i+511]

    def on_pubmsg(self, c, e):
        a = e.arguments[0].split(" ")
        if a[0] == "?botlist":
            msg = ','.join([b.name for b in self.bot_list])
            self.msg_channel(c, msg)
        elif a[0] == "?shorten":
            if len(a) == 2:
                url = a[1]
                self.msg_channel(c, self.shorten(url))
            else:
                self.msg_channel(c, "usage: ?shorten url")
        elif a[0] == "?campaign":
            self.make_campaign(c, a)
        elif a[0] == "?gettrends":
            self.msg_channel(c, str(self.bot_list[0].get_global_trends()))
        elif a[0] == "?tweet":
            #?tweet botname msg
            if len(a) >= 3:
                bot = self.get_bot(a[1])
                if bot:
                    bot.tweet(' '.join(a[2:]))
                    self.msg_channel(c, 'Tweeted on http://twitter.com/%s' % bot.name)
                else:
                    self.msg_channel(c, "bot not in bot_list, try: " + ','.join([bot.name for bot in self.bot_list]))
            else:
                self.msg_channel(c, "usage: ?tweet botname msg")

    def random_char(self, y):
        return ''.join(random.choice(string.ascii_letters) for x in range(y))

    def make_campaign(self, c, msg):
        campaign = msg
        print campaign
        #?campaign all|botname url
        if(len(campaign) != 3):
            self.msg_channel(c, "usage: ?campaign all|botname")
            return
        campaign_type = campaign[1]
        campaign_url = campaign[2]
        # if its a campaign for all the bots this bot controls, generate a short url for each one
        if campaign_type == "all":
            self.msg_channel(c, "starting all..")
            # get unique shortened urls for each bot
            urls = []
            for i in range(len(self.bot_list)):
                urls.append(self.shorten(campaign_url))
            # create a dict of tuples of urls to bots
            url_tuples = dict(zip(self.bot_list, urls))
            # asynchronously post to twitter
            jobs = [ gevent.spawn(bot.post_campaign, url) for bot, url in url_tuples.iteritems() ]
            gevent.joinall(jobs, timeout=750)
            # should log here: time start, time end, bot,url combos for tracking
            self.msg_channel(c, "Campaign complete")
        else:
            # if its for a specific bot name, then check to see if this bot has that handle authenticated, then work
            bot = self.get_bot(campaign_type)
            if bot is None:
                self.msg_channel(c, "cannot find %s in bot_list" % campaign_type)
                return
            # post single campaign
            bot.post_campaign(self.shorten(campaign_url))

    def get_bot(self, name):
        bot = None
        names = [b.name for b in self.bot_list]
        if name in names:
            bot = self.bot_list[names.index(name)]
        return bot

    def shorten(self, url):
        payload = {'longUrl': url + "?" + self.random_char(5)}
        headers = {'content-type': 'application/json'}
        r = requests.post(self.post_url, data=json.dumps(payload), headers=headers)
        if 'id' in r.text:
            return json.loads(r.text)['id'].rstrip()
        else:
            return 'error processing ' + url
