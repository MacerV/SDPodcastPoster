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



### Helper Functions
def load_json(file):		   # Return the raw json string from file
	with open(file, 'r') as f:
		return json.load(f)
def dump_json(file,data):		   # Dump raw json string to json file
	with open(file, "w") as file_Object:
		json.dump(data, file_Object, indent = 4)

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
	comment_log = logging.getLogger('SDBotcast.Commands')
	reddit_keys = load_json("keys.json")['reddit_keys'] 
	reddit_dev = praw.Reddit(		client_id		= reddit_keys['client_id'], 
									client_secret 	= reddit_keys['client_secret'], 
									user_agent		= reddit_keys['user_agent'], 
									username		= reddit_keys['username'], 
									password		= reddit_keys['password'])

	
	def __init__(self):
		super(bot_commands, self).__init__()
		self.shutdown_flag = threading.Event()
		self.comment_log.info("Comment command searching thread started")

	def run(self):
		while not self.shutdown_flag.is_set():
			for comment in self.reddit_dev.subreddit('SteveDangle').stream.comments(skip_existing=False):
				self.comment_log.debug(f"New Comment: {comment.body[:50]}...") 
				for command in self.COMMAND_STRINGS:		
					regex = re.search(command,comment.body)

					if regex is not None:
						if (regex.re.pattern == COMMAND_STRINGS["Favourite"]):
							reply_text = __BOT_Submit_Favourite(comment,regex)	 
						elif (regex.re.pattern == COMMAND_STRINGS["Hotdog"]):
							reply_text = __BOT_Is_A_Hotdog_A_Sandwhich()
						elif (regex.re.pattern == COMMAND_STRINGS['SoftMotherfucker']):
							reply_text = "Don't be an @SoftMotherFucker!"
						#elif (regex.re.pattern == COMMAND_STRINGS['']):
						#elif (regex.re.pattern == COMMAND_STRINGS['']):
						self.comment_log.info("Reply Text prepared: {reply_text}")
						self.comment_log.debug(f"Command Processed. \n\nCommand: {command}. Comment: {comment}")
						comment.reply(reply_text)
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
				favourites_log = load_json('favourites.json')
				favourites_log["Favourite Comments"].append(favourite_submission)
				dump_json('favourites.json',favourites_log)
				
				reply_text = f"Adding [SoundCloudLink]({SC_Link}) to the pile of favourites."
		except Exception as e: 
			reply_text = f"Exception while parsing timestamp {e}."
		return reply_text

	def __BOT_Is_A_Hotdog_A_Sandwhich(self):
		hotdogs = [
					"a hotdog a sandwhich","cereal soup", "ketchup a jam", 
					"ketchup a jelly", "pizza thin lazagna"
					]
		random_index = random.randrange(len(hotdogs))
		reply_text = f"I don't know, is {hotdogs[random_index]}?"
		return reply_text

