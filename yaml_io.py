from concurrent.futures.thread import threading
import logging
import yaml
from collections import OrderedDict


class YamlIO():

    _LOCK = threading.Lock()

    @classmethod
    def load_yaml(cls, yaml_filename):
        """
        Load a single yaml document from a file in a thread safe context.
        """
        try:
            with cls._LOCK:
                yaml_doc = yaml.load(open(yaml_filename, 'r'))
        except OSError:
            logging.critical("Unable to open file %s:", yaml_filename)
            raise
        except (yaml.YAMLError, yaml.scanner.ScannerError):
            logging.critical("Error while parsing file %S:", yaml_filename)
            raise
        return yaml_doc

    @classmethod
    def load_all_yaml(cls, yaml_filename):
        """
        Load a list of yaml documents from a file in a thread safe context.
        """
        try:
            with cls._LOCK:
                yaml_docs = yaml.load_all(open(yaml_filename, 'r'))
            # stream.close()
        except OSError:
            logging.critical("Unable to open file %s:", yaml_filename)
            raise
        except (yaml.YAMLError, yaml.scanner.ScannerError):
            logging.critical("Error while parsing file %s:", yaml_filename)
            raise
        return list(yaml_docs)

    @classmethod
    def dump_yaml(cls, to_dump, yaml_filename):
        """
        Dump a python object inside a yaml document in a thread safe context
        """
        try:
            with cls._LOCK:
                yaml.dump(to_dump, open(yaml_filename, 'w'),
                          default_flow_style=False,
                          allow_unicode=True)
        except OSError:
            logging.critical("Unable to open file %s:", yaml_filename)
            raise
        except (yaml.critical.YAMLError):
            logging.critical("Unable to dump %s in %s:\n",
                             to_dump,
                             yaml_filename)
            raise


# To be able to dump some string as litteral and OrderedDict as regular Dict
class Literal(str):
    """
    Just a dumb class derived from string so object of type literal
    will have a pecific representation (as litteral) when dump by
    the yaml dumper
    """
    pass


def literal_presenter(dumper, data):
    return dumper.represent_scalar(u'tag:yaml.org,2002:str', data, style='|')


def ordered_dict_presenter(dumper, data):
    return dumper.represent_dict(data.items())


yaml.add_representer(Literal, literal_presenter)
yaml.add_representer(OrderedDict, ordered_dict_presenter)
