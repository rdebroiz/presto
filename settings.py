import os

PRESTO_DIR = os.path.join(os.curdir, '.presto')
PRESTO_LOG_FILENAME = os.path.join(PRESTO_DIR, 'presto.log')


OKGREEN = '\033[92m'
FAIL = '\033[91m'
ENDC = '\033[0m'
RETURN = '\033[K\r'
ENDC = '\033[0m'
BOLD = '\033[1m'
ENDCBOLD = ENDC + BOLD
