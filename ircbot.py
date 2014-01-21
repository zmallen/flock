import irc.bot
import irc.strings
import json
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

    # check here for campaign
    def on_pubmsg(self, c, e):
        a = e.arguments[0].split(" ")
        if a[0] == "?botlist":
            msg = ''.join([b.name for b in self.bot_list])
            c.privmsg(self.channel, msg)
        elif a[0] == "?shorten":
             if len(a) == 2:
                url = a[1]
                c.privmsg(self.channel, self.shorten(url))

    def shorten(self, url):
        payload = {'longUrl': url}
        headers = {'content-type': 'application/json'}
        r = requests.post(self.post_url, data=json.dumps(payload), headers=headers)
        if 'id' in r.text:
            return json.loads(r.text)['id'].rstrip()
        else:
            return 'error processing ' + url