class bot_podcasts(threading.Thread):
	'''This function's main purpose is check every x minutes to see 
		if a new podcast is available to be posted to Reddit.

		It'll grab the latest podcast data and if the datetime doesn't
		matches the last known podcast date then it'll make a new
		post!
	'''	
	podcast_log = logging.getLogger('SDBotcast.Poster')
	config = load_json("config.json")
	reddit_keys = load_json("keys.json")['reddit_keys'] 
	reddit_dev = praw.Reddit(	client_id		= reddit_keys['client_id'], 
								client_secret 	= reddit_keys['client_secret'], 
								user_agent		= reddit_keys['user_agent'], 
								username		= reddit_keys['username'], 
								password		= reddit_keys['password'])


	def __init__(self):
		super(bot_podcasts, self).__init__()
		self.shutdown_flag = threading.Event()


		self.podcast_log.info("Podcast Check thread started")

	def run(self):
		while not self.shutdown_flag.is_set():
			try: 
				# Get data of latest podcast, and format date to datetime.
				cast = feedparser.parse(self.config['rss_feed']).entries[0]
				episode_data = {k: cast[k] for k in ('id','title', 'published','link','itunes_duration','summary')}
				episode_data['published'] = datetime.datetime.strptime(episode_data['published'],'%a, %d %b %Y %H:%M:%S %z')


				if self.config['last_cast_dt'] == str(episode_data['published']):
					self.podcast_log.info("RSS Reviewed: No new podcast available.")
				else:   
					self.podcast_log.info("RSS Reviewed: New podcast available. Processing")
					post_title = f"The Steve Dangle Podcast - {episode_data['title']}"

					it_link = "https://itunes.apple.com/ca/podcast/steve-dangle-podcast/id669828195?mt=2"
					yt_link = re.search("https://youtu\.be/.{11}", episode_data['summary']).group()		 	 # YT vid id is 11 chars
					selftext =  textwrap.dedent(f"""\
									New SteveDangle Podcast!
									
									Title: {episode_data['title']}

									Duration: {episode_data['itunes_duration']}
									
									[SoundCloud]({episode_data['link']})
									
									[Itunes]({it_link})
									
									[Youtube]({yt_link})

									To submit a favourite SDP moment, comment: SDBotcast! Favourite (timetamp in HH:MM:SS format)""")
					
					# post the podcast to reddit & save to config.
					podcastpost = self.reddit_dev.subreddit("SteveDangle").submit(post_title, selftext = selftext)
					podcastpost.mod.sticky()
					podcastpost.mod.suggested_sort(sort='new')

					self.config['last_cast_dt'] = str(episode_data['published'])
					dump_json("config.json",self.config)

					time.sleep(36*60*60)  # Podcasts never < 48 hours apart
				
				# Go to sleep for a set time depending on time of day.
				time.sleep(self.__calculate_sleeptime(self.config['sleep_Interval']))
			except Exception as e:
				self.podcast_log.error(f"RSS reading error. Error: {e}")
				time.sleep(900)
				continue



	def __calculate_sleeptime(self, sleep_Interval, tm = 1):
		''' This function provides a sleep time based on the current hour.  
			Historicially less probably posting times have larger sleep intervals. 
			
			Future Feature: Kernal Density Estimation based calculation.
		'''
		ch = datetime.datetime.now().hour
		if (ch == 23):			   tm = 1  #  11 PM				- 5   min
		elif(ch==0 or ch >= 22):   tm = 2  # 0-1 AM, 10-11PM  	- 10  min
		elif(ch <= 2 or ch >= 20): tm = 3  # 1-2 AM, 8-10PM		- 15  min
		elif(ch >= 17 or ch <4):   tm = 6  # 2-4 AM, 5-8PM	 	- 30  min
		else:					   tm = 24 # Off-Peak hours		- 120 min
		return tm*sleep_Interval

class bot_youtube(threading.Thread):

	youtube_log = logging.getLogger('SDBotcast.Youtube')
	last_video_id = load_json("config.json")["last_video_id"]
	API_KEY = load_json("keys.json")["google_keys"]["API_KEY"]
	reddit_keys = load_json("keys.json")['reddit_keys'] 
	reddit_dev = praw.Reddit(	client_id		= reddit_keys['client_id'], 
								client_secret 	= reddit_keys['client_secret'], 
								user_agent		= reddit_keys['user_agent'], 
								username		= reddit_keys['username'], 
								password		= reddit_keys['password'])

	def __init__(self):
		super(bot_youtube, self).__init__()
		self.shutdown_flag = threading.Event()
		self.youtube_log.info("Youtube Video checker started")


	def run(self):
		while not self.shutdown_flag.is_set():
			# get youtube response
			youtube = apiclient.discovery.build('youtube', 'v3', developerKey=bot_youtube.API_KEY, cache_discovery=False) 		# Their cache discovery thing is broke
			request = youtube.playlistItems().list(part="id,contentDetails", playlistId = "UUkUjSzthJUlO0uyUpiJfnxg" )
			response = request.execute()
			latest_video_id = response['items'][0]['contentDetails']['videoId']

			# Check if video is new.
			if latest_video_id != bot_youtube.last_video_id :
				youtube_log.info(f"New Steve Dangle Video {latest_video_id}")
				bot_youtube.last_video_id = latest_video_id


				# Get details and post to reddit.
				LFR = youtube.videos().list(part="snippet",id=f"{latest_video_id}").execute()
				LFR_title = f"[Steve Dangle] {LFR['items'][0]['snippet']['title']}"
				LFR_link = f"https://www.youtube.com/watch?v={self.latest_video_i}"
				youtube_video = self.reddit_dev.subreddit("SteveDangle").submit(LFR_title, url=LFR_link)


				# Save the last_video_id to the config.
				config = load_json("config.json")
				config["last_video_id"] = latest_video_id
				dump_json("config.json",config)


			time.sleep(1800)  	# 30 minutes
		


  


def configure_logging():
	''' A straight forward logging configuration: 
			Console: INFO and up notifcations, with truncated messages. 
			File   : Complete debug information.
	'''
	file_handler = logging.FileHandler('logfile.log', encoding= 'utf-8', mode='w')
	file_handler.setLevel(logging.DEBUG)
	console_handler = logging.StreamHandler()
	console_handler.setLevel(logging.INFO)
	console_handler.setFormatter(logging.Formatter(fmt='%(asctime)s | %(name)-18.18s | %(levelname)-4s | %(message)-72s'))	

	# Configure logging using the handlers. 
	logging.basicConfig(
		handlers=[file_handler,console_handler],
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
