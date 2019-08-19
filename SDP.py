# importing time, webreading, and reddit/twitter APIs
from __future__ import print_function
import datetime
import time
import praw
import feedparser
import unicodedata
import requests
import json
import re
import time
import pprint
import threading
import re


class User:
	def __init__(self, platform, *args):
		# creates a base user with a specified platform. 
		# 	if the user is a developer they  if they are a developer it'll take a dict of
		# key word arguments for secrets, keys, passwords.
		self.platform = platform
		self.isDev = False
		if args is not None:
			self.isDev = True
			for key, val in args[0].items() : #for some reason it gets turned into a list???
				#print("Key is : " + key + ", with a value of: " + val)
				setattr(self, key, val)
	def establish_api_connection(self):
		# Establishes a connection through the praw api for this dev.
		self.reddit_api = praw.Reddit(client_id=self.client_id, client_secret=self.client_secret,
									  user_agent=self.user_agent, username=self.username, password=self.password)
		return self.reddit_api
	def create_post(self, api, post_type, text_or_URL, title, subreddit, stickey=False, sort='new'):
		# creates a post through the developer connection with additional commonly used options (sticky/sort)
		if post_type == "text":
			self.thread = self.reddit_api.subreddit(
				subreddit).submit(title, selftext=text_or_URL)
		elif post == "link":
			self.thread = self.reddit_api.subreddit(
				subreddit).submit(title, url=text_or_URL)
		if stickey:
			self.thread.mod.sticky()
		if sort != "new":
			self.thread.mod.suggested_sort(sort=sort)
		return self.thread
	def comment_reply(self, comment, reply_text):
		##Still in development
		comment.reply(reply_text)
	def is_dev(self):
		# Returns whether the user is a developer or not
		return self.isDev
class RedditDev(User):
	def __init__(self, reddit_keys):
		# Creates a reddit developer instance. Requries username, password, client id, client secret, & user agent
		User.__init__(self, 'Reddit', reddit_keys)
		self.isDev = True
	def create_sticky_post(self, api, post_type, Text_or_URL, title, subreddit, stickey=True, sort='new'):
		if post_type == "text":
			thread = self.reddit_api.subreddit(
				subreddit).submit(title, selftext=Text_or_URL)
		elif post_type == "link":
			thread = self.reddit_api.subreddit(
				subreddit).submit(title, url=Text_or_URL)
		if stickey:
			thread.mod.sticky()
		if sort != "new":
			thread.mod.suggested_sort(sort=sort)
		return thread

def add_to_log(message):
	#this could also print out to a log eventually, but for now its just for simplying the messages being printed to the screen
	print(str(datetime.datetime.now()) + " | " + message)
def get_podcast_data(rss_feed):
	#requries feedparser
	cast = feedparser.parse(rss_feed).entries[0]

	title = cast['title']
	duration = cast['itunes_duration']
	published = cast['published']
	published = datetime.datetime.strptime(published[:len(published)-len(' +0000')], '%a, %d %b %Y %H:%M:%S')
	sc_link = cast['links'][0]['href']
	summary = cast['summary']
	return { "title": title, 
		"duration": duration,
		"published": published,
		"sc_link": sc_link,
		"summary": summary}

def init():
	print("----------------------------------------------------------------------------")
	add_to_log("Initialize | DANGLE-PI! Started. Loading Settings.")
	#Try Loading Program Settings
	try:
		key_file = 'keys.json'
		with open(key_file, 'r') as f:
			keys = json.load(f)
		reddit_keys = keys['reddit_keys'] #should return a dict of reddit keys
	except Exception as e:
		add_to_log("Initialize | Error importing config file. Likely missing or outdated values. Exiting Program.")
		add_to_log("Initialize | Main error follows: " + str(e))
		exit()

	# Creating Instance of Reddit Users
	try:
		reddit_user = RedditDev(reddit_keys)
		reddit_connect = reddit_user.establish_api_connection()
		add_to_log("Initialize | Connected to Reddit")
	except Exception as e:
		add_to_log("Initialize | Initialize | Error connecting to Reddit. Exiting Program.")
		add_to_log("Initialize | Main error follows: " + str(e))
		exit()

	#if everything is running according to plan it can now execute the main program loop.
	main(reddit_user, reddit_connect)
