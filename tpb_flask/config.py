APIBAY_URL = "https://apibay.org/q.php"

OMDB_API_KEY = '' # get from https://www.omdbapi.com/apikey.aspx

REAL_DEBRID_API_TOKEN = '' # get from https://real-debrid.com/apitoken

FLASK_HOST = '0.0.0.0'
FLASK_PORT = 8123
FLASK_DEBUG = True

UNDESIRABLE_LIST = [
    'french',
    'russian',
    'rus',
    'ita',
    'dub',
    'cam',
    'latin',
    'hindi',
    'subs',
    'onlyfans',
    'porn',
    'blowjob',
    'sex',
    'anal',
    'cum'
    ]

QUALITY_ORDER = {
    '2160p': 1,
    '1080p': 2,
    '720p': 3,
    '480p': 4,
    'Other': 5,
    'bottom': 6
    }
