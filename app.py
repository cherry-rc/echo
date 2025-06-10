#     15 Nov 2024 -- updated to ELSentry v2.0a beta
#     updated with specific path to /view
"""
EchoLeaf Version 1.5c / p3

20 Sept 2024 
Changed def ConfigProperties to read a multiple line JSON object

Passes Pycharm P3 Check / Minor syntax issues (e.g. upper/lowercase on functions)
FB 5 June 2024

Application: app.py
Version: 1.0
Release Date: 01 Dec 2016
Description:  Thin client web server from running EchoLeaf Administation function via a web browser.

Change History:

Copyright EchoLeaf 2016
"""

import bottle
import os
import sys
import json

# routes contains the HTTP handlers for our server and must be imported.
import routes

if '--debug' in sys.argv[1:] or 'SERVER_DEBUG' in os.environ:
    # Debug mode will enable more verbose output in the console window.
    # It must be set at the beginning of the script.
    bottle.debug(True)


def configProperties():
    # ... (same as before)
    try:
        with open("EchoLeaf.config", "r") as configuration:
            info = json.load(configuration)
        info["error"] = 0
        info["errormsg"] = ''
    except FileNotFoundError:  # More specific exception handling
        info["error"] = 2
        info["errormsg"] = "Configuration file 'EchoLeaf.config' not found."
    except json.JSONDecodeError:
        info["error"] = 3
        info["errormsg"] = "Invalid JSON in configuration file."
    except Exception as e:  # catch all other exceptions
        info["error"] = 4
        info["errormsg"] = f"An unexpected error occurred: {e}"
    return info


def wsgi_app():
    """Returns the application to make available through wfastcgi. This is used
    when the site is published to Microsoft Azure."""
    return bottle.default_app()


if __name__ == '__main__':
    PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
    STATIC_ROOT = os.path.join(PROJECT_ROOT, 'static').replace('\\', '/')
    VIEWS_ROOT = os.path.join(PROJECT_ROOT, 'views').replace('\\', '/')
    server = "localhost"
    prop = configProperties()  # opens EchoLeaf.config
    if prop["error"] != 0:
        print(f"Error starting EchoLeaf application: {prop['errormsg']}")
        sys.exit(1)  # Exit with an error code if there's a config error
    else:
        server = prop['host']
        # HOST = '192.168.1.34'  # Or use prop['host'] if needed
        HOST = "127.0.0.1"

        try:
            PORT = int(os.environ.get('SERVER_PORT', '5555'))
        except ValueError:
            PORT = 5555
            print("Warning: Invalid SERVER_PORT environment variable. Using default port 5555.")
        except TypeError:
            PORT = 5555
            print("Warning: SERVER_PORT environment variable not set. Using default port 5555.")

        @bottle.route('/static/<filepath:path>')
        def server_static(filepath):
            """Handler for static files."""
            return bottle.static_file(filepath, root=STATIC_ROOT)

        @bottle.route('/views/<filepath:path>') 
        def serve_views(filepath):
            """Handler for files in views directory."""
            return bottle.static_file(filepath, root=VIEWS_ROOT)

        # Starts a local test server. REMOVE reloader=True for production
        bottle.run(server='wsgiref', host=HOST, port=PORT)  # removed reloader=True      
