#!/usr/bin/python
# -*- coding: utf-8 -*-
# author:   Jan Hybs
import threading
import subprocess

import sys

import time

import psutil
from scripts.core.base import Printer
from scripts.execs.test_executor import ProcessUtils
from utils.counter import ProgressCounter
from utils.events import Event
from utils.globals import ensure_iterable


class ExtendedThread(threading.Thread):
    def __init__(self, name, target=None):
        super(ExtendedThread, self).__init__(name=name)
        self.started = None
        self.target = target

        self._is_over = True
        self._returncode = None

        # create event objects
        self.on_start = Event()
        self.on_complete = Event()

    def _run(self):
        if self.target:
            self.target()

    @property
    def returncode(self):
        return self._returncode

    @returncode.setter
    def returncode(self, value):
        self._returncode = value

    def run(self):
        self._is_over = False
        self.on_start(self)
        self._run()
        self._is_over = True
        self.on_complete(self)

    def is_over(self):
        return self._is_over

    def is_running(self):
        return not self._is_over


class BinExecutor(ExtendedThread):
    """
    :type process: psutil.Popen
    :type threads: list[scripts.core.threads.BinExecutor]
    """
    threads = list()

    @staticmethod
    def register_sigint():
        import signal
        signal.signal(signal.SIGINT, BinExecutor.signal_handler)

    @staticmethod
    def signal_handler(signal, frame):
        if signal:
            sys.stderr.write("\nError: Caught SIGINT! Terminating application in peaceful manner...\n")
        else:
            sys.stderr.write("\nError: Terminating application threads\n")
        # try to kill all running processes
        for executor in BinExecutor.threads:
            try:
                if executor.process.is_running():
                    sys.stderr.write('\nTerminating process {}...\n'.format(executor.process.pid))
                    ProcessUtils.secure_kill(executor.process)
            except Exception as e:
                pass
        sys.exit(1)
        raise Exception('You pressed Ctrl+C!')

    def __init__(self, command, name='exec-thread'):
        super(BinExecutor, self).__init__(name)
        BinExecutor.threads.append(self)
        self.command = [str(x) for x in ensure_iterable(command)]
        self.process = None
        self.stdout = subprocess.PIPE
        self.stderr = subprocess.PIPE

    def _run(self):
        # run command and block current thread
        try:
            self.process = psutil.Popen(self.command, stdout=self.stdout, stderr=self.stderr)
            self.process.wait()
        except Exception as e:
            # broken process
            self.process = BrokenProcess(e)
        self.returncode = getattr(self.process, 'returncode', None)


class BrokenProcess(object):
    def __init__(self, exception=None):
        self.exception = exception
        self.pid = -1
        self.returncode = 666

    @staticmethod
    def is_running():
        return False


class MultiThreads(ExtendedThread):
    """
    :type threads: list[scripts.core.threads.ExtendedThread]
    """
    def __init__(self, name, progress=False):
        super(MultiThreads, self).__init__(name)
        self.threads = list()
        self.returncodes = dict()
        self.running = 0
        self.stop_on_error = False
        self.counter = None
        self.progress = progress
        self.counter = None
        self.index = 0
        self.stopped = False

    def run_next(self):
        if self.stopped:
            return False
        if self.index >= self.total:
            return False

        self.index += 1

        if self.counter:
            self.counter.next(locals())

        self.threads[self.index - 1].start()
        return True

    def add(self, thread):
        """
        :type thread: scripts.core.threads.ExtendedThread
        """
        self.threads.append(thread)
        self.returncodes[thread] = None
        thread.on_start += self.on_thread_start
        thread.on_complete += self.on_thread_complete

    @property
    def current_thread(self):
        return self.threads[self.index -1]

    @property
    def returncode(self):
        return max(self.returncodes.values()) if self.returncodes else None

    @property
    def total(self):
        return len(self.threads)

    def on_thread_start(self, thread):
        """
        :type thread: scripts.core.threads.ExtendedThread
        """
        self.running += 1

    def on_thread_complete(self, thread):
        self.returncodes[thread] = thread.returncode
        self.running -= 1

    # aliases
    __len__ = total
    __iadd__ = add
    append = add


class SequentialThreads(MultiThreads):
    def __init__(self, name, progress=True, indent=False):
        super(SequentialThreads, self).__init__(name, progress)
        self.thread_name_property = False
        self.indent = indent

    def _run(self):
        if self.progress:
            if self.thread_name_property:
                self.counter = ProgressCounter('{self.name}: {:02d} of {self.total:02d} | {self.current_thread.name}')
            else:
                self.counter = ProgressCounter('{self.name}: {:02d} of {self.total:02d}')

        if self.indent:
            Printer.open()

        while True:
            if not self.run_next():
                break
            self.current_thread.join()

            if self.stop_on_error and self.current_thread.returncode > 0:
                self.stopped = True
                break

        if self.indent:
            Printer.close()


class ParallelThreads(MultiThreads):
    def __init__(self, n=4, name='runner', progress=True):
        super(ParallelThreads, self).__init__(name, progress)
        self.n = n if type(n) is int else 1
        self.counter = ProgressCounter('Case {:02d} of {self.total:02d}')
        self.printer = Printer(Printer.LEVEL_KEY)
        self.stop_on_error = True

    def on_thread_complete(self, thread):
        """
        :type thread: scripts.core.threads.ExtendedThread
        """
        super(ParallelThreads, self).on_thread_complete(thread)
        if self.stop_on_error > 0 and thread.returncode:
            self.stopped = True
            BinExecutor.signal_handler(None, None)
            sys.exit(1)

    def ensure_run_count(self):
        if self.stopped:
            return False
        if self.index >= self.total:
            return False

        if self.running < self.n:
            self.run_next()
        return True

    def _run(self):
        # start first thread which will cascade to start next threads if necessarily
        while True:
            if not self.ensure_run_count():
                break
            time.sleep(1)


