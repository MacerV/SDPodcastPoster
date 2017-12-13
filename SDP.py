#importing time, webreading, and reddit/twitter APIs
from __future__ import print_function
import datetime
import time
import praw
import feedparser
import unicodedata
import requests

import pprint

from keys import *

class User:
	def __init__(self,platform,**kwargs):
		# creates a base user with the specified platform 
		# and if they are a developer it'll take a dict of 
		# key word arguments for secrets, keys, passwords.
		self.platform = platform
		self.isDev = False
		if kwargs is not None:
			self.isDev = True
			for key,val in kwargs.items():
				# print("Key is : " + key + ", with a value of: " + val)
				setattr(self,key,val)
	def is_dev(self):
		#Returns whether the user is a developer or not
		return self.isDev

class RedditDev(User):
	def __init__(self,**kwargs):
		#Creates a reddit developer instance. Requries username, password, client id, client secret, & user agent
		User.__init__(self,'Reddit',**kwargs)
		self.isDev = True
	def establish_api_connection(self):
		reddit_api = praw.Reddit(client_id=self.client_id,client_secret=self.client_secret,user_agent=self.user_agent,username=self.username,password=self.password)
		return reddit_api
	def create_post(self,api,post_type,Text_or_URL,title,subreddit,stickey=False,sort='new'):
		if post_type == "text":
			thread = reddit_connect.subreddit(subreddit).submit(title,selftext=selftext)
		elif post_type == "link":
			thread = reddit_connect.subreddit(subreddit).submit(title,url=text_or_URL)
		if stickey:
			thread.mod.sticky()
		if sort != "new":
			thread.mod.suggested_sort(sort=sort)		
		return thread


def getStringAfterString(search,str1,str2,x=1):
	#find the first string, then search for the xth instance of the 2nd
	#required libraries
	#	re
	search = search[search.find(str1):]
	index = [m.start() for m in re.finditer(search,str2)][0] #index 2 is third occurrence 
	string = search[index:index+len(str2)]
	
	return String
	
# Creating Instance of Twitter Users, and connect to twitter through API
# twitter_user = TwitterDev('MacerV', 'tSpHLSbHtohFnNhkm4THqRITP', 'PAExPZI5GYDR6KQWZc5Ac9QxUFUPF2nLkmDXhhjQOwfmCFQotf','977625156-rE3KQ1VB4nk4yD7AxbHu8AvNVLXgjkkmf8OJ6Osm', 'Y68yLYZG26gZ90sKK3CAIXo33xCrasP7lbHUmtApI2dJB')
# twitter_target = TwitterUser('JesseBlake')
# twitter_connect = twitter_user.establish_api_connection()
reddit_user = RedditDev(**redditkeys)
reddit_connect = reddit_user.establish_api_connection()

# Itunes SDP
## Itunes API is shit and doesn't work for podcasts like at all
# https://itunes.apple.com/ca/podcast/steve-dangle-podcast/id669828195?mt=2#




#Sound Cloud search
SoundCloud = 'https://soundcloud.com/steve-dangle-podcast'
page = requests.get(SoundCloud)
html = page.text
text = html.encode('utf-8')
TrackLocation = text.find("itemprop=\"track\"")
StreamLocation = text.find("itemprop=\"url\"",TrackLocation)
Href =  text.find("href=\"",StreamLocation)
EndHref = text.find("\"",Href+6)
PodcastLink = text[Href+6:EndHref]
FullSCLink = "https://soundcloud.com" + PodcastLink
print("Most Recent Podcast Link: " + FullSCLink)
	

#reads soundcloud 
url = 'http://feeds.feedburner.com/stevedanglepodcast'
page = feedparser.parse(url)



podcastTitle = unicodedata.normalize('NFKD', page.entries[0]["title"]).encode('ascii','ignore')
publishedDate = unicodedata.normalize('NFKD', page.entries[0]["published"]).encode('ascii','ignore')
publishedDate = publishedDate[:len(publishedDate)-len(' +0000')]

newestPodcast = datetime.datetime.strptime(publishedDate, '%a, %d %b %Y %H:%M:%S')

#Starting to ad-hoc this a bit. Opens the ics calendar file and just checks to see if there is a game
file_name = "C:\Users\Mason\Documents\Projects\SDP\lastchecked.txt"

with open(file_name) as file_Object:
	lastPodcast = file_Object.read()	
file_Object.closed

if lastPodcast != publishedDate:
	# New Podcast is out!!!
	print("This is a new podcast.")
	with open(file_name, 'w') as file_Object:
		 file_Object.write(publishedDate)
	file_Object.closed
	
	
# Jesse_tweets = twitter_target.get_tweets(twitter_connect,since_id=lastTweetID)
# # Jesse_tweets = twitter_target.get_tweets(twitter_connect,num_of_tweets=10)

	
# #Looks for the first instance of a podcast tweet and stops (so no triple posting by accident
# for tweet in Jesse_tweets:
	# if tweet.text.find("Pod")>-1:
		# # print("FOUND A PODCAST MOTHERFUCKER!")
		# try:
			# podcastlink = tweet.text[tweet.text.find("https"):tweet.text.find("https")+23]
			
			# selftext = "New Steve Dangle Podcast \n "
			# title = "Steve Dangle Podcast - " + d.datetime.strftime('%b %d, %Y')
			# subreddit = "stevedangle"
			
			# print(title)
			
			# # podcastpost = RedditDev.create_post(reddit_connect,"text",selftext,title,subreddit,True,"new")
			# break

		# except:
			# print("Must not be a podcast")

# with open(file_name,'w') as file_Object:
	# lastTweetID = Jesse_tweets[1].id
	# file_Object.write(lastTweetID)
# file_Object.closed


	SoundCloud = "[SoundCloud](https://soundcloud.com/steve-dangle-podcast) \n"
	ITunes = "[Itunes](https://itunes.apple.com/ca/podcast/steve-dangle-podcast/id669828195?mt=2) \n"
	Youtube = "[Youtube](https://www.youtube.com/channel/UC0a0z05HiddEn7k6OGnDprg/videos) \n"

	selftext = "New Steve Dangle Podcast : " + podcastTitle + "\nLinks:\n" + SoundCloud + ITunes + Youtube
	# print(selftext) 
	
	
	title = "The Steve Dangle Podcast - " + podcastTitle
	subreddit = "stevedangle"
						
	podcastpost = reddit_user.create_post(reddit_connect,"text",selftext,title,subreddit,True,"new")




