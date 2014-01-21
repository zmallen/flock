import irc.bot
import irc.strings
import json
import syslog
import requests 

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

    def on_privmsg(self, c, e):
        self.do_command(e, e.arguments[0])

    def msg_channel(self, c, msg):
        if(len(msg) > 512):
            for chunk in self.chunk_msg(msg):
                print 'chunk: ' + str(len(chunk)) + " ->" + chunk
                c.privmsg(self.channel, chunk)
        else:
            c.privmsg(self.channel, msg)
    # need a lazy generator here because irc wont take anything over 512 bytes / message        
    def chunk_msg(self, msg):
        for i in xrange(0, len(msg), 512):
            yield msg[i:i+512]

    def on_pubmsg(self, c, e):
        a = e.arguments[0].split(" ")
        if a[0] == "?botlist":
            msg = ''.join([b.name for b in self.bot_list])
            self.msg_channel(c, msg)
        elif a[0] == "?shorten":
             if len(a) == 2:
                url = a[1]
                self.msg_channel(c, self.shorten(url))
        elif a[0] == "?campaign":
            self.make_campaign(c, a)
        elif a[0] == "?gettrends":
            self.msg_channel(c, str(self.bot_list[0].get_global_trends()))

    def make_campaign(self, c, msg):
        campaign = msg
        #?campaign all|botname url
        if(len(campaign) != 3):
            c.privmsg(self.channel, "usage: ?campaign all|botname url")
            return
        campaign_type, url = campaign[1], campaign[2]
        # if its a campaign for all the bots this bot controls, generate a short url for each one
        if campaign_type == "all":
            c.privmsg(self.channel, "starting all..")
        else:
            # if its for a specific bot name, then check to see if this bot has that handle authenticated, then work
            if campaign_type not in self.bot_list:
                c.privmsg(self.channel, "cannot find %s in bot_list" % campaign_type)
                return

    def shorten(self, url):
        payload = {'longUrl': url}
        headers = {'content-type': 'application/json'}
        r = requests.post(self.post_url, data=json.dumps(payload), headers=headers)
        if 'id' in r.text:
            return json.loads(r.text)['id'].rstrip()
        else:
            return 'error processing ' + url
