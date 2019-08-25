# Import Modules
import re, datetime, time #standard modules
import json         # https://docs.python.org/3/library/json.html
import logging         # https://docs.python.org/3/library/logging.html
import threading     # https://docs.python.org/3/library/threading.html

import feedparser  # rss parser: https://pythonhosted.org/feedparser/
import praw #reddit api wrapper: https://praw.readthedocs.io/en/latest/


class User:
    '''This is a base user class to store user keys. 
        The more social media platforms that are used, 
        the more worthwhile this class becomes. 
    '''                             
    def __init__(self, platform, *args):
        self.platform = platform

        # Declaration of secrets, tokens, passwords, etc.
        if args is not None:
            for key, val in args[0].items() :                 
                setattr(self, key, val)
class Reddit_User(User):  
    '''This class is used to create an easy means of creating helper
        functions for the PRAW wrapper while maintaining structre.

        Additionally, the R_User/R_Mod specifications makes it 
        easy to remember what kind of commands a particular user
        should have available at their disposal. 
    '''

    # Pass the reddit API keys (name & password needed for posting)
    def __init__(self, reddit_keys):
        super().__init__('Reddit', reddit_keys)
        if all(hasattr(self, arg) for arg in ["username","password"]):  
            self.ReadOnly = False
        else: self.ReadOnly = True

    # Establish a link to reddit through PRAW and return that connection
    def establish_api_connection(self):            
        self.reddit = praw.Reddit(
            client_id=self.client_id, 
            client_secret=self.client_secret,
            user_agent=self.user_agent, 
            username=self.username, 
            password=self.password)
        return self.reddit

    # creates a new reddit post based on provided Kwargs.
    # kwargs - https://praw.readthedocs.io/en/latest/code_overview/models/subreddit.html?highlight=submit#praw.models.Subreddit.submit
    def create_post(self,subreddit, title, **kwargs):
        self.thread = self.reddit.subreddit(subreddit).submit(title, **kwargs)
        return self.thread
class Reddit_Mod(Reddit_User):
    '''Similar to Reddit_User, this class is a subclass meant to make
        available function calls more easy to remember and complete.
        I.E. Only Reddit_mods can sticky posts and comments
    '''

    # Passes the reddit API keys, and inheret the Reddit_User Functions. 
    def __init__(self, reddit_keys):
        super().__init__(reddit_keys)

    # Calls create_post and then sorts/stickies accordingly. 
    def create_sticky_post(self, subreddit, title, 
                           sticky=True, sort='blank',**kwargs):
        self.thread = self.create_post(subreddit, title, **kwargs)
        self.thread.mod.sticky(state=sticky,bottom=False)
        self.thread.mod.suggested_sort(sort=sort)
        return self.thread

### Helper Functions
def print_textfile(file):      # Prints a given textfile to the output.
    with open('AsciiIntro.txt', 'r',encoding="utf8") as f:
        file_contents = f.read()
        print (file_contents)
def load_json(file):           # Return the raw json string from file
    with open(file, 'r') as f:
        raw_json = json.load(f)
    return raw_json
def dump_json(file):           # Dump raw json string to json file
    with open(file, "w") as file_Object:
        json.dump(data, file_Object, indent = 4)
