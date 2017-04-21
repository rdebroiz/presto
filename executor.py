import logging
from concurrent import futures
from concurrent.futures import ThreadPoolExecutor
from evaluator import Evaluator
from yaml_io import YamlIO
from yaml_io import Literal
from node import ROOT_NAME
import settings
import sys
import subprocess
import datetime
from pprint import pformat
from collections import OrderedDict


def remove_space_before_new_line(string):
    return ''.join([line.rstrip() + '\n' for line in string.splitlines()])


class PipelineExecutor():
    _pipeline = None
    _print_only = False
    _force_execution = False

    @property
    def print_only(self):
        return self._print_only

    @print_only.setter
    def print_only(self, value):
        self._print_only = value

    @property
    def force_execution(self):
        return self._print_only

    @force_execution.setter
    def force_execution(self, value):
        self._force_execution = value

    def _print_progression(self, desc, prog, is_ok):
        if is_ok:
            color = settings.OKGREEN
        else:
            color = settings.FAIL

        eol = settings.ENDC + settings.RETURN
        msg = "{0}{1}: {2:.0%}{3}".format(color,
                                          desc,
                                          prog,
                                          eol)
        print(msg, end="")

        sys.stdout.flush()

    def execute(self, node_name=None):
        if node_name is None or node_name == ROOT_NAME:
            node = self._pipeline.root
        else:
            try:
                node = self._pipeline.nodes[node_name]
            except KeyError:
                msg = ("Unable to find node '" +
                       settings.FAIL + "{}".format(node_name) + settings.ENDC +
                       settings.BOLD + "'.\n in pipeline")
                logging.critical(msg)
                raise
            if self._print_only:
                self._print_one_node(node)
            else:
                self._execute_one_node(node)
        for n in self._pipeline.walk(node):
            if self._print_only:
                self._print_one_node(n)
            else:
                self._execute_one_node(n)

    def _execute_one_node(self, node):
        pass

    def _print_one_node(self, node):
        if self._print_only:
            print(settings.BOLD, "\nExecuting: ", node.name, settings.ENDC)
            for scope_value in node.scope.values:
                evaluator = Evaluator(scope_value)
                cmd_str = evaluator.evaluate(" ".join(node.cmd))
                print(cmd_str)

    def _execute_one_scope_value(self, node, scope_value, scope_value_status):
        return_status = scope_value_status
        # First we check if we actually need to launch the command.
        previous_succes = True
        try:
            assert scope_value_status["status"] == "SUCCESS"
        except (AssertionError, KeyError):
            previous_succes = False
        # Update context if previous success.
        if previous_succes:
            return_status["context"] = "NO_WORK_TO_DO"

        evaluator = Evaluator(scope_value)
        cmd = [evaluator.evaluate(arg) for arg in node.cmd]

        cmd_str = " ".join(cmd)
        return_status["cmd"] = cmd_str

        if not previous_succes or self._force_execution:
            try:
                output = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
                return_status["execution_date"] = datetime.datetime.now()

                # decode bytes output with encoding used by stdout
                # and then use the dumb litteral class derived from str
                # so it will be dump as litteral by PyYAML (see yaml_io module)
                output = output.decode(sys.stdout.encoding)
                # We have to remove all space before \n otherwise PyYAML fail
                # to dump it as a literal
                output = remove_space_before_new_line(output)
                return_status["status"] = "SUCCESS"
                return_status["context"] = "EXECUTED"
                return_status["message"] = Literal(output + "\n")

            except subprocess.CalledProcessError as err:
                error = err.output.decode(sys.stdout.encoding)
                return_status["status"] = "FAILURE"
                return_status["context"] = "ERROR"
                error = remove_space_before_new_line(error)
                return_status["message"] = Literal(error + "\n")
            except PermissionError as perm_err:
                logging.error("Permission denied to launch '%s':\n%s",
                              " ".join(cmd),
                              perm_err)
                return_status["status"] = "FAILURE"
                return_status["context"] = "PERMISSION_DENIED"
                perm_err = remove_space_before_new_line(perm_err.strerror)
                return_status["message"] = Literal(perm_err + "\n")
            except FileNotFoundError as file_err:
                # This exception is raised if the first arg of cmd
                # is not a valid comand.
                return_status["status"] = "FAILURE"
                return_status["context"] = "COMMAND_NOT_FOUND"
                file_err = remove_space_before_new_line(file_err.strerror)
                return_status["message"] = Literal(file_err + "\n")
            except TypeError as type_err:
                return_status["status"] = "FAILURE"
                return_status["context"] = "BAD FORMAT"
                type_err = remove_space_before_new_line(type_err.strerror)
                return_status["message"] = Literal(type_err + "\n")

        return return_status


class ThreadedPipelineExecutor(PipelineExecutor):
    _max_workers = 0
    scope_values = None

    _LOCK = futures.thread.threading.Lock()

    def __init__(self, pipeline, max_workers):
        self._max_workers = max_workers
        self._pipeline = pipeline

    def _execute_one_node(self, node):
        """
        Create a pool of thread, submit all the command to launch
        for each scope values of the given node.
        Submitting a command give back a future object which is
        an observer on the state of the command.
        As each command is completed (success or failur) we dump a yaml
        document resuming the state of all command and update the progression
        on the standard output.
        """

        # A dictionary Key are the scope value,
        # value is the staus of the corresponding command
        # This dict is what is load/dump in yaml
        max_workers = self._max_workers * node.workers_modifier

        node_filname = settings.PRESTO_DIR.joinpath(node.name +
                                                    settings.NODE_EXEC_SUFFIX)
        if node_filname.exists():
            scope_values_status = YamlIO.load_yaml(node_filname)
        else:
            scope_values_status = dict()

        # A dictionary that list all the observer
        # and its corresponding scope_value.
        scope_values_observer = dict()

        # A list of the scope value for which the cmd fail
        scope_values_failed = []
        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            for scope_value in node.scope.values:
                scope_value_status = OrderedDict()
                scope_value_status["execution_date"] = ""
                scope_value_status["status"] = ""
                scope_value_status["context"] = ""
                scope_value_status["cmd"] = ""
                scope_value_status["message"] = Literal("\n")
                try:
                    # ugly trick to reorder
                    d = scope_values_status[scope_value]
                    scope_value_status["execution_date"] = d["execution_date"]
                    scope_value_status["status"] = d["status"]
                    scope_value_status["context"] = d["context"]
                    scope_value_status["cmd"] = d["cmd"]
                    scope_value_status["message"] = Literal(d["message"])
                except KeyError:
                    pass
                observer = ex.submit(self._execute_one_scope_value,
                                     node,
                                     scope_value,
                                     scope_value_status)
                # fill a dictionary with observer as Key
                scope_values_observer[observer] = scope_value

            progression = 0
            is_ok = True
            for future in futures.as_completed(scope_values_observer.keys()):
                scope_value = scope_values_observer[future]
                status = future.result()
                # Key is used to get the double quoted style in the yaml doc
                scope_values_status[scope_value] = status
                if status["status"] == "SUCCESS":
                    progression += 1
                else:
                    is_ok = False
                    scope_values_failed.append(scope_value)
                # show progression
                with self._LOCK:
                    progression_percent = progression / len(node.scope.values)
                    self._print_progression(node.description,
                                            progression_percent, is_ok)
                # dump results, must be here in case after each futur
                # get completed so yaml results are always OK even if user
                # plug off the computer.
                YamlIO.dump_yaml(scope_values_status, node_filname)
        # print new line
        print("")
        if scope_values_failed:
            logging.error("Failed scope value: \n%s", pformat(scope_values_failed))
