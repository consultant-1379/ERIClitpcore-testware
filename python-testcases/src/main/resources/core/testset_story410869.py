"""
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     June 2020
@author:    Bryan McNulty
@summary:   Test for story TORF-410869: As a LITP Developer I
            want the ability to run a LITP initial install plan
            on RHEL 7.7 to apply updates on the LITP Management
            Server
"""
from litp_generic_test import GenericTest, attr
from litp_cli_utils import CLIUtils


class Story410869(GenericTest):
    '''
    As a LITP User I want to be able to retrieve the version information,
    so that I can provide this info when troubleshooting issues
    '''

    def setUp(self):
        """
        Description:
            Runs before every single test
        """
        # 1. Call super class setup
        super(Story410869, self).setUp()
        self.cli = CLIUtils()
        self.ms_node = self.get_management_node_filename()

    def tearDown(self):
        """
        Description:
            Runs after every test to perform the test teardown/cleanup
        """
        # call super class teardown
        super(Story410869, self).tearDown()

    @attr('all', 'revert', 'story410869', 'story410869_tc03')
    def test_03_p_verify_run_plan_help(self):
        """
        @tms_id: TORF-410869_tc_03
        @tms_requirements_id: TORF-410869
        @tms_title: Verify run plan help is correct.
        @tms_description: Verify help for "litp run_plan -h"
        @tms_test_steps:
            @step: Run the command "litp run_plan --help".
            @result: The correct output is displayed.
            @step: Run the command "litp run_plan -h".
            @result: The correct output is displayed.
        @tms_test_precondition: Litp installed on RHEL7
        @tms_execution_type: Automated
        """
        output = ['Usage: litp run_plan [-h] [-j] [--resume]',
                  'Executes the tasks in a plan to deploy the deployment' \
                      ' model.',
                  'Optional Arguments:',
                  '-h, --help  Show this help message and exit',
                  '-j, --json  Output raw JSON response from server',
                  '--resume    Resume failed plan',
                  'Example: litp run_plan']
        help_cmds = ["--help", "-h"]
        for help_cmd in help_cmds:
            cmd = "{0} {1} {2}".format(self.cli.litp_path, 'run_plan',
                                       help_cmd)
            stdout, _, _ = \
                self.run_command(self.ms_node, cmd, add_to_cleanup=False)
            self.assertEqual(output, stdout, 'The test output for \"{0}\"' \
                                      ' cmd does not match expected output')
