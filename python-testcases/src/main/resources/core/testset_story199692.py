"""
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     July 2017, Refactored on May 2019
@author:    Laura Forbes, Refactored by Yashi Sahu
@summary:   TORF-199692
            Optimise "puppet" timer configuration to improve performance on
            larger systems and minimise occurrence of 'execution expired'
"""

from litp_generic_test import GenericTest, attr
import test_constants as const
from redhat_cmd_utils import RHCmdUtils


class Story199692(GenericTest):
    """
        Optimise "puppet" timer configuration to improve performance on
        larger systems and minimise occurrence of 'execution expired'
    """

    def setUp(self):
        """ Runs before every single test """
        super(Story199692, self).setUp()
        self.rhcmd = RHCmdUtils()
        self.ms_node = self.get_management_node_filename()
        self.mn_nodes = self.get_managed_node_filenames()
        self.all_nodes = [self.ms_node] + self.mn_nodes
        self.run_interval = "runinterval"
        self.run_interval_expected = self.run_interval = "1800"
        self.config_timeout = "configtimeout"
        self.config_timeout_expected = self.config_timeout = "1720"
        self.expected_values = [self.run_interval_expected,
                                self.config_timeout_expected]

    def tearDown(self):
        """ Runs after every single test """
        super(Story199692, self).tearDown()

    @attr('all', 'revert', 'story199692', 'story199692_tc06')
    def test_06_p_correct_values_in_conf_file(self):
        """
        @tms_id: torf_199692_tc06
        @tms_requirements_id: TORF-199692
        @tms_title: "Puppet" conf file has correct values
        @tms_description: Verify that the "puppet" config files on
            the MS and all peer nodes have the correct values for
            'runinterval' and 'configtimeout'.
        @tms_test_steps:
            @step: Grep the "puppet" conf file on all nodes for 'runinterval'
                and 'configtimeout' parameters and ensure they have
                the correct values.
            @result: Parameters are set to the correct
                values as expected.
        @tms_test_precondition: None
        @tms_execution_type: Automated
        """
        self.log('info', "1. Grep the 'puppet' conf file on all nodes "
                         "and assert that the 'runinterval' and "
                         "'configtimeout' parameters are set to "
                         "correct values ")
        cmd = self.rhcmd.get_grep_file_cmd(const.PUPPET_CONFIG_FILE,
                            [self.run_interval_expected,
                            self.config_timeout_expected])
        for node in self.all_nodes:
            correct_value = self.run_command(node, cmd, su_root=True,
                                             default_asserts=True)[0]
            for value in self.expected_values:
                self.assertTrue(any(value in s for s in correct_value),
                "Expected '{0}' not found in {1} on {2}".format(value,
                 const.PUPPET_CONFIG_FILE, node))
