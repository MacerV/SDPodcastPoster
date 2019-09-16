# Import Modules
import re, datetime, time #standard modules
import random
import textwrap	 		# standard module for removing trailing idnents in post string
import json		 		# https://docs.python.org/3/library/json.html
import logging			# https://docs.python.org/3/library/logging.html
import threading		# https://docs.python.org/3/library/threading.html

import feedparser  	# rss parser: https://pythonhosted.org/feedparser/
import praw 		# reddit api wrapper: https://praw.readthedocs.io/en/latest/



### Helper Functions
def load_json(file):		   # Return the raw json string from file
	with open(file, 'r') as f:
		raw_json = json.load(f)
	return raw_json
def dump_json(file,data):		   # Dump raw json string to json file
	with open(file, "w") as file_Object:
		json.dump(data, file_Object, indent = 4)
def calculate_sleeptime(sleep_Interval, tm = 1):
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

### Bot Helper Procedures/Functions
def BOT_Submit_Favourite(comment, regex):
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

def BOT_Is_A_Hotdog_A_Sandwhich():
	hotdogs = [
				"a hotdog a sandwhich","cereal soup", "ketchup a jam", 
				"ketchup a jelly", "pizza thin lazagna"
				]
	random_index = random.randrange(len(hotdogs))
	reply_text = f"I don't know, is {hotdogs[random_index]}?"
	return reply_text

def configure_logging():
	''' A straight forward logging configuration: 
			Console: INFO and up notifcations, with truncated messages. 
			File   : Complete debug information.
	'''
	file_handler = logging.FileHandler('logfile.log', encoding= 'utf-8', mode='w')
	file_handler.setLevel(logging.DEBUG)
	console_handler = logging.StreamHandler()
	console_handler.setLevel(logging.INFO)
	console_handler.setFormatter(logging.Formatter(fmt='%(asctime)s | %(name)-16.16s | %(levelname)-4s | %(message)-72s'))	

	# Configure logging using the handlers. 
	logging.basicConfig(
		handlers=[file_handler,console_handler],
		level = logging.DEBUG,
		format='%(asctime)s | %(name)-32.32s | %(levelname)-8.8s | %(message)s',
		datefmt = '%Y-%m-%d %H:%M:%S'
		)

	# Setting logging level for particularly Verbose loggers.	
	# logging.getLogger("prawcore").setLevel(logging.ERROR)	


def main():
	''' The main purpose of the script is to execute a growing number of automated tasks for /r/SteveDangle
			- Automaticially post Steve Dangle Podcast Episodes
			- Monitor user comments for favourite submissions & other commands
			- Future: Post SteveDangle videos
	'''
	# Configure logger, reddit conection
	configure_logging()
	root_log = logging.getLogger('SDBotcast.Root')

	reddit_keys = load_json("keys.json")['reddit_keys'] 
	SDBotcast_reddit = praw.Reddit(	client_id		= reddit_keys['client_id'], 
									client_secret 	= reddit_keys['client_secret'], 
									user_agent		= reddit_keys['user_agent'], 
									username		= reddit_keys['username'], 
									password		= reddit_keys['password'])


	with open('AsciiIntro.txt', 'r',encoding="utf8") as f:
		root_log.info(f.read())
	
	# Assigning threads for main bot functions
	podcast_thread = threading.Thread(
		target = new_podcast,
		args = (SDBotcast_reddit,))  
	commands_thread = threading.Thread(
		target = new_commands,
		args = (SDBotcast_reddit,)) 

	# Starting  threads
	root_log.info("Starting threads for podcast and command searchers. ")
	podcast_thread.start()
	commands_thread.start()

	podcast_thread.join()
	commands_thread.join()

	root_log.info("Terminating Program.")
	

def new_podcast(reddit_dev):
	'''This function's main purpose is check every x minutes to see 
		if a new podcast is available to be posted to Reddit.

		It'll grab the latest podcast data and if the datetime doesn't
		matches the last known podcast date then it'll make a new
		post!
	'''	
	new_podcast_log = logging.getLogger('SDBotcast.Poster')
	config = load_json("config.json")

	while True:
		try: 
			# Get data of latest podcast, and format date to datetime.
			cast = feedparser.parse(config['rss_feed']).entries[0]
			episode_data = {k: cast[k] for k in ('id','title', 'published','link','itunes_duration','summary')}
			episode_data['published'] = datetime.datetime.strptime(episode_data['published'],'%a, %d %b %Y %H:%M:%S %z')


			if config['last_cast_dt'] == str(episode_data['published']):
				new_podcast_log.info("RSS Reviewed: No new podcast available.")
			else:   
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
				podcastpost = reddit_user.subreddit("SteveDangle").submit(post_title, selftext = selftext)
				podcastpost.mod.sticky()
				podcastpost.mod.suggested_sort(sort='new')

				config['last_cast_dt'] = str(episode_data['published'])
				dump_json("config.json",config)

				time.sleep(36*60*60)  # Podcasts never < 48 hours apart
			
			# Go to sleep for a set time depending on time of day.
			time.sleep(calculate_sleeptime(config['sleep_Interval']))
		except Exception as e:
			new_podcast_log.error(f"RSS reading error. Error: {e}")
			time.sleep(900)
			continue

def new_commands(reddit_user):
	'''Searches each comment for every command string, and calls all 
		helper function based on the index of the regular expression(s)
		which was successful.

	'''
	comment_log = logging.getLogger('SDBotcast.Commands')
	COMMAND_STRINGS = {
		"Favourite" :	"(SDBotcast! Favourite|Favorite|favourite|favorite) (\d\d:\d\d:\d\d|\d:\d\d:\d\d)",
		"Hotdog" 	:	"(?:^|(?<=[.?!])) ?(?:IS|Is|is) ?a? ([a-zA-Z]{3,16}) ?a? ([a-zA-Z]{3,16})\?",
		"SoftMotherfucker" : "(?i)@ ?soft ?mother ?fucker"
	}

	for comment in reddit_user.subreddit('SteveDangle').stream.comments(skip_existing=False):
		comment_log.info(f"New Comment: {comment.body[:50]}...") 
		for command in COMMAND_STRINGS:		
			regex = re.search(command,comment.body)

			if regex is not None:
				if (regex.re.pattern == COMMAND_STRINGS["Favourite"]):
					reply_text = BOT_Submit_Favourite(comment,regex)	 
				elif (regex.re.pattern == COMMAND_STRINGS["Hotdog"]):
					reply_text = BOT_Is_A_Hotdog_A_Sandwhich()
				elif (regex.re.pattern == COMMAND_STRINGS['SoftMotherfucker']):
					reply_text = "Don't be an @SoftMotherFucker!"
				#elif (regex.re.pattern == COMMAND_STRINGS['']):
				#elif (regex.re.pattern == COMMAND_STRINGS['']):
				comment_log.info("Command processed.")
				comment_log.debug(f"Command Processed. \n\nCommand: {command}. Comment: {comment}")
				comment.reply(reply_text)


if __name__ == '__main__':
	main()
