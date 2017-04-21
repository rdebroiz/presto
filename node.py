import logging
import settings
from settings import FAIL, ENDCBOLD
from pprint import pformat

ROOT_NAME = "root"


class Node():
    _description = None
    _scope = None
    _name = None
    _cmd = None
    _workers_modifier = None
    _parents = None
    _cmd_for_value = None

    def __init__(self, yaml_doc):
        # initialise mutable attributs
        self._parents = set()
        self._parents.add(ROOT_NAME)
        self._cmd_for_value = dict()

        from data_model import DataModel
        from evaluator import Evaluator

        try:
            self._name = yaml_doc['__NAME__']
        except KeyError:
            logging.error("Missing '__NAME__' key. YAML document:\n"
                          "{}".format(yaml_doc))
            raise

        try:
            self._description = yaml_doc['__DESCRIPTION__']
        except KeyError:
            logging.error("Missing '__DESCRIPTION__' key. YAML document:\n"
                          "{}".format(yaml_doc))
            raise

        try:
            scope_name = yaml_doc['__SCOPE__']
        except KeyError:
            logging.error("Missing '__SCOPE__' key in {}".format(self._name))

        try:
            self._scope = DataModel.scopes[scope_name]
        except KeyError:
            logging.error(settings.FAIL + "'{}'".format(scope_name) +
                          settings.ENDCBOLD +
                          " is not a valid scope, you have declared scopes:\n"
                          "'{}'".format(pformat(DataModel.scopes.keys())))

        try:
            self._cmd = yaml_doc['__CMD__']
        except KeyError:
            logging.error("Missing '__CMD__' key")
            raise

        try:
            self._parents = self._parents.union(yaml_doc['__DEPEND_ON__'])
        except KeyError:
            msg = ("Node '{}' has no '__DEPEND_ON__' section\n"
                   "\tYou should consider to provided it one.\n"
                   "\tDefault behavior: no dependece.".format(self._name))
            logging.warning(msg)
            pass  # root will be the default parent
        except TypeError:
            if yaml_doc['__DEPEND_ON__'] is None:
                msg = ("Node '{}' has an empty '__DEPEND_ON__' section\n"
                       "\tDid you forget to had the dependeces?\n"
                       "\tGive an empty list:  '__DEPEND_ON__ : []' "
                       "\tto have no dependence and no warning\n"
                       "\tDefault behavior: no dependece.".format(self._name))
                logging.warning(msg)
            else:
                raise
        try:
            self._workers_modifier = yaml_doc['__WORKERS_MODIFIER__']
        except KeyError:
            self._workers_modifier = 1
        try:
            if(self._workers_modifier is not None):
                self._workers_modifier = float(self._workers_modifier)
        except TypeError:
            logging.error("__WORKERS_MODIFIER__ must be castable "
                          "in float")
            raise
        self._scope = DataModel.scopes[scope_name]

        # check integrity of the node.
        for scope_value in self._scope.values:
            evaluator = Evaluator(cur_scope_value=scope_value)
            try:
                self._cmd_for_value[scope_value] = [evaluator.evaluate(arg)
                                                    for arg in self._cmd]
            except (TypeError, KeyError):
                logging.critical("Error in node {}.".format(self._name))
                raise

    def __str__(self):
        return ("[--\nname: {0},"
                "\ndescription: {1},"
                "\nscope: {2},"
                "\ncmd: {3},"
                "\nworkers_modifier: {4},"
                "\nparents: {5},"
                "\n--]".format(self._name,
                               self._description,
                               self._scope.name,
                               self._cmd,
                               self._workers_modifier,
                               self._parents))

    def __repr__(self):
        return self.__str__()

    @property
    def description(self):
        return self._description

    @property
    def scope(self):
        return self._scope

    @property
    def name(self):
        return self._name

    @property
    def cmd(self):
        return self._cmd

    @property
    def workers_modifier(self):
        return self._workers_modifier

    @property
    def parents(self):
        return self._parents

    @parents.setter
    def parents(self, value):
        self._parents = value


class Root(Node):
    def __init__(self):
        self._description = ROOT_NAME
        self._name = ROOT_NAME
        self._parents = set()
        self._workers_modifier = 1
        self._cmd = list()
        self._cmd_for_value = dict()

    def __str__(self):
        return ("[--\nname: {0},"
                "\ndescription: {1},"
                "\n--]".format(self._name,
                               self._description))