def calculate_sleeptime(sleep_Interval):
    '''This function is meant to allow for the podcast search function
        to sleep longer during hours when posting never happens. 

        Later if I'm really bored I'll convert this into a Kernal
        Density Estimate based calculation to teach it to myself
            - Calculate KDE
            - Take current time
            - Find time t where probability of posting is X.

        For now this is simply assigning a rough time multipler 
        based off of a histogram of the posting times. 
    '''

    tm = 1
    ch = datetime.datetime.now().hour
    if (ch == 23):             tm = 1  #  11 PM            - 5   min
    elif(ch==0 or ch >= 22):   tm = 2  # 0-1 AM, 10-11PM   - 10  min
    elif(ch <= 2 or ch >= 20): tm = 3  # 1-2 AM, 8-10PM    - 15  min
    elif(ch >= 17 or ch <4):   tm = 6  # 2-4 AM, 5-8PM     - 30  min
    else:                      tm = 24 # Off-Peak hours    - 120 min
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
    SC_Link =  re.search("\[Soundcloud\]\((.+)\)",post_text).group(2)    
    Duration = re.search("Duration: (\d\d:\d\d:\d\d)", post_text).group(2)
    reply_text = ""

    try:
        # Try and parse timestamp and push data to favourites.json         
        timestamp = datetime.datetime.strptime(regex.group(2),"%H:%M:%S")
        if (timestamp > Duration):
            comment_log.warning("Invalid timestamp provided.")
            reply_text("Timestamp exceeds podcast duration, try again.")
        else:
            favourite_submission = { 
                "name" : comment.author.name, 
                "posting_time" : comment.created_utc,
                "comment_id" : comment.id,
                "link": SC_Link }    
            favourites_log = load_json(file)
            favourites_log["Favourite Comments"].append(favourite_submission)
            dump_json(file)
            
            reply_text = f"Adding [SoundCloudLink]({SC_Link}) to the pile of favourites."
    except: 
        comment_log.warning("Exception from timetamp parsing: {e}")
        reply_text = "Unable to parse timestamp. Confirm timestamp is available in podcast post, and that timestamp provided is in the 00:00:00 format."
    return reply_text

def configure_logging():
    '''Configure the logging module. 

        BasicConfig is used to ensure that imports that use logging
        will have their logs piped into the logfile.This is important
        as it means you can see PRAW timeouts, max retries,etc.
    '''

    # creates file/console handlers. file should be always set to DEBUG.
    file_handler = logging.FileHandler('logfile.log',mode='w')
    file_handler.setLevel(logging.DEBUG)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # Configure logging using the handlers. 
    # WARNING: Level acts as an overall level filter over handlers 
    logging.basicConfig(
        handlers=[file_handler,console_handler],
        level = logging.DEBUG,
        format='%(asctime)s - %(name)17s  - %(levelname)8s - %(message)s')          # I think this ensures that other modules using logging have their messages piped through.
    

    return
def get_podcast_data(rss_feed):         
    '''Uses the feedparser module to parse the SDP RSS feed. 
        This function retrieves the latest podcast data dictionary,
        and returns a subset of it. Also parses the publish time to 
        standard form. 
    '''
    cast = feedparser.parse(rss_feed).entries[0]
    episode_data = {k: cast[k] for k in (
        'id','title', 'published','link','itunes_duration','summary')}
    episode_data['published'] = datetime.datetime.strptime(
        episode_data['published'],'%a, %d %b %Y %H:%M:%S %z')
    return episode_data


def init():
    '''This initilaization function just takes care of some of the 
        necessary items to run the bot. 
        - Print the ever important Ascii Art
        - configure the logger for debugging & notices
        - load keys and connect to reddit.
    '''

    print_textfile("AsciiIntro.txt")     # C'est très important. 
    configure_logging()

    init_log = logging.getLogger('SDPBOT.Initialize')
    init_log.info("SDPBOT loading.")

    # Load Reddit API keys.
    keys = load_json('keys.json')
    reddit_keys = keys['reddit_keys'] 
    init_log.info("Reddit's API keys have been retrived.")

    # Creating Instance of Reddit Users
    try:
        reddit_user = Reddit_Mod(reddit_keys)
        reddit_connect = reddit_user.establish_api_connection()
        init_log.info("Connected to Reddit")
    except Exception as e:
        init_log.critical(f"Can't connect to Reddit, exiting program. Error: {e}")
        exit()

    # Excecute the main program loop.
    init_log.info("Loading complete. Continuing to main program.")
    main(reddit_user, reddit_connect)

