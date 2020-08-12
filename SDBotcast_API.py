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




class bot_commands(threading.Thread):
	'''Searches each comment for every command string, and calls all 
		helper function based on the index of the regular expression(s)
		which was successful.

	'''
	COMMAND_STRINGS = {
		"Favourite" :	"(SDBotcast! Favourite|Favorite|favourite|favorite) (\d\d:\d\d:\d\d|\d:\d\d:\d\d)",
		"Hotdog" 	:	"(?:^|(?<=[.?!])) ?(?:IS|Is|is) ?a? ([a-zA-Z]{3,16}) ?a? ([a-zA-Z]{3,16})\?",
		"SoftMotherfucker" : "(?i)@ ?soft ?mother ?fucker"
	}

	
	# Connect to reddit and all that jazz.
	def __init__(self):
		super(bot_commands, self).__init__()
		self.comment_log = logging.getLogger('SDBotcast.Commands')
		self.shutdown_flag = threading.Event()

		with open("keys.json", 'r') as f:
			self.reddit_keys = json.load(f)['reddit_keys'] 
		self.reddit_dev = praw.Reddit(	client_id		= self.reddit_keys['client_id'], 
										client_secret 	= self.reddit_keys['client_secret'], 
										user_agent		= self.reddit_keys['user_agent'], 
										username		= self.reddit_keys['username'], 
										password		= self.reddit_keys['password'])
		self.comment_log.info("Comment command searching thread started")

	# Main execution loop, checking if new commands have been made in the comments. 
	#		Should run continually using praw's own sleep logic.
	#
	# 		Note: this could get computationally heavy using the current method 
	#		In the future it may be advisable to have only do commands using the SDBotcast! or /u/SDBotcast call
	def run(self):
		while not self.shutdown_flag.is_set():
			for comment in self.reddit_dev.subreddit('SteveDangle').stream.comments(skip_existing=False):
				self.comment_log.debug(f"New Comment: {comment.body[:50]}...") 
				for command in self.COMMAND_STRINGS:		
					regex = re.search(command,comment.body)

					# Check for specific command strings and if there execute the command.
					if regex is not None:
						if (regex.re.pattern == COMMAND_STRINGS["Favourite"]):
							reply_text = __BOT_Submit_Favourite(comment,regex)	 
						elif (regex.re.pattern == COMMAND_STRINGS["Hotdog"]):
							reply_text = __BOT_Is_A_Hotdog_A_Sandwhich()
						elif (regex.re.pattern == COMMAND_STRINGS['SoftMotherfucker']):
							reply_text = "Don't be an @SoftMotherFucker!"
						#elif (regex.re.pattern == COMMAND_STRINGS['']):
						#elif (regex.re.pattern == COMMAND_STRINGS['']):
						#elif (regex.re.pattern == COMMAND_STRINGS['']):
						#elif (regex.re.pattern == COMMAND_STRINGS['']):
						#elif (regex.re.pattern == COMMAND_STRINGS['']):
						#elif (regex.re.pattern == COMMAND_STRINGS['']):
						self.comment_log.info("Reply Text prepared: {reply_text}")
						self.comment_log.debug(f"Command Processed. \n\nCommand: {command}. Comment: {comment}")
						comment.reply(reply_text)

			# If this stuff is run it means the praw logic got broken, so this will log the error, 
			# 		and essentially restart the call to PRAW to get comments again.
			self.comment_log.error("Praw comment stream exited, rebooting in 5 minutes.")
			time.sleep(300)	 	# sleeping 5 minutes to hopefully allow the connection to reboot or whatever error to solve itself


	def __BOT_Submit_Favourite(self, comment, regex):
		'''Favourite submissions are submitted by users of /r/SteveDangle.
			They usea command string including a timestamp which is found
			by the regex. 

			This procedure takes the favourited timestamp and pushes a
			timestamped soundcloud link with other information to 
			a favourites.json file for later observation.

		'''
		# Grab the SoundCloud link and Duration from post text. 
		# group() & group(1) is full match, group(20)
		post_text = comment.submission.selftext
		SC_Link =  re.search("\[SoundCloud\]\((.+)\)",post_text).group(1)	
		duration = datetime.datetime.strptime(re.search("Duration: (\d\d:\d\d:\d\d)", post_text).group(1),"%H:%M:%S")
		reply_text = ""

		try:
			# Try and parse timestamp and push data to favourites.json		 
			timestamp = datetime.datetime.strptime(regex.group(2),"%H:%M:%S")
			if (timestamp > duration):
				reply_text("Timestamp exceeds podcast duration, try again.")
			else:
				favourite_submission = { 
					"name" : comment.author.name, 
					"posting_time" : comment.created_utc,
					"comment_id" : comment.id,
					"comment_body" : comment.body,
					"link": f"{SC_Link}#{regex.group(2)}"
				}

				# Append new favourite to favourites
				with open('favourites.json', 'r') as f:
					favourites_log = json.load(f)
				favourites_log["Favourite Comments"].append(favourite_submission)
				with open('favourites.json', "w") as file_Object:
					json.dump(favourites_log, file_Object, indent = 4)

				reply_text = f"Adding [SoundCloudLink]({SC_Link}) to the pile of favourites."
		except Exception as e: 
			reply_text = f"Exception while parsing timestamp {e}."
		return reply_text

	def __BOT_Is_A_Hotdog_A_Sandwhich(self):
		hotdogs = [
					"a hotdog a sandwhich","cereal soup", "ketchup a jam", 
					"ketchup a jelly", "pizza thin lazagna", 
					"two stacked lazagnas two seperate lazagnas or one big lazagna"
					]
		random_index = random.randrange(len(hotdogs))
		reply_text = f"I don't know, is {hotdogs[random_index]}?"
		return reply_text

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
	commands_thread = bot_commands() 	
	commands_thread.start()
	commands_thread.join()

	root_log.critical("Rughrohg, the program has stopped.")


if __name__ == '__main__':
	main()
