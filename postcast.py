# Import Modules
import re, datetime, time, os, sys 	#standard modules
import textwrap	 		# standard module for removing trailing idnents in post string
import json		 		# https://docs.python.org/3/library/json.html
import logging			# https://docs.python.org/3/library/logging.html

# Non-standard modules
import feedparser  	# rss parser: https://pythonhosted.org/feedparser/
import praw 		# reddit api wrapper: https://praw.readthedocs.io/en/latest/


def configure_logging():
	handlers = []
	file_handler = logging.FileHandler('SDBotcast.log', encoding= 'utf-8')
	handlers.append(file_handler)

	logging.basicConfig(
		handlers=handlers,
		level = logging.INFO,
		format='%(asctime)s | %(name)-32.32s | %(levelname)-8.8s | %(message)s',
		datefmt = '%Y-%m-%d %H:%M:%S'
		)

def main():
	# start up the log & load config file
	configure_logging()
	podcast_log = logging.getLogger('SDBotcast.Poster')
	podcast_log.info("__________________________________________")
	podcast_log.info("Executing Podcast Checker Script")
	with open("config.json", 'r') as f:
		config = json.load(f)

	## Main Execution
	podcast_log.info("Podcast Check started.")
	try: 
		# Get data of latest podcast from Soundcloud, and format date to datetime.
		cast = feedparser.parse(config['rss_feed']).entries[0]
		episode_data = {k: cast[k] for k in ('id','title', 'published','link','itunes_duration','summary')}
		episode_data['published'] = datetime.datetime.strptime(episode_data['published'],'%a, %d %b %Y %H:%M:%S %z')
		podcast_log.debug(episode_data)

		# compare new podcast date to old one to see if new. 
		if config['last_cast_dt'] == str(episode_data['published']):
			podcast_log.info("RSS Reviewed: No new podcast available.")
		else:   
			podcast_log.info("RSS Reviewed: New podcast available. Processing")
			
			# Parsing reddit post information.
			post_title = f"The Steve Dangle Podcast - {episode_data['title']}"
			it_link = "https://itunes.apple.com/ca/podcast/steve-dangle-podcast/id669828195?mt=2"
			yt_link = "https://www.youtube.com/channel/UC0a0z05HiddEn7k6OGnDprg" 						#Backup default  link
			try: 
				yt_link = re.search("https://youtu\.be/.{11}", episode_data['summary']).group()		 	 # YT vid id is 11 chars
			except: 
				podcast_log.warning("Youtube link not found in podcast description")

			selftext =  textwrap.dedent(f"""\
						Places to listen to the new SteveDangle Podcast! 

						|[SoundCloud]({episode_data['link']})|[Itunes]({it_link})[Youtube]({yt_link})|

						Duration: {episode_data['itunes_duration']}
						
						To submit a favourite SDP moment, comment: SDBotcast! Favourite (timetamp in HH:MM:SS format)""")

			# post the podcast to reddit & save to config.
			with open("keys.json", 'r') as f:
				reddit_keys = json.load(f)['reddit_keys'] 
			reddit_dev = praw.Reddit(	client_id		= reddit_keys['client_id'], 
										client_secret 	= reddit_keys['client_secret'], 
										user_agent		= reddit_keys['user_agent'], 
										username		= reddit_keys['username'], 
										password		= reddit_keys['password'])

			# Checks submission format is valid with the sub (which is should be) and submits it, and stickeys it. 
			reddit_dev.validate_on_submit = True 
			podcastpost = reddit_dev.subreddit("SteveDangle").submit(post_title, selftext = selftext)
			podcastpost.mod.sticky()
			podcastpost.mod.suggested_sort(sort='new')

			config['last_cast_dt'] = str(episode_data['published'])
			with open("config.json", "w") as file_Object:
				json.dump(config, file_Object, indent = 4)

	except Exception as e:
		podcast_log.error(f"RSS reading error. Error: {e}")


if __name__ == '__main__':
	main()
