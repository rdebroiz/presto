#!/usr/bin/env python3

"""presto.

Usage:
    presto [-l <log_level> | --log <log_level>]
           [-w <workers> | --workers <workers>]
           [-p | --print]
           [-f | --force]
           [-n <node_name> | --node <node_name>]
           [-s <name:regexp> | --override_scope <name:regexp>]...
           <pipe.yaml>
    presto -h | --help
    presto -v |--version

Options:
    -w --workers <workers>
        Number max of different processus to launch together.
        [default: 0] -> Number of host's CPU.
    -l --log <log_level>
        Level of verbosity to print in the log file.
        Must be in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        [default: INFO]
    -p --print
        Print the execution of the pipeline only.
    -f --force
        Force execution of any node of the pipeline.
    -n --node <node_name>
        Launch pipeline from this node
    -s --override_scope <name:regexp>
        Use this option to override the regular expression used to build
        a scope.
        Example '-s SCOPE_NAME:reg-exp'
    <pipe.yaml>
        A yaml file starting with the data structure description
        and describing the pipeline.

    -h --help
        Show this screen.

    -v --version
        Show version.
"""

import os
import logging
from pprint import pformat
import settings
import log
from path import Path


def main(arguments):

    """Main function"""

    # ##############################################################################
    # make PRESTO_DIR
    # ##############################################################################

    settings.PRESTO_DIR = Path(arguments['<pipe.yaml>']).abspath() + '.presto'
    settings.PRESTO_LOG_FILENAME = settings.PRESTO_DIR + 'presto.log'
    os.makedirs(settings.PRESTO_DIR, exist_ok=True)

    # ##############################################################################
    # setup logs
    # ##############################################################################

    log_level = arguments['--log']
    log.setup(settings.PRESTO_LOG_FILENAME, log_level)
    logging.debug("cmd line arguments:\n%s", pformat(arguments))

    # ##############################################################################
    # get number of workers to use:
    # ##############################################################################

    try:
        max_workers = arguments['--workers']
        max_workers = int(max_workers)
        assert max_workers >= 0
    except (ValueError, AssertionError):
        logging.warning("<workers> must be a positive integer.\nDefault "
                        "value (auto-determine by the system) will be "
                        "used.\n")
        max_workers = 0

    try:
        if max_workers == 0:
            max_workers = os.cpu_count()
        assert max_workers is not None
    except AssertionError:
        logging.critical("could not find host's number of CPU please set the "
                         "--workers option yourself")
        raise

    # ##############################################################################
    # construct data model
    # ##############################################################################
    from yaml_io import YamlIO
    try:
        import path
    except ImportError:
        logging.critical("Presto requiered path.py to be installed, "
                         "checkout requirement.txt.")
        raise

    yaml_document_path = path.Path(arguments['<pipe.yaml>']).abspath()
    yaml_document = YamlIO.load_all_yaml(yaml_document_path)

    scope_to_override = {}
    for s in set(arguments['--override_scope']):
        scope_regexp = s.split(':')
        try:
            scope_to_override[scope_regexp[0]] = scope_regexp[1]
        except IndexError:
            msg = ("Malformed scope to override: '" +
                   settings.FAIL + s + settings.ENDC +
                   settings.BOLD + "'.\nHave to be: SCOPE_NAME:regexp")
            logging.critical(msg)
            raise

    try:
        from data_model import DataModel
        DataModel(yaml_document.pop(0),
                  yaml_document_path.dirname(),
                  scope_to_override)
    except IndexError:
        logging.critical("empty <pipe.yaml> file.")
        sys.exit(1)

    # ##############################################################################
    # construct pipeline
    # ##############################################################################

    try:
        import pipeline as pipi
        pipeline = pipi.Pipeline(yaml_document)
    except pipi.PipelineCyclicError:
        logging.critical("Pipeline can't be cyclic")
        sys.exit(-1)
    from executor import ThreadedPipelineExecutor
    executor = ThreadedPipelineExecutor(pipeline, max_workers)
    executor.print_only = arguments['--print']
    executor.force_execution = arguments['--force']

    # ##############################################################################
    # execute pipeline
    # ##############################################################################
    executor.execute(arguments['--node'])


# -- Main
if __name__ == '__main__':
    import sys
    try:
        from docopt import docopt
    except ImportError as err:
        print("presto need docopt", err)
        sys.exit(1)

    arguments = docopt(__doc__, version='presto 1.0.0')
    main(arguments)
