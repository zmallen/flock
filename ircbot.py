import irc.bot
import irc.strings
import json
import syslog
import requests 
import gevent
import string
import random
import syslog
from random import randint
import greenclock
from datetime import datetime, time, date
from TwitterAPI import TwitterAPI

class IrcNodeHead(irc.bot.SingleServerIRCBot):

    def __init__(self, channel, nickname, server, port, bot_list):
        irc.bot.SingleServerIRCBot.__init__(self, [(server, port)], nickname, nickname)
        self.nickname = nickname
        self.channel = channel
        self.post_url = "https://www.googleapis.com/urlshortener/v1/url"
        self.bot_list = bot_list
        # if its a weekday, tweet between 9 and 5 for a total of 5 times
        # if its a weekend, tweet between 12 and 10 for a total of 7 times
        self.scheduled_tweets = { 'weekday': { 'num_tweets':5, 'times':[8,17] }, 'weekend': { 'num_tweets':7, 'times':[12,10] } }
        # start scheduler
        scheduler = greenclock.Scheduler(logger_name='flocker')
        scheduler.schedule('tweet_to_look_human', greenclock.every_hour(hour=7, minute=0, second=0), self.look_human)
        scheduler.run_forever(start_at='once')
        # corpus of tweets from the day
        self.twitter_corpus = []
        self.max_tweets = 100

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
                shortened = self.shorten(campaign_url)
                if shortened.startswith('error'):
                    self.msg_channel('error shortening %s -> %s' % (campaign_url, shortened))
                    return
                else:
                    urls.append(shortened)
            # create a dict of tuples of urls to bots
            url_tuples = dict(zip(self.bot_list, urls))
            # asynchronously post to twitter
            jobs = [ gevent.spawn(bot.post_campaign, url) for bot, url in url_tuples.iteritems() ]
            gevent.joinall(jobs, timeout=901)
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
            return 'error %s' % r

    def look_human(self):
        syslog.syslog('Looking human for %s' % self.nickname)
        # build a streamer of a sample of tweets
        self.build_streamer()
        ## schedule each bot to tweet a random tweet pulled from corpus at random specified time depending on if its a weekday or not
        # get todays date
        today = date.today() 
        # get whether its a weekday or weekend
        week_type = self.get_weektime(today.weekday())
        # get minimum datetime and maximum datetime to spawn intervals in between them
        mintime = time(self.scheduled_tweets[week_type]['times'][0], 0)
        mindt = datetime.combine(today, mintime)
        maxtime = time(self.scheduled_tweets[week_type]['times'][1], 0)
        maxdt = datetime.combine(today, maxtime)
        # get each bot, and use gevent to spawn_later tasks based on the week_type with a random tweet
        for bot in self.bot_list:
           intervals = [ self.randtime(mindt, maxdt) for x in xrange(self.scheduled_tweets[week_type]['num_tweets']) ]
           # assign the gevent to spawn_later by mapping each interval generated, find the time delta to determine number of seconds until event
           # and then pull a random tweet from the corpus
           map(lambda time: gevent.spawn_later(time - int(datetime.now().strftime('%s')), bot.tweet, self.get_random_tweet), intervals)
        # reset
        self.twitter_corpus = []

    def randtime(self, mindt, maxdt):
        return randint(int(mindt.strftime('%s')), int(maxdt.strftime('%s')))

    def get_weektime(self, weekdaynum):
       return 'weekday' if weekdaynum < 5 else 'weekend' 

    def build_streamer(self):
        # choose a random bot to get stream from
        bot = random.choice(self.bot_list)
        bot_stream = TwitterAPI(bot.con_k, bot.con_s, bot.acc_k, bot.acc_s)
        # get max_tweets tweets then stop
        for tweet in self.stream(bot_stream):
            self.build_corpus(tweet)
            if len(self.twitter_corpus) >= max_tweets:
                break

    def stream(self, bot_stream):  
        request = bot_stream.request("statuses/sample", {"language":"en:"})
        return request.get_iterator()

    def build_corpus(self, tweet):
        self.twitter_corpus.append(tweet)

    # pull a random one then delete it so we dont duplicate it
    def get_random_tweet(self):
        tweet = random.choice(self.twitter_corpus)
        index = self.twitter_corpus.index(tweet)
        self.twitter_corpus.remove(index)
        return tweet
