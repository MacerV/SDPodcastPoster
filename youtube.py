# Import Modules
import re, datetime, time, os, sys 	#standard modules
import json		 		# https://docs.python.org/3/library/json.html
import logging			# https://docs.python.org/3/library/logging.html

import praw 		# reddit api wrapper: https://praw.readthedocs.io/en/latest/
import apiclient 	# google's API 

def configure_logging():
	''' A straight forward logging configuration: 
			Console: INFO and up notifcations, with truncated messages. 
			File   : Complete debug information.
	'''
	silent_console = False
	handlers = []

	file_handler = logging.FileHandler('SDBotcast.log', encoding= 'utf-8')
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
	## Initilization?
	configure_logging()
	youtube_log = logging.getLogger('SDBotcast.Youtube')
	with open("config.json", 'r') as f:
		last_video_id = json.load(f)["last_video_id"]
	youtube_log.info("Youtube Video checker started")

	# Grab private keys from file.
	with open("keys.json", 'r') as f:
		keys = json.load(f)
		reddit_keys = keys['reddit_keys'] 
		API_KEY = keys["google_keys"]["API_KEY"]

	# get youtube response of most recent video from channel(playlistId)
	youtube = apiclient.discovery.build('youtube', 'v3', developerKey=API_KEY, cache_discovery=False) 		# Their cache discovery thing is broke
	request = youtube.playlistItems().list(part="id,contentDetails", playlistId = "UUkUjSzthJUlO0uyUpiJfnxg" )
	response = request.execute()
	latest_video_id = response['items'][0]['contentDetails']['videoId']

	# Check if video is new.
	if latest_video_id != last_video_id:
		youtube_log.info(f"New Steve Dangle Video {latest_video_id}")
		
		#Connecting to reddit
		reddit_dev = praw.Reddit(	client_id		= reddit_keys['client_id'], 
									client_secret 	= reddit_keys['client_secret'], 
									user_agent		= reddit_keys['user_agent'], 
									username		= reddit_keys['username'], 
									password		= reddit_keys['password'])
		reddit_dev.validate_on_submit = True 
		
		# Get details and post to reddit.
		LFR = youtube.videos().list(part="snippet",id=f"{latest_video_id}").execute()
		LFR_title = f"[Steve Dangle] {LFR['items'][0]['snippet']['title']}"
		LFR_link = f"https://www.youtube.com/watch?v={latest_video_id}"
		LFR_post = reddit_dev.subreddit("SteveDangle").submit(LFR_title, url=LFR_link)
		
		# If there is a duplicate then just delete this post, and move on.
		for duplicate in LFR_post.duplicates():
			LFR_post.delete()
			break

		# Save the last_video_id to the config.
		with open("config.json", 'r') as f:
			config = json.load(f)
		config["last_video_id"] = latest_video_id
		with open("config.json", "w") as file_Object:
			json.dump(config, file_Object, indent = 4)


if __name__ == '__main__':
	main()
