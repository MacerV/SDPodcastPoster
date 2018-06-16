#importing time, webreading, and reddit/twitter APIs
from __future__ import print_function
import datetime
import time
import praw
import feedparser
import unicodedata
import requests

import pprint



class User:
	def __init__(self,platform):
		# creates a base user with the specified platform 
		# and if they are a developer it'll take a dict of 
		# key word arguments for secrets, keys, passwords.
		self.platform = platform
		self.isDev = False
	def is_dev(self):
		#Returns whether the user is a developer or not
		return self.isDev

class RedditDev(User):
	isDev = True
	def __init__(self):
		#Creates a reddit developer instance. Requries username, password, client id, client secret, & user agent
		User.__init__(self,'Reddit')
	def establish_api_connection(self):
		self.reddit_api = praw.Reddit(client_id="",client_secret="",user_agent="",username="",password="")
		return self.reddit_api
	def create_post(self,api,post_type,Text_or_URL,title,subreddit,stickey=False,sort='new'):
		if post_type == "text":
			thread = self.reddit_api.subreddit(subreddit).submit(title,selftext=Text_or_URL)
		elif post_type == "link":
			thread = self.reddit_api.subreddit(subreddit).submit(title,url=Text_or_URL)
		if stickey:
			thread.mod.sticky()
		if sort != "new":
			thread.mod.suggested_sort(sort=sort)		
		return thread



def main():	
	currentTime = datetime.datetime.now()
	print(currentTime, end='')  # does sameline print for next statement
	print(": Script started.")
	# Creating Instance of Twitter Users, and connect to twitter through API
	reddit_user = RedditDev()
	reddit_connect = reddit_user.establish_api_connection()
	print("Connected to Reddit")

	#grabs last registered podcast
	file_name = "lastchecked.txt"
	with open(file_name) as file_Object:
		print("Reading Last Podcast Date")
		lastPodcast = file_Object.read()	
	file_Object.closed

	#Over a 8 hour period it will repeatedly check if there's a new more recent podcast.
	# breaks if a new one is found or 8 hours has passed. 
	url = 'http://feeds.feedburner.com/stevedanglepodcast'
	posting_window = 16 #time in hours
	max_Sleep = posting_window*60*60
	while True:
		print("Reading feed until th end of the day or new podcast is found.")
		page = feedparser.parse(url)
		podcastTitle = unicodedata.normalize('NFKD', page.entries[0]["title"])
		publishedDate = unicodedata.normalize('NFKD', page.entries[0]["published"])
		publishedDate = publishedDate[:len(publishedDate)-len(' +0000')]
		# newestPodcast = datetime.datetime.strptime(publishedDate, '%a, %d %b %Y %H:%M:%S')
		
		print(podcastTitle)

		if lastPodcast == publishedDate:
			if max_Sleep > 0:
				print("No new podcast, sleeping for 15 minutes")
				time.sleep(15*60)
				max_Sleep = max_Sleep - 15*60
			else:
				break
		else:
			break

	print("Podcast Feed Analyzed")
	print("Last Registered Podcast: " + lastPodcast)
	print("Most Recent Podcast: " + publishedDate)


	#if the last registered podcast is not the same as the last podcast then we'll have a new podcast!
	if lastPodcast != publishedDate:
		# New Podcast is out!!!
		print("This is a new podcast.")
	
		with open(file_name, 'w') as file_Object:
			file_Object.write(publishedDate)
		file_Object.closed
	
		#Grabbing the podcast link from SoundCloud
		SoundCloud = 'https://soundcloud.com/steve-dangle-podcast'
		page = requests.get(SoundCloud)
		html = page.text
		text = html
		TrackLocation = text.find("itemprop=\"track\"")
		StreamLocation = text.find("itemprop=\"url\"",TrackLocation)
		Href =  text.find("href=\"",StreamLocation)
		EndHref = text.find("\"",Href+6)
		PodcastLink = text[Href+6:EndHref]
		FullSCLink = "https://soundcloud.com" + PodcastLink
		print("Most Recent Podcast Link: " + FullSCLink)
	
	
		#The Podcast Link Text	
		SoundCloud = "[SoundCloud](https://soundcloud.com/steve-dangle-podcast) \n\n"
		ITunes = "[Itunes](https://itunes.apple.com/ca/podcast/steve-dangle-podcast/id669828195?mt=2) \n\n"
		Youtube = "[Youtube](https://www.youtube.com/channel/UC0a0z05HiddEn7k6OGnDprg/videos) \n\n"
	
		selftext = "New Steve Dangle Podcast : " + podcastTitle + "\n\nLinks:\n\n" + SoundCloud + ITunes + Youtube
		# print(selftext) 		
		
		title = "The Steve Dangle Podcast - " + podcastTitle
		subreddit = "stevedangle"

		print(reddit_connect)
		print(selftext+"\n"+title+"\n"+subreddit)
					
		podcastpost = reddit_user.create_post(reddit_connect,"text",selftext,title,subreddit,True,"new")

#script start
main()


