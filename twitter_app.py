from flask import Flask,redirect
from flask import render_template
from flask import request
from twython import Twython
from redis import Redis


app = Flask(__name__)
r = Redis()

API_KEY = "qrMVReFylFb4aQVqZFfzxw"
API_SECRET = "BcULFEskAWKYMRevP7pNB80eA4K1LnP0HDcbGTTlw"

@app.route("/twitter", methods=["GET"])
def display():
	#Create Twitter API instance	
	twitter = Twython(app_key=API_KEY, app_secret=API_SECRET)
	#Get auth url
	auth = twitter.get_authentication_tokens(callback_url='http://127.0.0.1/twitterfinish')
	#Save off token and secret for later use. Could be saved in cookies.
	r.set("twitter:token", auth['oauth_token'])
	r.set("twitter:secret", auth['oauth_token_secret'])
	#redirect user to auth link
	return redirect(auth['auth_url'])

@app.route("/twitterfinish", methods=["GET"])
def finish():
	#Get verifier from GET request from Twitter
	verifier = request.args['oauth_verifier']
	#Get token and secret that was saved earlier
	token = r.get("twitter:token")
	secret =  r.get("twitter:secret")
	#Create new Twitter API instance with the new credentials
	twitter = Twython(API_KEY, API_SECRET, token, secret)
	#Send new credentials with verifier to get the access_token
	last = twitter.get_authorized_tokens(verifier)
	# get access_key, access_secret & botname to writeout to writeout
	access_key = last['oauth_token']
	access_secret = last['oauth_token_secret']
	twitter2 = Twython(API_KEY, API_SECRET, access_key, access_secret)
	bot_name = twitter2.verify_credentials()['screen_name']
	# write out and update our csv file
	with open("bots.csv", "a") as f:
		f.write("bot=%s,%s,%s,%s,%s" % (bot_name, API_KEY, API_SECRET, access_key, access_secret))

	#Display access_token and access_token_secret
	#return "Token: %s <br> Secret: %s" % (last['oauth_token'], last['oauth_token_secret'])
	return "%s" % (last)

if __name__ == '__main__':
    app.run(debug=True, port=80)
