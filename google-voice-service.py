#!/usr/bin/env python3
from multiprocessing import Process
# Google Voice service
import asyncio
import datetime
import random
import time
import json
import giphy_client
import logging
import config
import platform
import subprocess
import sys
import threading
from subprocess import Popen
from giphy_client.rest import ApiException
import pprint
import websockets
# Import Google AIY and Voice Assitant libs
import aiy.assistant.auth_helpers
from aiy.assistant.library import Assistant
import aiy.audio
import aiy.voicehat
from google.assistant.library.event import EventType

lastLoadedQuery = ''
lastLoadedTime = 0

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s:%(name)s:%(message)s"
)

def power_off_pi():
    aiy.audio.say('Good bye!')
    subprocess.call('sudo shutdown now', shell=True)


def reboot_pi():
    aiy.audio.say('See you in a bit!')
    subprocess.call('sudo reboot', shell=True)


def say_ip():
    ip_address = subprocess.check_output("hostname -I | cut -d' ' -f1", shell=True)
    aiy.audio.say('My IP address is %s' % ip_address.decode('utf-8'))

def launchChrome():
    Popen(['/usr/bin/chromium-browser', '--start-fullscreen', 'websocket-client.html'])

def getGiphy(query):
    default_return_obj = {'query' : 'kittens', 'timestamp' : 0, 'embed_url' : ['https://giphy.com/embed/DBucugVBKhvTW'] }
    try:
        # create an instance of the Giphy API class
        api_instance = giphy_client.DefaultApi()
        api_key = config.api_key # str | Giphy API Key.
        limit = 25 # int | The maximum number of records to return. (optional) (default to 25)
        offset = 0 # int | An optional results offset. Defaults to 0. (optional) (default to 0)
        rating = 'g' # str | Filters results by specified rating. (optional)
        lang = 'en' # str | Specify default country for regional content; use a 2-letter ISO 639-1 country code. See list of supported languages <a href = \"../language-support\">here</a>. (optional)
        fmt = 'json' # str | Used to indicate the expected response format. Default is Json. (optional) (default to json)
        api_response = api_instance.gifs_search_get(api_key, query, limit=limit, offset=offset, rating=rating, lang=lang, fmt=fmt)
        embedUrls = []
        # Loop through gifs and create array of embed urls
        for elem in api_response.data:
            embedUrls.append(elem.embed_url)
        data = {}
        data['embed_url'] = embedUrls
        data['query'] = query
        data['timestamp'] = time.time()
        pprint.pprint(data)
        return(data)
    except ApiException as e:
        print("Exception when calling DefaultApi->gifs_search_get: %s\n" % e)
        return(default_return_obj)
    except IndexError as e:
        print('empty response from giphy returned %s\n' % e)
        return(default_return_obj)

def getGiphyFromFile() :
    try:
        with open('giphySearch.json', 'r') as json_file:
            data = json.load(json_file)
            return(data)
    except json.decoder.JSONDecodeError as e:
        print('Caught exception - JSON file incomplete')
        return({'query' : lastLoadedQuery, 'timestamp': 0, 'embed_url' : []})

def searchAndWriteGiphy(query):
	with open('giphySearch.json', 'w') as outfile:
		json.dump(getGiphy(query), outfile)

class MyAssistant(object) :
    """An assistant that runs in the background.

    The Google Assistant Library event loop blocks the running thread entirely.
    To support the button trigger, we need to run the event loop in a separate
    thread. Otherwise, the on_button_pressed() method will never get a chance to
    be invoked.
    """

    def __init__(self):
        self._task = threading.Thread(target=self._run_task)
        self._can_start_conversation = False
        self._assistant = None

    def start(self):
        """Starts the assistant.

        Starts the assistant event loop and begin processing events.
        """
        self._task.start()

    def _run_task(self):
        credentials = aiy.assistant.auth_helpers.get_assistant_credentials()
        with Assistant(credentials) as assistant:
            self._assistant = assistant
            for event in assistant.start():
                self._process_event(event)

    def _process_event(self, event):
        status_ui = aiy.voicehat.get_status_ui()
        if event.type == EventType.ON_START_FINISHED:
            status_ui.status('ready')
            self._can_start_conversation = True
            # Start the voicehat button trigger.
            aiy.voicehat.get_button().on_press(self._on_button_pressed)
            if sys.stdout.isatty():
                print('Say "OK, Google" or press the button, then speak. '
                      'Press Ctrl+C to quit...')

        elif event.type == EventType.ON_RECOGNIZING_SPEECH_FINISHED and event.args:
            print('You said:', event.args['text'])
            text = event.args['text'].lower()
            if text == 'power off':
                self._assistant.stop_conversation()
                power_off_pi()
            elif text == 'reboot':
                self._assistant.stop_conversation()
                reboot_pi()
            elif text == 'ip address':
                self._assistant.stop_conversation()
                say_ip()
            elif text.startswith('search'):
                if len(text) > 7:
                    gifToSearch = text[7:]
                    self._assistant.stop_conversation()
                    #aiy.audio.say('You requested giphy results for ' + gifToSearch)
                    searchAndWriteGiphy(gifToSearch)
                else:
                    aiy.audio.say('Invalid search. Please try again.')

        elif event.type == EventType.ON_CONVERSATION_TURN_STARTED:
            self._can_start_conversation = False
            status_ui.status('listening')

        elif event.type == EventType.ON_END_OF_UTTERANCE:
            status_ui.status('thinking')

        elif (event.type == EventType.ON_CONVERSATION_TURN_FINISHED
              or event.type == EventType.ON_CONVERSATION_TURN_TIMEOUT
              or event.type == EventType.ON_NO_RESPONSE):
            status_ui.status('ready')
            self._can_start_conversation = True

        elif event.type == EventType.ON_ASSISTANT_ERROR and event.args and event.args['is_fatal']:
            sys.exit(1)

    def _on_button_pressed(self):
        # Check if we can start a conversation. 'self._can_start_conversation'
        # is False when either:
        # 1. The assistant library is not yet ready; OR
        # 2. The assistant library is already in a conversation.
        if self._can_start_conversation:
            self._assistant.start_conversation()

async def timedGiphy(websocket, path):
	while True:
		global lastLoadedQuery
		global lastLoadedTime
		time.sleep(.5)
		loadedJSON = getGiphyFromFile()
		if lastLoadedTime != loadedJSON['timestamp'] and len(loadedJSON['embed_url']) > 0:
			print('new query has been made: ' + loadedJSON['query'])
			lastLoadedQuery = loadedJSON['query']
			lastLoadedTime = loadedJSON['timestamp']
			await websocket.send(json.dumps(loadedJSON, indent=4))
		await asyncio.sleep(random.random())

def websocketServer():
    print('Starting websocket server on port 5678')
    start_server = websockets.serve(timedGiphy, '127.0.0.1', 5678) 
    launchChrome()
    asyncio.get_event_loop().run_until_complete(start_server)
    asyncio.get_event_loop().run_forever()

def startGoogleVoice():
    print('Starting google voice service...')
    MyAssistant().start()
    

if __name__ == "__main__":
    firstLoad = getGiphyFromFile()
    lastLoadedQuery = firstLoad['query']
    lastLoadedTime = firstLoad['timestamp']
    print('first loaded query = ' + firstLoad['query'])
    p1 = Process(target=websocketServer)
    p1.start()
    #p2 = Process(target=startGoogleVoice)
    #p2.start()
    startGoogleVoice()
