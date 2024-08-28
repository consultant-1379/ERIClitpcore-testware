'''
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     April 2014
@author:    Luke Murphy
@summary:   Integration test for @todo
            Agile: @todo Epic: @todo Story: @todo Sub-Task: @todo
'''

import os
import ast
import re
import test_constants
from json_utils import JSONUtils
from litp_generic_test import GenericTest, attr
from redhat_cmd_utils import RHCmdUtils


class Story3330(GenericTest):
    """As a system designer I want extend the Callback API with Mcollective RPC
       calls, so that I keep plug-in logic within the plug-in rather than
       implement within the RPC agent code.
    """

    def setUp(self):
        """runs before every test to perform setup"""
        super(Story3330, self).setUp()
        self.test_ms = self.get_management_node_filename()
        self.rhcmd = RHCmdUtils()
        self.json = JSONUtils()
        self.litp_log_path = test_constants.GEN_SYSTEM_LOG_PATH
        # regular expression performs a look behind for strings that contain a
        # '{' preceded by a whitespace, followed by any number of characters
        # and ends with a look behind for '}' that ends with another '}'; used
        # to identify JSON formatted strings
        self.regex = '\\{(?=\')[:,\'\\w].+(?<=\\})'

    def tearDown(self):
        """runs after every test to perform cleanup"""
        super(Story3330, self).tearDown()

    def get_hostnames_from_model(self):
        """get the node hostnames from the model tree"""

        hostnames = list()

        nodes = self.find(self.test_ms, '/deployments', 'node')
        nodes.append('/ms')

        for node in nodes:
            hostnames.append(
                self.execute_show_data_cmd(
                    self.test_ms, node, 'hostname'
                )
            )

        return hostnames

    def execute_common_methods(self, test_, plan_state, log_type):
        """execute a series of common test methods"""

        # install the plugin rpms if required
        self._install_rpms()

        # get current log length
        start_log_pos = self.get_file_len(self.test_ms, self.litp_log_path)

        # run the litp create command
        # build path to avoid hardcoding
        software_path = os.path.join(
            self.find(self.test_ms, "/software", "software-item", False)[0],
            test_
        )
        self.execute_cli_create_cmd(
            self.test_ms, software_path, "story3330",
            props="name={0}".format(test_)
        )
        self.execute_cli_createplan_cmd(self.test_ms)
        self.execute_cli_runplan_cmd(self.test_ms)
        self.assertTrue(self.wait_for_plan_state(self.test_ms, plan_state),
        "Unexpected plan state")

        # get the log length
        curr_log_pos = self.get_file_len(self.test_ms, self.litp_log_path)
        test_log_len = curr_log_pos - start_log_pos

        # grep the log file for the Mcollective output
        # get all lines that are debug level 'INFO'
        std_out, std_err, rcode = self.run_command(
            self.test_ms,
            RHCmdUtils().get_grep_file_cmd(
                self.litp_log_path, log_type,
                file_access_cmd="tail -n {0}".format(test_log_len)
            )
        )
        self.assertNotEqual([], std_out)
        self.assertEqual([], std_err)
        self.assertEqual(0, rcode)

        return std_out

    def _install_rpms(self):
        """
        Description:
        Method that installs plugin and extension
        if they are not already installed
        """
        # Check if the plugin is already installed
        plugin_id = 'story3330'
        _, _, rcode = self.run_command(
            self.test_ms, self.rhc.check_pkg_installed([plugin_id]),
            su_root=True)

        # If not, copy plugin and extension onto MS
        if rcode == 1:
            local_rpm_paths = self.get_local_rpm_path_ls(
                os.path.abspath(
                    os.path.join(os.path.dirname(__file__), 'plugins')
                ),
                plugin_id
            )
            self.assertTrue(
                self.copy_and_install_rpms(self.test_ms, local_rpm_paths))

    @attr('all', 'non-revert')
    def test_01_p_rpc_task_success(self):
        """
            Description:
                Using a dummy test extension and plugin that are packaged
                into RPMs, install them on the MS and using a litp create
                command to execute a Mcollective command and assert that the
                return output is correct. The dummy extension defines a new
                model extension type 'story3330' which extends 'software-item',
                and then test plugin uses a CallbackTask to execute the
                Mcollective command.
            Actions:
                1. Get position of log file for start of test
                2. Install test plugin
                3. Run litp create command which triggers plugin code
                4. Grep section of logs for plugin code output
                5. Load the output into JSON and assert correct contents
            Result:
                Mcollective RPC calls located in plugin code is proven
                to execute correctly
        """

        # execute the common test methods
        std_out = self.execute_common_methods("test_01",
            test_constants.PLAN_COMPLETE, "INFO")

        # load it to JSON
        for line in std_out:
            # search each line for JSON format text based on the regular
            # expression and if found, load into JSON
            matched = re.search(self.regex, line)
            if matched:
                # matched string is not valid JSON, using literal_eval, will
                # convert to dict, then JSOn dump to make a valid JSON string
                # and JSON load to create a valid JSON object
                json_obj = self.json.load_json(
                    self.json.dump_json(ast.literal_eval(matched.group(0)))
                )
                self.assertTrue(isinstance(json_obj, dict))

        # assert that we got the correct output
        for hostname in self.get_hostnames_from_model():
            self.assertTrue(self.is_text_in_list(hostname, json_obj.keys()),
                "Host '{0}' not found in '{1}'".format(hostname, json_obj))
            # check for json object values
            self.assertEqual(
                'running', json_obj[hostname]['data']['status'])
            self.assertEqual('', json_obj[hostname]['errors'])

    @attr('all', 'non-revert')
    def test_02_n_rpc_task_failure(self):
        """
            Description:
                Using a dummy test extension and plugin that are packaged
                into RPMs, install them on the MS and using a litp create
                command to execute a Mcollective command (will fail by design)
                and assert that the return output is correct.
                The dummy extension defines a new model extension type
                'story3330' which extends 'software-item', and then test
                plugin uses a CallbackTask to execute the Mcollective command.
            Actions:
                1. Get position of log file for start of test
                2. Install test plugin
                3. Run litp create command which triggers plugin code
                4. Grep section of logs for plugin code output
                5. Load the output into JSON and assert correct contents
                   (negative)
            Result:
                Mcollective RPC calls located in plugin code is proven
                to log correct error message in the negative case
        """
        # execute the common test methods
        std_out = self.execute_common_methods("test_02",
            test_constants.PLAN_FAILED, "ERROR")

        # load it to JSON
        for line in std_out:
            # search each line for JSON format text based on the regular
            # expression and if found, load into JSON
            matched = re.search(self.regex, line)
            if matched:
                # matched string is not valid JSON, using literal_eval, will
                # convert to dict, then JSOn dump to make a valid JSON string
                # and JSON load to create a valid JSON object
                json_obj = self.json.load_json(
                    self.json.dump_json(ast.literal_eval(matched.group(0)))
                )
                self.assertTrue(isinstance(json_obj, dict))

        # assert that we got the correct output
        for hostname in self.get_hostnames_from_model():
            self.assertTrue(self.is_text_in_list(hostname, json_obj.keys()),
                "Host '{0}' not found in '{1}'".format(hostname, json_obj))
            # check for json object values
            self.assertNotEqual('', json_obj[hostname]['errors'])

    @attr('all', 'non-revert')
    def test_03_n_rpc_task_timeout(self):
        """
            Description:
                Using a dummy test extension and plugin that are packaged
                into RPMs, install them on the MS and using a litp create
                command to execute a Mcollective command
                (will timeout by design) and assert that the return
                output is correct. The dummy extension defines a new
                model extension type 'story3330' which extends
                'software-item', and then test plugin uses a CallbackTask
                to execute the Mcollective command.
            Actions:
                1. Get position of log file for start of test
                2. Install test plugin
                3. Run litp create command which triggers plugin code
                4. Grep section of logs for plugin code output
                5. Load the output into JSON and assert correct contents
                   (negative)
            Result:
                Mcollective RPC calls located in plugin code will
                log correct messages for commands that time out
        """
        # execute the common test methods
        std_out = self.execute_common_methods("test_03",
            test_constants.PLAN_FAILED, "ERROR")

        # load it to JSON
        for line in std_out:
            # search each line for JSON format text based on the regular
            # expression and if found, load into JSON
            matched = re.search(self.regex, line)
            if matched:
                # matched string is not valid JSON, using literal_eval, will
                # convert to dict, then JSOn dump to make a valid JSON string
                # and JSON load to create a valid JSON object
                json_obj = self.json.load_json(
                    self.json.dump_json(ast.literal_eval(matched.group(0)))
                )
                self.assertTrue(isinstance(json_obj, dict))

        # assert that we got the correct output
        for hostname in self.get_hostnames_from_model():
            host_timeout = '{0}timeout'.format(hostname)
            self.assertTrue(self.is_text_in_list(host_timeout,
                json_obj.keys()),
            "Host '{0}' not found in '{1}'".format(host_timeout, json_obj))
            # check for json object values
            self.assertNotEqual('', json_obj[host_timeout]['errors'])
            self.assertTrue(self.is_text_in_list('No answer from',
                [json_obj[host_timeout]['errors']]),
            "Expected error message 'No answer from' not found in '{0}'".\
                format(json_obj[host_timeout]['errors']))

    @attr('all', 'non-revert')
    def test_04_n_rpc_task_invalid_args(self):
        """
            Description:
                Using a dummy test extension and plugin that are packaged
                into RPMs, install them on the MS and using a litp create
                command to execute a Mcollective command (will fail by design)
                and assert that a python exception is logged due to invalid
                arguments passed to the CallbackTask().
                The dummy extension defines a new model extension type
                'story3330' which extends 'software-item', and then test
                plugin uses a CallbackTask to execute the Mcollective command.
            Actions:
                1. Get position of log file for start of test
                2. Install test plugin
                3. Run litp create command which triggers plugin code
                4. Grep section of logs for python exception

            Result:
                Task failure due to python exception from invalid arguments
                passed to callback
        """
        # execute the common test methods
        std_out = self.execute_common_methods("test_04",
            test_constants.PLAN_FAILED, "ERROR")

        # check python exception logged for invalid arguments
        self.assertTrue(self.is_text_in_list(
            'Exception running task', std_out),
        "Expected python exception message '{0}' not found in stdout: '{1}'".\
            format('Exception running task', std_out))
