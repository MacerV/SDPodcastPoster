## Import Modules
import re, datetime, time #standard regex, datetime, & time modules
import json #json parser modules 			- https://docs.python.org/3/library/json.html
import logging ##flexible logging wrapper   - https://docs.python.org/3/library/logging.html
import threading #allows parallel processng - https://docs.python.org/3/library/threading.html

import feedparser #rss parser    			- https://pythonhosted.org/feedparser/
import praw #reddit api wrapper  			- https://praw.readthedocs.io/en/latest/


class User: 							# base user class to use with custom platform accounts
	def __init__(self, platform, *args):
		self.platform = platform

		# Declaration of secrets, tokens, passwords, etc.
		if args is not None:
			for key, val in args[0].items() : 				
				setattr(self, key, val)

class Reddit_User(User):  				# User Subclass for regular PRAW interactions 
	def __init__(self, reddit_keys):
		super().__init__('Reddit', reddit_keys)
		if all(hasattr(self, arg) for arg in ["username","password"]):  
			self.ReadOnly = False
		else: self.ReadOnly = True

	def establish_api_connection(self):			# Establishes and returns link to PRAW connection for user. 
		self.reddit = praw.Reddit(
			client_id=self.client_id, 
			client_secret=self.client_secret,
			user_agent=self.user_agent, 
			username=self.username, 
			password=self.password)
		return self.reddit

	def comment_reply(self, comment, reply_text):  #replies to ref. comment		
		comment.reply(reply_text)

	#kwargs - https://praw.readthedocs.io/en/latest/code_overview/models/subreddit.html?highlight=submit#praw.models.Subreddit.submit
	def create_post(self,subreddit, title, **kwargs):
		self.thread = self.reddit.subreddit(subreddit).submit(
			title, **kwargs)
		return self.thread

class Reddit_Mod(Reddit_User):
	def __init__(self, reddit_keys):
		super().__init__(reddit_keys)

	def create_sticky_post(self, subreddit, title, #Performs mod actions on thread
			sticky=True, sort='blank',**kwargs):
		self.thread = self.create_post(subreddit, title, **kwargs)
		self.thread.mod.sticky(state=sticky,bottom=False)
		self.thread.mod.suggested_sort(sort=sort)
		return self.thread

###Helper Functions
def print_textfile(file):
	with open('AsciiIntro.txt', 'r',encoding="utf8") as f:
		file_contents = f.read()
		print (file_contents)
def load_json(file):
	with open(file, 'r') as f:
		raw_json = json.load(f)
	return raw_json
def configure_logging():
	# Sets the logfile and formatting of the log messages
	logging.basicConfig(filename='logfile.log',level=logging.DEBUG)
	formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

	# creates a console handler and sets the logging level to debug
	main_console_handler = logging.StreamHandler()
	main_console_handler.setLevel(logging.DEBUG)
	main_console_handler.setFormatter(formatter) 

	# Starts the main logger, sets its level and console handler. 
	logger = logging.getLogger('SDPBOT')
	logger.setLevel(logging.DEBUG)
	logger.addHandler(main_console_handler)

	return
def get_podcast_data(rss_feed): 		# returns subset of episode data from  feedparser module
	cast = feedparser.parse(rss_feed).entries[0]
	cast['published'] = datetime.datetime.strptime(cast['published'],'%a, %d %b %Y %H:%M:%S %z')
	episode = {k: cast[k] for k in ('id','title', 'published','link','itunes_duration','summary')}
	return episode


def init():
	# print_textfile("AsciiIntro.txt") 	# C'est très important
	configure_logging()  				# Configures the parameters for Logging
	init_logger = logging.getLogger('SDPBOT.Initialize')
	init_logger.info("SDPBOT loading.")

	#Try Loading Program Settings
	try:
		keys = load_json('keys.json')
		reddit_keys = keys['reddit_keys'] #should return a dict of reddit keys
		init_logger.info("eddit's API keys have been retrived.")
	except Exception as e:
		init_logger.critical(f"Error loading keys; Exception: {e}")
		exit()

	# Creating Instance of Reddit Users
	try:
		reddit_user = Reddit_Mod(reddit_keys)
		reddit_connect = reddit_user.establish_api_connection()
		init_logger.info("Connected to Reddit")
	except Exception as e:
		init_logger.critical(f"Can't connect to Reddit, exiting program. Error: {e}")
		exit()

	#if everything is running according to plan it can now execute the main program loop.
	init_logger.info("Loading complete. Continuing to main program.")
	main(reddit_user, reddit_connect)

