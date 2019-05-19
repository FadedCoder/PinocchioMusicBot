import os

# Core
PREFIX = os.environ.get('PREFIX', 'p!')
TOKEN = os.environ.get('TOKEN')
CLIENT_ID = "579762337792262187"
if TOKEN is None:
    raise Exception('The TOKEN environmental variable is not set.')


# Database
DB_USERNAME = os.environ.get('DB_USERNAME')
DB_PASSWORD = os.environ.get('DB_PASSWORD')
DB_NAME = os.environ.get('DB_NAME')
if DB_USERNAME is None or DB_NAME is None:
    raise Exception('Environmental variables for database not set')
ENGINE_URL = "postgresql://{0}:{1}@localhost:5432/{2}".format(DB_USERNAME, DB_PASSWORD, DB_NAME)
