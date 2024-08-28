"""
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     September 2016, Refactored May 2019
@author:    Maurizio Senno, Yashi Sahu
@summary:   TORF-107213
            As a LITP architect I want to replace the existing legacy storage
            solution with a data tier, Celery and PuppetDB

"""
from litp_generic_test import GenericTest, attr
import test_constants as const


class Story107213(GenericTest):
    """
        As a LITP architect I want to replace the existing legacy storage
        solution with a data tier, Celery and PuppetDB
    """

    def setUp(self):
        """ Runs before every test """
        super(Story107213, self).setUp()
        self.ms_node = self.get_management_node_filename()
        self.deploy_url = '/deployments'

    def tearDown(self):
        """ Runs after every single test """
        super(Story107213, self).tearDown()

    @attr('all', 'revert', 'story107213', 'story107213_tc24')
    def test_24_n_issue_litp_command_when_postgres_db_unreachable(self):
        """
        @tms_id: torf_107213_tc_24
        @tms_requirements_id: TORF-107213
        @tms_title: Verify that if the DB is unreachable when a LITP
                    command is entered an error is thrown.
        @tms_description: Verify that if the DB is unreachable when
                   a LITP command is entered an error is thrown.
        @tms_test_steps:
            @step: Wait until the current "puppet" run and the subsequent
                one has completed before stopping the "postgresql" service.
            @result: "Puppet" run has successfully completed its
                cycle and the "postgresql" service has stopped successfully
            @step: Stop the "postgresql" service and issue a LITP command
                to verify the error message.
            @result: The "postgresql" service has successfully stopped and
                an error is thrown.
            @step: Wait for the "postgresql" service to restart
                automatically.
            @result: The "postgresql" service has restarted successfully.
            @step: Issue a LITP command "litp show".
            @result: LITP command "litp show" has completed successfully.
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """

        self.log('info',
        '1. Waiting until the current "puppet" run and a subsequent '
        'one has completed before stopping the postgresql database')
        self.start_new_puppet_run(self.ms_node)
        self.wait_for_puppet_idle(self.ms_node,
                                  node_hostname=self.ms_node)

        self.log('info',
        '2. Stop the "postgresql" service and issue a LITP command to '
        'verify the error message.')
        self.stop_service(self.ms_node, const.PSQL_SERVICE_NAME)
        expected_err = [self.deploy_url, 'ServerUnavailableError    '
                                        'A dependent service is unavailable']
        stderr = self.execute_cli_show_cmd(self.ms_node, self.deploy_url,
                                           expect_positive=False)[1]
        self.assertEqual(expected_err, stderr, "Postgresql service is "
                                               "not stopped")

        self.log('info',
        '3. Wait for "postgresql" to be restarted by "puppet"')
        cmd = '{0} {1} status' .format(const.SERVICE_PATH,
                                         const.PSQL_SERVICE_NAME)
        puppet_wait = self.wait_for_puppet_action(self.ms_node, self.ms_node,
                                    cmd, 0, su_root=True)
        self.assertTrue(puppet_wait, "postgresql is not restarted by puppet")

        self.log('info', '4. Verify that LITP command is successful '
           'after "postgresql" is back up and running')
        cmd = self.cli.get_show_cmd(self.deploy_url)
        litp_up = self.wait_for_cmd(self.ms_node, cmd, 0,
                                        timeout_mins=10)
        self.assertTrue(litp_up, '"litp" command failed to become'
                        'available after "postgresql" started')
