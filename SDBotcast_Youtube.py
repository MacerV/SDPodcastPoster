# Import Modules
import re, datetime, time, os, sys 	#standard modules
import random
import textwrap	 		# standard module for removing trailing idnents in post string
import json		 		# https://docs.python.org/3/library/json.html
import logging			# https://docs.python.org/3/library/logging.html
import threading		# https://docs.python.org/3/library/threading.html

import feedparser  	# rss parser: https://pythonhosted.org/feedparser/
import praw 		# reddit api wrapper: https://praw.readthedocs.io/en/latest/
import apiclient 	# google's API 




class bot_youtube(threading.Thread):
	def __init__(self):
		super(bot_youtube, self).__init__()
		self.youtube_log = logging.getLogger('SDBotcast.Youtube')
		self.shutdown_flag = threading.Event()

		# loading keys and starting up praw connection.
		with open("config.json", 'r') as f:
			self.last_video_id = json.load(f)["last_video_id"]

		with open("keys.json", 'r') as f:
			self.keys = json.load(f)
		self.API_KEY = keys["google_keys"]["API_KEY"]
		self.reddit_keys = keys['reddit_keys'] 
		self.reddit_dev = praw.Reddit(	client_id		= self.reddit_keys['client_id'], 
										client_secret 	= self.reddit_keys['client_secret'], 
										user_agent		= self.reddit_keys['user_agent'], 
										username		= self.reddit_keys['username'], 
										password		= self.reddit_keys['password'])

		self.youtube_log.info("Youtube Video checker started")


	def run(self):
		while not self.shutdown_flag.is_set():
			# get youtube response
			youtube = apiclient.discovery.build('youtube', 'v3', developerKey=self.API_KEY, cache_discovery=False) 		# Their cache discovery thing is broke
			request = youtube.playlistItems().list(part="id,contentDetails", playlistId = "UUkUjSzthJUlO0uyUpiJfnxg" )
			response = request.execute()
			latest_video_id = response['items'][0]['contentDetails']['videoId']

			# Check if video is new.
			if latest_video_id != self.last_video_id :
				self.youtube_log.info(f"New Steve Dangle Video {latest_video_id}")
				self.last_video_id = latest_video_id


				# Get details and post to reddit.
				LFR = youtube.videos().list(part="snippet",id=f"{latest_video_id}").execute()
				LFR_title = f"[Steve Dangle] {LFR['items'][0]['snippet']['title']}"
				LFR_link = f"https://www.youtube.com/watch?v={self.last_video_id}"
				LFR_post = self.reddit_dev.subreddit("SteveDangle").submit(LFR_title, url=LFR_link)
				
				# If there is a duplicate then just delete this post, and move on.
				for duplicate in LFR_post.duplicates():
					LFR_post.delete()
					break

				# Save the last_video_id to the config.
				with open(config.json, 'r') as f:
					config = json.load(f)
				config["last_video_id"] = latest_video_id
				with open(file, "w") as file_Object:
					json.dump(config, file_Object, indent = 4)



			time.sleep(900)  	# 15 minutes
		


  


def configure_logging():
	''' A straight forward logging configuration: 
			Console: INFO and up notifcations, with truncated messages. 
			File   : Complete debug information.
	'''
	silent_console = False
	handlers = []



	file_handler = logging.FileHandler('logfile.log', encoding= 'utf-8', mode='w')
	file_handler.setLevel(logging.DEBUG)
	handlers.append(file_handler)

	if silent_console == False:
		console_handler = logging.StreamHandler()
		console_handler.setLevel(logging.INFO)
		console_handler.setFormatter(logging.Formatter(fmt='%(asctime)s | %(name)-18.18s | %(levelname)-4s | %(message)-72s'))
		handlers.append(console_handler)	

	# Configure logging using the handlers. 
	logging.basicConfig(
		handlers=handlers,
		level = logging.DEBUG,
		format='%(asctime)s | %(name)-32.32s | %(levelname)-8.8s | %(message)s',
		datefmt = '%Y-%m-%d %H:%M:%S'
		)

	# Setting logging level for particularly Verbose loggers.	
	# logging.getLogger("prawcore").setLevel(logging.ERROR)	
	logging.getLogger('googleapiclient.discovery').setLevel(logging.WARNING)


def main():
	''' The main purpose of the script is to execute a growing number of automated tasks for /r/SteveDangle
			- Automaticially post Steve Dangle Podcast Episodes
			- Monitor user comments for favourite submissions & other commands
			- Future: Post SteveDangle videos
	'''
	configure_logging()
	root_log = logging.getLogger('SDBotcast.Root')
	with open('AsciiIntro.txt', 'r',encoding="utf8") as f:
		root_log.info(f.read())
	
	root_log.info("Starting program threads. ")
	podcast_thread = bot_podcasts()
	commands_thread = bot_commands()
	youtube_thread = bot_youtube()
 	
	podcast_thread.start()
	commands_thread.start()
	youtube_thread.start()

	podcast_thread.join()
	commands_thread.join()
	youtube_thread.join()

	root_log.critical("Rughrohg, the program has stopped.")


if __name__ == '__main__':
	main()