def main(reddit_user, reddit_connect):
    '''This is the main thread where the threads for the different
        main bot actions are created and started.
    '''
    root_log = logging.getLogger('SDPBOT')
    
    # Assigning threads for main bot functions
    podcast_thread = threading.Thread(
        target = new_podcast,
        args = (reddit_user, reddit_connect))  
    commands_thread = threading.Thread(
        target = new_commands,
        args = (reddit_user, reddit_connect)) 

    # Starting  threads
    root_log.info("Starting threads for podcast and command searchers. ")
    podcast_thread.start()
    commands_thread.start()

def new_podcast(reddit_dev, reddit_connect):
    '''This function's main purpose is check every x minutes to see 
        if a new podcast is available to be posted to Reddit.

        It'll grab the latest podcast data and if the datetime doesn't
        matches the last known podcast date then it'll make a new
        post!
    '''    

    new_podcast_log = logging.getLogger('SDPBOT.SDP-Poster')
    config = load_json("config.json")

    while True:
        try: 
            # Get data of latest podcast, and compare the date.
            new_podcast_data = get_podcast_data(config['rss_feed'])
            if config['last_cast_dt'] == str(new_podcast_data['published']):
                new_podcast_log.info("RSS Reviewed: No new podcast available.")
            else:   
                for key, val in new_podcast_data.items() :     
                    setattr(self, key, val)

                # Get the youtube link from podcast data.
                it_link = "https://itunes.apple.com/ca/podcast/steve-dangle-podcast/id669828195?mt=2"
                yt_link = re.search(
                    "https://youtu\.be/.{11}",  # YT vid id is 11 chars
                    new_podcast_data['summary']).group()          
                
                # Build the selftext & title, and POST IT!
                selftext =  f"""New SteveDangle Podcast!
                                Title: {title}
                                Duration: {itunes_duration}
                                [SoundCloud]({link})
                                [Itunes]({it_link})
                                [Youtube]({yt_link})"""
                title = f"The Steve Dangle Podcast - {title}"""
                podcastpost = reddit_dev.create_post(
                    "SteveDangle",title, True, "new",selftext=selftext)
                new_podcast_log.info(
                    f"New podcast posted! {title}. Sleeping for 36 hours.")

                # Update last podcast date in config. 
                #   This is after the post to ensure it'll only get
                #   update on a successful post. 
                with open("config.json", 'w') as file_Object:
                    config['last_cast_dt'] = str(published)
                    json.dump(config,file_Object, indent=4)

                time.sleep(36*60*60)  # Podcasts never < 48 hours apart
            
            # Go to sleep for a set time depending on time of day.
            time.sleep(calculate_sleeptime(config['sleep_Interval']))
        except Exception as e:
            new_podcast_log.error(f"RSS reading error. Error: {e}")
            time.sleep(900)
            continue
def new_commands(reddit_user, reddit_connect):
    '''Searches each comment for every command string, and calls all 
        helper function based on the index of the regular expression(s)
        which was successful.

    '''
    comment_log = logging.getLogger('SDPBOT.Com-Search')
    command_strings = [
        "(SDPBOT! Favourite|Favorite|favourite|favorite) (\d\d:\d\d:\d\d|\d:\d\d:\d\d)"
    ]
    for comment in reddit_connect.subreddit('SteveDangle').stream.comments(skip_existing=True):
        for command in command_strings:        
            regex = re.search(command,comment.body)
            if regex is not None:
                command_text = regex.group()
                if (regex.re.pattern == command_strings[0]):
                    reply_text = BOT_Submit_Favourite()     
                #elif (regex.re.pattern == command_strings[1]):
                #elif (regex.re.pattern == command_strings[2]):
                #elif (regex.re.pattern == command_strings[3]):
                #elif (regex.re.pattern == command_strings[4]):
                #elif (regex.re.pattern == command_strings[5]):
                #elif (regex.re.pattern == command_strings[6]):
                #elif (regex.re.pattern == command_strings[7]):
                comment_log.info("Command processed.")
                comment_log.debug(f"Command Processed. \n\nCommand: {command}. Comment: {comment}")
                comment.reply(reply_text)


if __name__ == '__main__':
    init()
