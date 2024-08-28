'''
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     February 2014
@author:    Maria Varley
@summary:   Integration test for rest API for DEBUG operations
            Agile: STORY LITPCDS-227 (BUG LITPCDS-2203)
'''


from litp_generic_test import GenericTest
from rest_utils import RestUtils
from litp_cli_utils import CLIUtils
from redhat_cmd_utils import RHCmdUtils
import test_constants


class Story227(GenericTest):
    '''
    As a LITP USer I want to enable/disable debug level
    on the TRACE log via the CLI
    '''

    def setUp(self):
        """
        Description:
            Runs before every single test
        Actions:
            1. Call the super class setup method
            2. Set up variables used in the tests
        Results:
            The super class prints out diagnostics and variables
            common to all tests are available.
        """
        # 1. Call super class setup
        super(Story227, self).setUp()
        self.test_nodes = self.get_management_node_filenames()
        self.assertNotEqual([], self.test_nodes)
        self.test_node = self.test_nodes[0]
        self.ms_ip_address = self.get_node_att(self.test_node, 'ipv4')
        self.debug_path = "/litp/rest/v1/litp"
        self.restutils = RestUtils(
            self.ms_ip_address, rest_version="", rest_loc=self.debug_path)
        self.cli = CLIUtils()

    def tearDown(self):
        """
        Description:
            Runs after every single test
        Actions:
            1. Perform Test Cleanup
            2. Call superclass teardown
        Results:
            Items used in the test are cleaned up and the
        """
        #Make sure debug is set correctly by restarting and setting debug to on
        self.restart_litpd_service(self.test_node)
        super(Story227, self).tearDown()

    def obsolete_01_p_enable_debug(self):
        """
        This test is covered by:
        testset_story4669.py
        test_01_p_enable_true_rest
        Description:
        Tests that debug can be enabled from the rest interface.

        Actions:
        1. Get the current log file position
        2. Set debug to overide with the rest interface
        3. Assert command executed successfully
        4. Get current log position
        5. Check expected debug log was outputed during the test

        Result:
        Logs report that debug has been switched to overide following
        a call from the rest interface.

        """
        # 0. Restart litpd so we know debug is set to off
        self.restart_litpd_service(self.test_node, False)

        # 1. Get the current log file position
        debug_val_log = "INFO: ModelManager.set_debug(DEBUG)"
        start_log_pos = \
            self.get_file_len(self.test_node,
                              test_constants.GEN_SYSTEM_LOG_PATH)

        # 2. Set debug to overide with the rest interface
        message_data = "{\"properties\": {\"force_debug\": \"true\"} }"
        stdout, stderr, status, = self.restutils.put(
            "/logging", self.restutils.HEADER_JSON, data=message_data)

        # 3. Assert command executed successfully
        self.assertEqual("", stderr)
        self.assertEqual(200, status)
        _, errorlist = self.restutils.get_json_response(stdout)
        self.assertEquals([], errorlist)

        # 4. Get current log position
        curr_log_pos = \
            self.get_file_len(self.test_node,
                              test_constants.GEN_SYSTEM_LOG_PATH)
        test_logs_len = curr_log_pos - start_log_pos

        # 5. Check expected debug log was outputed during the test
        cmd = \
            RHCmdUtils().get_grep_file_cmd(test_constants.GEN_SYSTEM_LOG_PATH,\
                debug_val_log, \
                file_access_cmd="tail -n {0}".format(test_logs_len))
        outlist, errorlist, exitcode = \
            self.run_command(self.test_node, cmd, add_to_cleanup=False)

        # Assert no errors and output is generated from the grep
        self.assertNotEqual([], outlist)
        self.assertEqual(0, exitcode)
        self.assertEqual([], errorlist)
