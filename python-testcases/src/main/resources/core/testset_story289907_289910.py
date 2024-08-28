"""
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     December 2018
@author:    Aisling Stafford
@summary:   Integration tests for stories TORF-289907 & TORF-289910
"""
import time
from litp_generic_test import GenericTest, attr
from litp_generic_utils import GenericUtils
import test_constants as const


class Story289907Story289910(GenericTest):
    """
    TORF-289907: As a LITP user I want the Celery processes to run
    as a dedicated non-root user.
    TORF-289910: As a LITP user I want the RabbitMQ processes to run
    as a dedicated non-root user
    """
    def setUp(self):
        """Runs before every test"""

        super(Story289907Story289910, self).setUp()

        self.ms_node = self.get_management_node_filename()
        self.ms_ip = self.get_node_att(self.ms_node, 'ipv4')
        self.celery_user = 'celery'
        self.rabbitmq_user = 'rabbitmq'
        self.celery_processes = ['celery', 'celerybeat']
        self.rabbitmq_process = "rabbitmq-server"
        self.gen_utils = GenericUtils()

    def tearDown(self):
        """Runs after every test"""
        super(Story289907Story289910, self).tearDown()

    def verify_process_ownership(self, expected_process_user):
        """
        Description: Verifies the process has the
                     expected user and group
        Args:
            expected_process_user (str): Expected owner/group of
                                         the process
        """

        cmd = "{0} axfo pid,euser,egroup,args | {1} {2} | {1} -v grep".format(
                                                 const.PS_PATH,
                                                 const.GREP_PATH,
                                                 expected_process_user)

        process_output, _, _ = self.run_command(self.ms_node, cmd,
                                           default_asserts=True)

        process_owners = [process_owner.split()[1] for process_owner
                         in process_output if "init.d" not in process_owner and
                         "runuser" not in process_owner and "local" not in
                          process_owner]

        process_groups = [process_group.split()[2] for process_group
                          in process_output if "init.d" not in process_group
                          and "runuser" not in process_group and "local" not in
                          process_group]

        for owner, group in zip(process_owners, process_groups):

            self.assertEqual(expected_process_user, owner, "All processes are "
                             "not owned by user '{0}'".format(
                             expected_process_user))

            self.assertEqual(expected_process_user, group, "All processes do "
                             "not belong to group '{0}'".format(
                             expected_process_user))

    def check_services_status(self, services):
        """
        Description: Checks the status of the passed list of
                     service(s).
        Args:
            services (lst): list of service(s) to check
        """

        if isinstance(services, str):
            service_list = [services]
        else:
            service_list = services

        for service in service_list:
            self.get_service_status(self.ms_node, service)

    def start_puppet_run_and_wait_complete(self):
        """
        Description: Starts a Puppet run, waits for the Puppet to
                     transition on the MS to "applying a catalog"
                     and then waits for Puppet to become idle.
        """

        self.start_new_puppet_run(self.ms_node)

        status_cmd_str = ('{0} puppet status | {1} "^ *{2}: Currently '
                          'applying a catalog"').format(const.MCO_EXECUTABLE,
                                                        const.GREP_PATH,
                                                        self.ms_node)
        self.assertTrue(self.wait_for_cmd(self.ms_node, status_cmd_str, 0,
                                          timeout_mins=1,
                                          su_root=True,
                                          default_time=2))

        self.wait_for_puppet_idle(self.ms_node)

    def wait_for_service_up(self, service, check_phrase):
        """
        Description: Checking status of a service and grepping for
                     matching string in output, then assert
                     against a return code of 0 if status output is
                     matched within time limit.
        Args:
            service (str): the service queried for status
            check_phrase (str): status output to match
        """
        status_cmd_str = ('{0} status {1} |'
                          '{2} {3}').format(const.SYSTEMCTL_PATH, service,
                          const.GREP_PATH, check_phrase)

        self.assertTrue(self.wait_for_cmd(self.ms_node, status_cmd_str, 0,
                                          timeout_mins=5, su_root=True))

    def reboot_ms_and_assert_success(self):
        """
        Description: Reboots the MS and waits for the node to
                     come back up.
        """

        cmd = "(sleep 1; {0} -r now {1}) &".format(const.SHUTDOWN_PATH,
               self.ms_node)

        self.run_command(self.ms_node, cmd, su_root=True, default_asserts=True)

        self.assertTrue(self.wait_for_ping(self.ms_ip, False, retry_count=4),
                        "Node '{0} has not gone down".format(self.ms_node))

        self.assertTrue(self.wait_for_node_up(self.ms_node,
                        wait_for_litp=True), "'{0} did not come up in "
                        "expected timeframe".format(self.ms_node))

    @attr('all', 'revert', 'story289907', 'story289907_tc01')
    def test_01_p_verify_celery_processes_run_non_root(self):
        """
        @tms_id: torf_289907_tc01
        @tms_requirements_id: TORF-289907
        @tms_title: Verify Celery-related processes run as non root
                    user
        @tms_description: Verify that celery related proccesses are
                          not run as root
        @tms_test_steps:
            @step: Check permissions on celery processes
            @result: All celery processes are running as a 'celery' user
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """

        self.log("info", "1. Check permissions on celery processes")

        self.verify_process_ownership(self.celery_user)

    @attr('all', 'revert', 'story289907', 'story289907_tc02')
    def test_02_p_verify_rabbitmq_processes_run_non_root(self):
        """
        @tms_id: torf_289907_tc02
        @tms_requirements_id: TORF-289907
        @tms_title: Verify RabbitMQ processes run as non root
                    user
        @tms_description: Verify that RabbitMQ related proccesses are
                          not run as root
        @tms_test_steps:
            @step: Check permissions on RabbitMQ processes
            @result: RabbitMQ processes are running as a 'rabbitmq' user
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """

        self.log("info", "1. Check permissions on RabbitMQ processes")

        self.verify_process_ownership(self.rabbitmq_user)

    @attr('all', 'revert', 'story289907', 'story289907_tc03')
    def test_03_p_verify_puppet_restarts_celery_if_stopped(self):
        """
        @tms_id: torf_289907_tc03
        @tms_requirements_id: TORF-289907
        @tms_title: Verify Puppet restarts Celery processes if stopped
        @tms_description: Verify that puppet will restart Celery processes
                          if stopped
        @tms_test_steps:
            @step: Stop the 'celeryd' and 'celerybeat' processes
            @result: The 'celeryd' and 'celerybeat' processes are stopped
            @step: Start a puppet run and wait for it to complete
            @result: Puppet run completes successfully
            @step: Check the status of the 'celeryd' and 'celerybeat'
                   processes
            @result: The 'celeryd' and 'celerybeat' processes are running
            @step:  Verify Celery process permissions remain as user 'celery'
            @result: Celery process permissions persist
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        self.log("info", "1. Stop the '{0}' and '{1}' processes".format(
                    self.celery_processes[0], self.celery_processes[1]))

        for service in self.celery_processes:
            self.stop_service(self.ms_node, service)

        self.log("info", "2. Start a puppet run and wait for it to "
                 "complete")

        self.start_puppet_run_and_wait_complete()

        self.log("info", "3. Check the status of the '{0}' and '{1}'"
                 "processes".format(self.celery_processes[0],
                                    self.celery_processes[1]))

        self.check_services_status(self.celery_processes)

        self.log("info", "4. Verify Celery process permissions remain as "
                 "user '{0}'".format(self.celery_user))

        self.verify_process_ownership(self.celery_user)

    @attr('all', 'revert', 'story289907', 'story289907_tc04')
    def test_04_p_verify_puppet_restarts_rabbitmq_if_stopped(self):
        """
        @tms_id: torf_289907_tc04
        @tms_requirements_id: TORF-289907
        @tms_title: Verify Puppet restarts RabbitMQ process if stopped
        @tms_description: Verify that puppet will restart RabbitMQ process
                          if stopped
        @tms_test_steps:
            @step: Disable puppet on MS
            @result: Puppet disabled on MS
            @step: Enable puppet on MS
            @result: Puppet enabled on MS
            @step: Wait for Puppet to become idle on the MS
            @result: Puppet is idle on the MS
            @step: Stop the 'rabbitmq-server' process
            @result: The 'rabbitmq-server' is stopped
            @step: Run 'puppet agent -t' on MS
            @result: Puppet run on MS is executed
            @step: Wait for rabbitmq service to restart
            @result: Rabbitmq-server is restarted
            @step: Verify RabbitMQ process permissions remain as user
                  'rabbitmq'
            @result: RabbitMQ process permissions persist
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """

        run_puppet_agent = "{0} agent -t".format(const.PUPPET_PATH)

        self.log("info", "1. Disable puppet on MS")

        self.toggle_puppet(self.ms_node, enable=False)

        self.log("info", "2. Enable puppet on MS")

        self.toggle_puppet(self.ms_node, enable=True)

        self.log("info", "3. Wait for puppet idle before stopping rabbitmq")

        self.wait_for_puppet_idle(self.ms_node, node_hostname=self.ms_node)

        self.log("info", "4. Stop rabbitmq-server")

        self.stop_service(self.ms_node, self.rabbitmq_process)

        self.log("info", "5. Run 'puppet agent -t' on MS")

        self.run_command(self.ms_node, run_puppet_agent, su_root=True)

        self.log("info", "6. Wait for rabbitmq-server to restart")

        self.wait_for_service_up("rabbitmq-server", "running")

        time.sleep(5)

        self.log("info", "7. Verify RabbitMQ process permissions remain as "
                 "user '{0}'".format(self.rabbitmq_user))

        self.verify_process_ownership(self.rabbitmq_user)

    @attr('all', 'revert', 'story289907', 'story289907_tc05')
    def test_05_p_verify_celery_rabbitmq_process_permissions_reboot(self):
        """
        @tms_id: torf_289907_tc05
        @tms_requirements_id: TORF-289907
        @tms_title: Verify Celery and RabbitMQ process user permissions
                      persist after MS reboot
        @tms_description: Verify that after a reboot of the MS that celery
                            processes remain as user 'celery' and
                            RabbitMQ processes remain as user 'rabbitmq'
        @tms_test_steps:
            @step: Reboot the MS
            @result: The MS reboots successfully
            @step: Verify Celery process permissions remain as user
                   'celery' and RabbitMQ process permissions remain as
                    user 'rabbitmq'
            @result: Celery and RabbitMQ process permissions persist
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """

        self.log("info", "1. Reboot the MS")

        self.reboot_ms_and_assert_success()

        self.log("info", "2. Verify Celery process permissions remain as "
                 "user '{0}' and RabbitMQ process permissions remain "
                 "as '{1}'".format(self.celery_user, self.rabbitmq_user))

        for process in [self.celery_user, self.rabbitmq_user]:
            self.verify_process_ownership(process)
