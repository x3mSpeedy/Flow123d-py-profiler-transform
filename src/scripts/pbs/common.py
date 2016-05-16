#!/usr/bin/python
# -*- coding: utf-8 -*-
# author:   Jan Hybs
import importlib
import json
import platform
from scripts.core.base import Paths, Printer


class DummyModule(object):
    """
    :type template: str
    """

    def __init__(self):
        self.template = None

    def Module(self, test_case, proc_value, filename):
        """
        :rtype : scripts.core.prescriptions.PBSModule
        """
        pass

    def ModuleJob(self, job_id):
        """
        :rtype : scripts.pbs.job.Job
        """
        pass


def get_pbs_module(hostname=None):
    """
    :rtype : scripts.pbs.common.DummyModule
    """
    if not hostname:
        hostname = platform.node()

    # try to get name from json file
    host_file = Paths.join(Paths.source_dir(), 'host_table.json')
    if Paths.exists(host_file):
        with open(host_file, 'r') as fp:
            hosts = json.load(fp)
            pbs_module_path = hosts.get(hostname)
    else:
        hostname = hostname.replace('.', '_')
        pbs_module_path = 'pbs_{}'.format(hostname)
        Printer.out('Warning! no host specified assuming module {}', pbs_module_path)

    # try to get pbs_module
    return importlib.import_module('scripts.pbs.modules.{}'.format(pbs_module_path))