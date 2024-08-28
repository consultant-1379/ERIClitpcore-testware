##############################################################################
# COPYRIGHT Ericsson AB 2014
#
# The copyright to the computer program(s) herein is the property of
# Ericsson AB. The programs may be used and/or copied only with written
# permission from Ericsson AB. or in accordance with the terms and
# conditions stipulated in the agreement/contract under which the
# program(s) have been supplied.
##############################################################################

from litp.core.plugin import Plugin
#from litp.core.validators import ValidationError
from litp.core.task import CallbackTask
from litp.core.task import ConfigTask
from litp.core.litp_logging import LitpLogger
log = LitpLogger()
import time
import socket
import subprocess
import os


class Bug11610Plugin(Plugin):
    """
    LITP bug11610 plugin
    """

    def create_configuration(self, plugin_api_context):
        """
        Plugin to generate callback task to ensure that node1 is down
        to validate puppet_mco_timeout
        """
        tasks = []
        for node in plugin_api_context.query("node"):
            for pkg in node.query("package"):
                if pkg.name == "telnet" and pkg.get_state() == "Initial":
                    if node.hostname == "node1":
                        tasks.append(
                            CallbackTask(node, "CB task - wait for node down",\
                                    self.cb_wait_callback)
                        )
                    elif node.hostname == "node2":
                        sleep_cmd = "sleep 30"
                        tasks.append(
                            ConfigTask(node, pkg,
                                "Config task - sleep a while",
                                "exec", os.path.join(*('/bin', sleep_cmd))
                            )
                        )
        return tasks

    def cb_wait_callback(self, plugin_api_context):
        node1_ip = socket.gethostbyname('node1')

        timeout = 30
        elapsed_time = 0
        start_time = int(time.time())
        iteration_interval = 2

        while True:
            ret = subprocess.call('ping -c 2 ' + str(node1_ip), shell=True)
            if ret != 0:
                break
            elapsed_time = int(time.time()) - start_time
            if elapsed_time > timeout:
                print 'Callback task timeout while waiting for node1 ' \
                    'to shutdown'
                break
            time.sleep(iteration_interval)
