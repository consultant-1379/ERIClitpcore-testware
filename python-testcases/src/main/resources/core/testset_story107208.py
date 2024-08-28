"""
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     August 2016
@author:    Maurizio Senno
@summary:   TORF-107208
            As a LITP installer I want to configure PuppetDB on the system
            to hold supplement node information
"""
from litp_generic_test import GenericTest, attr


class Story107208(GenericTest):
    """
        As a LITP installer I want to configure PuppetDB on the system
        to hold supplement node information
    """

    def setUp(self):
        """ Runs before every single test """
        super(Story107208, self).setUp()
        self.ms1 = self.get_management_node_filenames()[0]

    def tearDown(self):
        """ Runs after every single test """
        super(Story107208, self).tearDown()

    @attr('all', 'revert', 'story107208', 'story107208_tc01')
    def test_01_p_verify_that_puppetdb_is_installed(self):
        """
        @tms_id:
            torf_107208_tc_01
        @tms_requirements_id:
            TORF-107208
        @tms_title:
            Verify that puppedDB is enabled on the MS system
        @tms_description:
            Verify that puppedDB is enabled on the MS system
        @tms_test_steps:
        @step: Run the command "ps aux | grep -i puppetdb | grep -v grep"
        @result: At least one postgres process owned by puppedb is found

        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        cmd = 'ps aux | grep -i puppetdb | grep -v grep'
        stdout, _, _ = self.run_command(self.ms1, cmd, default_asserts=True)
        self.assertTrue(len(stdout) > 0,
            'No "puppetdb" processes were found running on system')
