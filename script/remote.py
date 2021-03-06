#!/usr/bin/env python

import getpass
import os
import sys

#To run this script, from the application root folder (where migrate.py is located):
#python script/remote.py

## Application specific
#make sure the variables below are correct.
SDK_DIR = '/home/your_username/google_appengine'
APP_DIR = '/home/your_username/git/bloggart'
APPID = 'bloggart_GAE_app_ID'
EMAIL = 'your_email@example.com'

print "Your SDK folder is "+SDK_DIR;
print "If this is incorrect, edit remote.py to reflect the correct path!"

REMOTE_API_PATH = '/remote_api'

## Extra paths to be inserted into sys.path,
## including the SDK, it's libraries, your APPDIR, and APPDIR/lib
EXTRA_PATHS = [
	SDK_DIR,
	os.path.join(SDK_DIR, 'lib', 'antlr3'),
	os.path.join(SDK_DIR, 'lib', 'django'),
	os.path.join(SDK_DIR, 'lib', 'webob'),
	os.path.join(SDK_DIR, 'lib', 'fancy_urllib'),
	os.path.join(SDK_DIR, 'lib', 'yaml', 'lib'),
	APP_DIR,
	os.path.join(APP_DIR, 'lib'),
]
sys.path = EXTRA_PATHS + sys.path

# Bloggart is currently based on Django 0.96
from google.appengine.dist import use_library
use_library('django', '0.96')

from google.appengine.ext.remote_api import remote_api_stub

def attach(host=None):
	def auth_func():
		if host and host.startswith('localhost'):
			return ('foo', 'bar')
		else:
			return (EMAIL, getpass.getpass())
	remote_api_stub.ConfigureRemoteApi(APPID, REMOTE_API_PATH, auth_func, host)
	remote_api_stub.MaybeInvokeAuthentication()
	os.environ['SERVER_SOFTWARE'] = 'Development (remote_api)/1.0'


if __name__ == '__main__':
	if len(sys.argv) == 2 and sys.argv[1] == '-l':
		host = 'localhost:8080'
	else: 
		host = None

	attach(host)

	from google.appengine.ext import db
	from google.appengine.api import memcache

	BANNER = "App Engine remote_api shell\n" + \
	"Python %s\n" % sys.version + \
	"The db, and memcache modules are imported."

	## Use readline for completion/history if available
	try:
		import readline
	except ImportError:
		pass
	else:
		HISTORY_PATH = os.path.expanduser('~/.remote_api_shell_history')
		readline.parse_and_bind('tab: complete')
		if os.path.exists(HISTORY_PATH):
			readline.read_history_file(HISTORY_PATH)
		import atexit
		atexit.register(lambda: readline.write_history_file(HISTORY_PATH))

	sys.ps1 = '%s <-- ' % (host or APPID)

	import code
	code.interact(banner=BANNER, local=globals())