def main(r_user, r_con):
	root_logger = logging.getLogger('SDPBOT')
	
	#Assigning threads for main bot functions; podcast_checker & command_searching
	pc_thr = threading.Thread(target = new_pc,args = (r_user, r_con))  
	coms_thr = threading.Thread(target = new_coms,args = (r_user, r_con)) 

	#Starting  threads
	root_logger.info("Starting threads for podcast and command searchers. ")
	pc_thr.start()
	coms_thr.start()

def new_pc(reddit_dev, reddit_connect):
	new_podcast_logger = logging.getLogger('SDPBOT.SDP-Poster')

	config = load_json("config.json")
	sleep_Interval = config['program_data']['sleep_Interval']
	last_podcast_date = config['program_data']['last_podcast_date']

	while True:
		try: #sometimes there is network issues.			
			new_podcast_data = get_podcast_data(config['program_data']['rss_feed'])
		except Exception as e:
			new_podcast_logger.error(f"Error reading RSS feed. Error: {e}")
			time.sleep(3600)
			continue

		# if the last registered podcast is not the same as the last podcast then we'll have a new podcast!
		if last_podcast_date != str(new_podcast_data['published']):
			#convert podcast data back into variables 
			#Note: tried k, v in dict.items but its not working here for some reason
			title = new_podcast_data['title']
			duration = new_podcast_data['itunes_duration']
			published = new_podcast_data['published']
			sc_link = new_podcast_data['link']
			summary = new_podcast_data['summary']

			#Updates the config file with the new podcast date.
			with open("config.json", 'w') as file_Object:
				config['program_data']['last_podcast_date'] = str(published)
				json.dump(config,file_Object, indent=4)

			#Generate the post submission text.
			yt_link = re.search("https://youtu\.be/.{11}",new_podcast_data['summary']).group() #searches the cast summary data for the youtube shortlink that Jesse puts there.
			selftext = f"New SteveDangle Podcast! \n\nTitle: {title} \n\nDuration: {duration}\n\n[SoundCloud]({sc_link}) \n\n[Itunes](https://itunes.apple.com/ca/podcast/steve-dangle-podcast/id669828195?mt=2) \n\n[Youtube]({yt_link}) \n\n"
			title = f"The Steve Dangle Podcast - {title}"

			# podcastpost = reddit_dev.create_post(subreddit,title,"text",selftext, True, "new")
			new_podcast_logger.info(f"RSS Reviewed: New podcast available! {title}. Sleeping for 24 hours.")
			time.sleep(24*60*60)
		else:
			new_podcast_logger.info("RSS Reviewed: No new podcast available.")

		time.sleep(sleep_Interval)

def new_coms(reddit_user, reddit_connect):
	comment_logger = logging.getLogger('SDPBOT.Com-Search')

	try:
		bot_command_string = "SDPBOT!"
		for comment in reddit_connect.subreddit('SteveDangle').stream.comments():

			if bot_command_string in comment.body:
				comment_logger.info("New command found.")
				command_string = comment.body[comment.body.find(bot_command_string):]
				if (bot_command_string + " Favourite") in command_string:
					timestamptext = re.search("(\d\d:\d\d:\d\d|\d:\d\d:\d\d)",command_string).group()
					timestamp = datetime.datetime.strptime(timestamptext,"%H:%M:%S")

					submissionText = comment.submission.selftext
					
					#confirm time within duration
					try:
						duration = re.search("Duration: \d\d:\d\d:\d\d", submissionText).group()
						duration = datetime.datetime.strptime(duration[11:],"%H:%M:%S")
					except:
						duration = datetime.datetime.strptime("00:00:00","%H:%M:%S")

					PodcastLink =  submissionText[submissionText.find('[')+13:submissionText.find(')')]
					SoundCloudLink = str(PodcastLink) + str("#t=") + str(timestamp)
					
					if (timestamp > duration):
						comment_logger.warning("Invalid timestamp provided. Informating user.")
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
						comment_logger.info("Adding new submission to favourites list.")
	except Exception as e:
		print(e)
		#the only exceptions should be network issues. Try again.
		reddit_connect = reddit_user.establish_api_connection()
		new_coms(reddit_user,reddit_connect)



if __name__ == '__main__':
	init()
