#!/usr/bin/env python3

import asyncio
import datetime
import random
import websockets
import time
import json
import giphy_client
from giphy_client.rest import ApiException
import pprint

lastLoadedQuery = ''

def getGiphyFromFile():
	try:
		with open('giphySearch.json', 'r') as json_file:  
			data = json.load(json_file)
			return(data)
	except json.decoder.JSONDecodeError as e:
	 	print('Caught exception')
	 	return({'query' : lastLoadedQuery})

async def timedGiphy(websocket, path):
	while True:
		global lastLoadedQuery
		time.sleep(.5)
		loadedJSON = getGiphyFromFile()
		if lastLoadedQuery != loadedJSON['query']:
			print('new query has been made: ' + loadedJSON['query'])
			lastLoadedQuery = loadedJSON['query']
			await websocket.send(json.dumps(loadedJSON, indent=4))
		await asyncio.sleep(random.random())


firstLoad = getGiphyFromFile()
lastLoadedQuery = firstLoad['query']
print('first loaded query = ' + firstLoad['query'])

start_server = websockets.serve(timedGiphy, '127.0.0.1', 5678)

asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()