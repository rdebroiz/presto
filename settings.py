from path import Path

# those tow file are set in presot.py

PRESTO_DIR = Path('')
PRESTO_LOG_FILENAME = Path('')
PRESTO_GRAPH_FILENAME = Path('')

# extention helpers:

NODE_EXEC_SUFFIX = '.nexec'

# stdout color helpers

OKGREEN = '\033[92m'
FAIL = '\033[91m'
ENDC = '\033[0m'
RETURN = '\033[K\r'
ENDC = '\033[0m'
BOLD = '\033[1m'
ENDCBOLD = ENDC + BOLD
