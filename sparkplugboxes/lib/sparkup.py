import abc
import gevent
from datetime import datetime
from inspect import getmembers, isfunction
from socketio.namespace import BaseNamespace


class SparkUpNamespace(BaseNamespace):
    """
    Abstract class to setup a server
    """
    __metaclass__ = abc.ABCMeta

    def __init__(self, environ, ns_name):
        """
        Initialize global variables to be used
        for status messages and progress
        """
        super(SparkUpNamespace, self).__init__(environ, ns_name)

        # TODO: Remove the region declaration from here to pymongo
        self.region = {
            'id': 'local',
            'name': 'Localhost',
            'domain': 'localhost',
            'folder': '/Applications/XAMPP/htdocs',
            'mysqlUsername': 'root',
            'mysqlPassword': '',
            'mysqlBin': '/usr/bin/mysql',
            'EXEC': " -u%s -p%s --host=localhost -f -e '" % (
                self.region['mysqlUsername'], self.region['mysqlUsername']),
            'FLUSH': 'FLUSH PRIVILEGES',
            'USER_MAX_LEN': 16
        }

        self.sparkup_abort = False
        self.sparkup_error = ''
        self.sparkup_message = ''
        self.sparkup_console = []
        self.sparkup_checklist = {
            'download': 0,
            'install': 0
        }

        self.box_data = {
            'id': None,
            'name': None,
            'username': None,
            'password': None,
            'email': None,
            'mysqlId': None,
            'mysqlPwd': None,
        }

        self.spawn_job_progress = None
        self.allow_reconnect = False

    def initialize(self):
        """
        Initialize all the global properties here
        Retrive region specific details,
        """
        if self.allow_reconnect:
            self.spawn_job_progress = self.spawn(self.job_progress)

    def recv_disconnect(self):
        """
        Keep the connection going, flag reconnection
        and kill spawned processes
        """
        self.spawn_job_progress.kill()
        self.allow_reconnect = True

    def recv_connect(self):
        """
        Register the box id to setup
        :return:
        """

    def log(self, message):
        self.sparkup_message = message
        self.sparkup_console.append({
            'message': message,
            'time': str(datetime.now().time()),
        })

    def abort(self, message=""):
        if message == "":
            message = "Sorry we couldn't setup your box!"

        self.sparkup_abort = True
        self.log(message)

    def complete(self, message=""):
        if message == "":
            message = "You'r box has been setup! Redirecting now .."

        self.log(message)
        self.disconnect()

    def on_start(self, box_data):
        self.box_data = box_data
        self.spawn_job_progress = self.spawn(self.job_progress)

        functions_list = [o for o in getmembers(self) if isfunction(o[1])]
        for func in (val for key, val in functions_list if key.startswith('task_')):
            func()

    @abc.abstractmethod
    def job_progress(self):
        """
        This function sends the current box setup status to the client
        """
        while not self.sparkup_abort:

            total_checks = len(self.sparkup_checklist.values())
            checks = sum(self.sparkup_checklist.values())

            self.emit('status', {
                'message': self.sparkup_message,
                'console': self.sparkup_console,
                'checks': checks,
                'total': total_checks
            })
            gevent.sleep(1)

            if checks == total_checks:
                self.complete()

        if self.sparkup_abort:
            self.emit('setup_failure', {
                'message': 'Sorry :( We could not setup your box ...'
            })
            self.disconnect()

    @abc.abstractmethod
    def task_download(self):
        """
        Download all the setup related content
        and add the task to the global checklist
        :return: Task status message
        """
        self.sparkup_checklist.update({
            'download': 0
        })
        pass

    @abc.abstractmethod
    def task_install(self):
        """
        Installation procedure to be added here
        :return: Task status message
        """
        self.sparkup_checklist.update({
            'install': 0
        })
        pass