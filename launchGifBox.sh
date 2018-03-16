#!/bin/bash
# Author:	Kevin Roberts
# Email:	kevin.roberts@icf.com
# Date:		2018-03-15
# Usage:	launchGifbox.sh
# Description:
#	Launches the python scripts and page for
#	running the Gifbox program.

function finish() {
	pgrep -f 'python3 websocket-server.py' | xargs kill &
        pgrep -f 'python3 google-voice-service.py' | xargs kill
	echo "closing Gifbox. bye."
}

trap finish SIGINT

python3 websocket-server.py &
python3 google-voice-service.py &
/usr/bin/chromium-browser --start-fullscreen websocket-client.html