def main(r_user, r_con):
	#Assigning threads
	pc_thr = threading.Thread(target = new_pc,args = (r_user, r_con))  # check if a new podcast is up
	rcom_thr = threading.Thread(target = new_coms,args = (r_user, r_con) ) # look for new commands and execute

	#Starting  threads
	pc_thr.start()
	rcom_thr.start()


def new_pc(reddit_dev, reddit_connect):
	config_file	= "config.json"
	with open(config_file, 'r') as f:
		config = json.load(f)
	sleep_Interval = config['program_data']['sleep_Interval']
	last_podcast_date = config['program_data']['last_podcast_date']
	rss_feed = config['program_data']['rss_feed']


	while True:
		add_to_log("SDP-Poster | Reading RSS feed for new podcast information. ")
		new_podcast_data = get_podcast_data(rss_feed)

		# if the last registered podcast is not the same as the last podcast then we'll have a new podcast!
		if last_podcast_date != str(new_podcast_data['published']):
			#convert podcast data back into variables 
			#Note: tried k, v in dict.items but its not working here for some reason
			title = new_podcast_data['title']
			duration = new_podcast_data['duration']
			published = new_podcast_data['published']
			sc_link = new_podcast_data['sc_link']
			summary = new_podcast_data['summary']

			#Updates the config file with the new podcast date.
			with open(config_file, 'w') as file_Object:
				config['program_data']['last_podcast_date'] = str(published)
				json.dump(config,file_Object, indent=4)

			#Generate the post submission text.
			yt_link = re.search("https://youtu\.be/.{11}",new_podcast_data['summary']).group() #searches the cast summary data for the youtube shortlink that Jesse puts there.
			selftext = f"New SteveDangle Podcast! \n\nTitle: {title} \n\nDuration: {duration}\n\n[SoundCloud]({sc_link}) \n\n[Itunes](https://itunes.apple.com/ca/podcast/steve-dangle-podcast/id669828195?mt=2) \n\n[Youtube]({yt_link}) \n\n"
			title = f"The Steve Dangle Podcast - {title}"

			# podcastpost = reddit_dev.create_post(reddit_connect, "text",selftext, title, subreddit, True, "new")
			add_to_log(f"SDP-Poster | New podcast available! {title}. Sleeping for 24 hours.")
			time.sleep(24*60*60)
		else:
			add_to_log(f"SDP-Poster | No new podcast available.")

		time.sleep(sleep_Interval)


def new_coms(reddit_user, reddit_connect):
	try:
		bot_command_string = "SDPBOT!"
		for comment in reddit_connect.subreddit('SteveDangle').stream.comments():
			if bot_command_string in comment.body:
				add_to_log("Com-Search | New command found.")
				command_string = comment.body[comment.body.find(bot_command_string):]
				if (bot_command_string + " Favourite") in command_string:
					timestamptext = re.search("(\d\d:\d\d|\d:\d\d:\d\d)",command_string).group()
					timestamp = datetime.datetime.strptime(timestamptext,"%H:%M:%S")

					submissionText = comment.submission.selftext
					
					#confirm time within duration
					duration = re.search("Duration: \d\d:\d\d:\d\d", submissionText).group()
					duration = datetime.datetime.strptime(duration[11:],"%H:%M:%S")
					

					PodcastLink =  submissionText[submissionText.find('[')+13:submissionText.find(')')]
					SoundCloudLink = str(PodcastLink) + str("#t=") + str(timestamp)
					
					if (timestamp > duration):
						add_to_log("Com-Search | Invalid timestamp provided. Informating user.")
						reddit_user.comment_reply(comment,"Invalid timestamp. Timestamp exceeds podcast duration.")
					else:
						favourite_submission = { "name" : comment.author.name, "link": SoundCloudLink }	
						favourites_log = "favourites.json"
						with open(favourites_log, "r") as file_Object:
							data = json.load(file_Object)
							data["Favourite Comments"].append(favourite_submission)
						with open(favourites_log, "w") as file_Object:
							json.dump(data, file_Object, indent = 4)
						
						reddit_user.comment_reply(comment,"Adding [SoundCloudLink](" + SoundCloudLink + ") to the pile of favourites.")
						add_to_log("Com-Search | Adding new submission to favourites list.")
	except Exception as e:
		#this should only really happen in times where a connection is lost, so reconnect and call again
		reddit_connect = reddit_user.establish_api_connection()
		new_coms(reddit_user,reddit_connect)



if __name__ == '__main__':
	init()
