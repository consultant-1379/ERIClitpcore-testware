'''
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     February 2016
@author:    David Hong-Minh, Maurizio Senno, Terry Farrell
@summary:   Integration tests for litpd service start when in different states
            Agile: Bug LITPCDS-13125 and LITPCDS-13052, EPIC LITPCDS-177
'''
from litp_generic_test import GenericTest, attr
from redhat_cmd_utils import RHCmdUtils
import test_constants as const
import time
from litp_cli_utils import CLIUtils

PRESENT = True
MISSING = False
RUNNING = True
NOT_RUNNING = False


class Bug13125(GenericTest):
    """
    Test litpd service start when the service is in different state/conditions:
    - litpd daemon running, not running
    - PID file present or not: "/var/run/litp_service.py.pid"
    - Startup lock file present or not: "/var/run/litp_startup_lock"
    Check litpd service can be restarted successfully in all cases
    """

    def setUp(self):
        """ Runs before every single test """
        super(Bug13125, self).setUp()
        self.ms1 = self.get_management_node_filenames()[0]
        self.rhc = RHCmdUtils()
        self.cli = CLIUtils()
        self.litp_service_file_path = \
                            '/opt/ericsson/nms/litp/lib/litp/core/service.py'
        self.litp_service_bin_file_path = \
                            '/opt/ericsson/nms/litp//bin/litp_service.py'

    def tearDown(self):
        """ Runs after every single test """
        litpd_status = self.get_service_status(self.ms1,
                                               'litpd',
                                               assert_running=False)
        if 'Active: active (running)' not in litpd_status:
            self.start_service(self.ms1, 'litpd')
        self.turn_on_litp_debug(self.ms1)
        super(Bug13125, self).tearDown()

    def _create_file(self, file_to_be_created):
        """
        Description:
            create file if file does not exist
        Args:
            file_to_be_created (str): path to file to be created
        """
        file_contents = []
        empty_file = True
        if file_to_be_created == const.LITP_PID_FILE:
            file_contents = ['999999']
            empty_file = False

        self.create_file_on_node(self.ms1,
                                 file_to_be_created,
                                 file_contents_ls=file_contents,
                                 su_root=True,
                                 empty_file=empty_file,
                                 add_to_cleanup=False,
                                 file_permissions='644')

    def _wait_for_service_killed(self, returncode):
        """ wait until litpd service returns expected return code"""
        cmd = self.rhc.get_service_running_cmd('litpd')
        self.wait_for_cmd(self.ms1, cmd, returncode)

        timeout = 10
        interval = 1
        for i in xrange(1, timeout):
            if not self._is_litpd_daemon_running():
                break
            else:
                time.sleep(interval)
                self.log('info',
                    'Waiting for "litpd" deamon to die. {0}s remaining'.
                    format(timeout - i))
        else:
            self.fail(
                'Timed out while waiting for "litpd" deamon to die')

    def _assert_preconditions_are_met(self,
                                      litpd_daemon_status,
                                      pid_file,
                                      startup_lock_file,
                                      litpd_service_status=None):
        """
        Description:
            Check that required precondition are met
        Args:
            litp_service_status (bool): litpd service status
            lipd_daemon_status (str)  : litp_service.py process status
            pid_file (bool)           : pid file (present or missing)
            startup_lock (bool)       : startup_lock_file (present or missing)
        """
        self.assertEqual(litpd_daemon_status,
                         self._is_litpd_daemon_running())

        valid_service_statuses = ['active',
                                  'inactive',
                                  'failed',
                                  'activating']

        if litpd_service_status is not None:
            self.assertTrue(litpd_service_status in valid_service_statuses,
                            'Invalid service status "{0}" was specified'.
                            format(litpd_service_status))

            if litpd_service_status == 'active':
                self.get_service_status(self.ms1, 'litpd', su_root=False)
            else:
                out, _, _ = self.get_service_status(self.ms1, 'litpd',
                                                    assert_running=False)
                self.assertTrue(self.is_text_in_list(
                    litpd_service_status,
                    out),
                    'litpd service found in "{0}" state. Expected "{1}"'.
                    format(out[0], litpd_service_status))

        self.assertTrue(pid_file in [MISSING, PRESENT])
        if pid_file == PRESENT:
            self.assertTrue(self.remote_path_exists(
                self.ms1, const.LITP_PID_FILE),
                'File "{0}" was NOT found'.format(
                    const.LITP_PID_FILE)
            )
        else:
            self.assertFalse(self.remote_path_exists(
                self.ms1, const.LITP_PID_FILE),
                'File "{0}" was found unexpectedly'.
                    format(const.LITP_PID_FILE))

        self.assertTrue(startup_lock_file in [MISSING, PRESENT])
        if startup_lock_file == PRESENT:
            self.assertTrue(self.remote_path_exists(
                self.ms1, const.STARTUP_LOCK_FILE),
                'File "{0}" was NOT found'.
                    format(const.STARTUP_LOCK_FILE))
        else:
            self.assertFalse(self.remote_path_exists(
                self.ms1, const.STARTUP_LOCK_FILE),
                'File "{0}" was found unexpectedly'.
                    format(const.STARTUP_LOCK_FILE))

    def _is_litpd_daemon_running(self):
        """
        Description
            Determine if "litp_service.py" process is running as daemon
        """
        cmd = '/usr/bin/pgrep -xf "python {0} --daemonize" -P 1'. \
              format(self.litp_service_bin_file_path)
        if len(self.run_command(self.ms1, cmd)[0]) == 1:
            return True
        return False

    def _start_patched_litpd(self):
        """
        Description:
            Start litpd service without waiting for any response or result
        """
        cmd = '/sbin/service litpd start &'
        self.run_command(self.ms1, cmd, su_root=True, default_asserts=True)

        cmd = '/usr/bin/pgrep -xf "python {0} --daemonize"'. \
              format(self.litp_service_bin_file_path)
        litpd_started = self.wait_for_cmd(self.ms1,
                                          cmd,
                                          expected_rc=0,
                                          default_time=1)
        self.assertTrue(litpd_started)

    def _apply_patch_to_litp_service(self, patch_file):
        """
        Description:
            Apply patch to litp service script so that the "litpd" process is
            daemonized after a given delay
        Args:
            patch_file (str): The file to be used to patch litp service
        """
        self.install_rpm_on_node(self.ms1, 'patch')

        self.backup_file(self.ms1, self.litp_service_file_path)

        self._create_diff_file_on_ms(patch_file)

        patch_cmd = 'patch -p0 {0} < {1}'. \
                    format(self.litp_service_file_path, patch_file)
        self.run_command(self.ms1, patch_cmd, su_root=True)

    def _remove_patch_to_litp_service(self, patch_file):
        """
        Description:
            Remove the patch that was applied to the litp service file
        Args:
            patch_file (str): The file to be used to unpatch litp service
        """
        patch_cmd = 'patch -p0 -R {0} < {1}'. \
                    format(self.litp_service_file_path, patch_file)
        self.run_command(self.ms1, patch_cmd, su_root=True)
        self.remove_item(self.ms1, patch_file, su_root=True)
        self.restart_litpd_service(self.ms1)

    def _create_diff_file_on_ms(self, patch_file, delay=20):
        """
        Description:
            Create diff to be used by utility "patch" to make changes to
            litp service file
        Args:
            patch_file (str): the patch file to create
        """
        file_contents = [
            'diff --git a/lib/litp/core/service.py b/lib/litp/core/service.py',
            'index f0c82f4..d02ed96 100755',
            '--- a/lib/litp/core/service.py',
            '+++ b/lib/litp/core/service.py',
            '@@ -260,6 +260,7 @@ def run_service():',
            '         data_manager.close()',
            '',
            '         server = CherrypyServer()',
            '+        time.sleep({0})'.format(delay),
            '         server.start(args.daemonize)',
            '',
            '     except '
            '(ModelItemContainerException, DataIntegrityException), e:',
        ]

        self.create_file_on_node(self.ms1,
                                 patch_file,
                                 file_contents,
                                 su_root=True)
        self.get_file_contents(self.ms1, patch_file, su_root=True)

    def _stop_litpd_service(self):
        """
        Description:
            Stops the litpd service on the MS and asserts that
            the status is stopped.
        """
        self.stop_service(self.ms1, 'litpd', assert_success=False,
                             execute_timeout=10)
        count = 0
        stopped = False
        while count < 9 and not stopped:
            stdout, _, _ = self.get_service_status(self.ms1, 'litpd',
                   assert_running=False)
            if "inactive" in stdout[0]:
                stopped = True
                break
            count += 1
            time.sleep(5)
        self.assertTrue(stopped, "litpd is not in a stopped state.")
        self.log("info", "Service 'litpd' stopped.")

    @attr('all', 'revert', 'bug13125', 'bug13125_tc01', 'bug13268')
    def test_01_p_litpd_starts_normally_when_service_stopped_root(self):
        """
        @tms_id: litpcds_13125_tc01
        @tms_requirements_id: LITPCDS-177
        @tms_title: Verify litpd service can be restarted
        @tms_description: Test that litpd service can be started normally
            when the service is in normal conditions
        @tms_test_steps:
        @step: Export the entire litp model to XML
        @result: Model exported successfully
        @step: Create a new litp item to make changes to the model
        @result: Item created successfully
        @step: Stop litp by entering the service litpd stop command
        @result: litp stops gracefully
        @step: Start litpd service,
        @result: litpd started successfully
        @step: Restore initial model by entering the "litp restore_model"
               command to verify that initial model data are still available
        @result: The model restored successfully
        @result: Initial model and current model are equal
        @step: Restart "litpd" service
        @result: "litpd" service restarted successfully
        @tms_test_precondition:
            - litpd service status   : inactive
            - litpd daemon status    : not running
            - PID file               : missing
            - startup lock file      : missing
        @tms_execution_type: Automated
        """
        self.log('info',
        '1. Export current model to XML file')
        initial_litp_model = '/tmp/initial_root.xml'
        self.execute_cli_export_cmd(self.ms1, '/', initial_litp_model)

        self.log('info',
        '2 Create a new litp item to make changes to the model')
        coll_fw_rules_url = self.find(self.ms1,
                                      '/ms',
                                      'collection-of-firewall-rule')[0]
        new_fw_rule_url = '{0}/fw_story13125'.format(coll_fw_rules_url)
        props = 'name="555 story 13125"'
        self.execute_cli_create_cmd(self.ms1,
                                    new_fw_rule_url,
                                    'firewall-rule',
                                    props=props)

        self.log('info',
        '3. Stop litpd service')
        if not self._is_litpd_daemon_running():
            self.start_service(self.ms1, 'litpd')
        self.stop_service(self.ms1, 'litpd', assert_success=False,
                             execute_timeout=10)

        self.log('info', '4. Check preconditions are met')
        self._assert_preconditions_are_met(
                                    litpd_service_status='inactive',
                                    litpd_daemon_status=NOT_RUNNING,
                                    pid_file=MISSING,
                                    startup_lock_file=MISSING)

        self.log('info',
        '3. Start "litpd" service')
        self.start_service(self.ms1, 'litpd')
        self.get_service_status(self.ms1, 'litpd')

        self.log('info',
        '4. Check that we can restore the initial model')
        self.execute_cli_restoremodel_cmd(self.ms1)

        current_litp_model = '/tmp/current_root.xml'
        self.execute_cli_export_cmd(self.ms1, '/', current_litp_model)

        cmd = '/usr/bin/diff {0} {1}'. \
              format(initial_litp_model, current_litp_model)
        diff = self.run_command(self.ms1, cmd, default_asserts=True)[0]
        self.assertEqual([], diff,
            'Failed to restore the model after starting "litpd" service')

        self.log('info',
        '5. Verify that "litpd" service can be restarted')
        self.restart_litpd_service(self.ms1)

    @attr('all', 'revert', 'bug13125', 'bug13125_tc02')
    def test_02_n_litpd_not_running_startup_lock_root(self):
        """
        @tms_id: litpcds_13125_tc02
        @tms_requirements_id: LITPCDS-177
        @tms_title: Verify litpd service starts normally if startup lock file
         present
        @tms_description: Test that litpd service can be started normally
            when the startup lock file is unexpectedly present
            (/var/run/litp_startup_lock)
        @tms_test_steps:
         @step: stop litp by issuing systemctl stop litpd.service,
         create a dummy startup lock file in /var/run/litp_startup_lock
         @result: litp stops gracefully
         @step: start litpd service
         @result: litpd starts normally
         @step: restart litpd service
         @result: can be restarted
        @tms_test_precondition:
        - litpd service status   : inactive
        - litpd daemon status    : not running
        - PID file               : missing
        - startup lock file      : present (unexpected)
        @tms_execution_type: Automated
        """
        self.log('info', '1. Stop litpd service')
        if not self._is_litpd_daemon_running():
            self.start_service(self.ms1, 'litpd')
        self._stop_litpd_service()

        self.log('info', '2. Create the startup_lock file')
        self._create_file(const.STARTUP_LOCK_FILE)

        self.log('info', '3. Check preconditions are met')
        self._assert_preconditions_are_met(
            litpd_service_status='inactive',
            litpd_daemon_status=NOT_RUNNING,
            pid_file=MISSING,
            startup_lock_file=PRESENT)

        self.log('info', '4. Start litpd service')
        self.start_service(self.ms1, 'litpd')

        self.log('info', '5. Check that litpd service starts successfully'
                         '(return code 0)')
        self.get_service_status(self.ms1, 'litpd')

        self.log('info', '6. Verify that litpd service can be restarted')
        self.restart_litpd_service(self.ms1)

    @attr('all', 'revert', 'bug13125', 'bug13125_tc03')
    def test_03_n_litpd_service_previously_killed_root(self):
        """
        @tms_id: litpcds_13125_tc03
        @tms_requirements_id: LITPCDS-177
        @tms_title: Verify litpd service starts when startup file
            is missing.
        @tms_description: Test that litpd service can be started normally
        @tms_test_steps:
         @step: SIGTERM litp by issuing a kill command, start litp
         @result: Check expected message and return code.
               litpd service starting, litpd starts
               eventually
         @step: restart litpd service
         @result: can be restarted
        @tms_test_precondition:
        - litpd service status   : active
        - litpd daemon status    : not running (killed)
        - PID file               : missing
        - startup lock file      : missing
        @tms_execution_type: Automated
        """
        self.log('info', '1. Kill (SIGTERM) litpd service')
        if not self._is_litpd_daemon_running():
            self.start_service(self.ms1, 'litpd')
        self.stop_service(self.ms1, 'litpd', kill_service=True)
        self._wait_for_service_killed(2)

        self.log('info', '2. Check preconditions are met')
        self._assert_preconditions_are_met(
            litpd_service_status='active',
            litpd_daemon_status=NOT_RUNNING,
            pid_file=MISSING,
            startup_lock_file=MISSING)

        self.log('info', '3. Start litpd service')
        stdout, _, rc = self.start_service(self.ms1, 'litpd')

        self.log('info', '4. Check expected message and return code')
        self.assertEqual([], stdout)
        self.assertEqual(0, rc)

        self.log('info', '5. Check that the litpd service is running')
        self.get_service_status(self.ms1, 'litpd')

        self.log('info', '6. Verify that litpd service can be restarted')
        self.restart_litpd_service(self.ms1)

    #attr('all', 'revert', 'bug13125', 'bug13125_tc04')
    def obsolete_04_n_litpd_not_running_subsys_startup_lock_root(self):
        """
        #tms_id: litpcds_13125_tc04
        #tms_requirements_id: LITPCDS-177
        #tms_title: Verify litpd service starts normally when unexpected
            startup lock file and subsystem lock files present
        #tms_description: Test that litpd service can be started normally
            when the startup lock file are unexpectedly present
            (/var/run/litp_startup_lock)
        #tms_test_steps:
         #step: issue service litpd stop
         #result: litp stops gracefully
         #step: create dummy files:
             /var/run/litp_startup_lock, start litp
         #result: Check expected message and return code
                   and litpd service starts successfully
         #step: restart litpd service
         #result: can be restarted
        #tms_test_precondition:
        - litpd service status   : inactive
        - litpd daemon status    : not running
        - PID file               : missing
        - subsystem lock file    : does not exist in RHEL7.7
        - startup lock file      : present (unexpected)
        #tms_execution_type: Automated
        """
        pass

    @attr('all', 'revert', 'bug13125', 'bug13125_tc05')
    def test_05_n_litpd_service_previously_sigkilled_root(self):
        """
        @tms_id: litpcds_13125_tc05
        @tms_requirements_id: LITPCDS-177
        @tms_title: Verify litpd service starts normally after SIGKILL
        @tms_description: Test that litpd service can be started normally
            after SIGKILL.
        @tms_test_steps:
         @step: kill -9 litpd service.
         @result: Check for expected message and return code
                  and litpd start eventually.
         @step: restart litpd service
         @result: can be restarted
        @tms_test_precondition:
        - litpd service status   : active
        - litpd daemon status    : not running (killed -9)
        - PID file               : missing
        - startup lock file      : missing
        @tms_execution_type: Automated
        """
        self.log('info', '1. Kill (SIGKILL) litpd service')
        if not self._is_litpd_daemon_running():
            self.start_service(self.ms1, 'litpd')
        self.stop_service(self.ms1, 'litpd', kill_service=True,
                          kill_args='-9')
        self._wait_for_service_killed(3)

        self.log('info', '2. Check preconditions are met')
        self._assert_preconditions_are_met(
            litpd_service_status='failed',
            litpd_daemon_status=NOT_RUNNING,
            pid_file=MISSING,
            startup_lock_file=MISSING)

        self.log('info', '3. Start litpd service')
        stdout, _, rc = self.start_service(self.ms1, 'litpd')

        self.log('info', '4. Check expected output and return code')
        self.assertEqual([], stdout)
        self.assertEqual(0, rc)

        self.log('info', '5. Check that the litpd service is running')
        self.get_service_status(self.ms1, 'litpd')

        self.log('info', '6. Verify that litpd service can be restarted')
        self.restart_litpd_service(self.ms1)

    @attr('all', 'revert', 'bug13125', 'bug13125_tc06')
    def test_06_n_litpd_not_running_pid_subsys_startup_lock_root(self):
        """
        @tms_id: litpcds_13125_tc06
        @tms_requirements_id: LITPCDS-177
        @tms_title: Verify litpd service can be started with unexpected
            files present
        @tms_description: Test that litpd service can be started normally
            when dummy files present:
            /var/run/litp_startup_lock,
            /var/run/litp_service.py.pid
        @tms_test_steps:
         @step: stop litp by systemctl stop litpd.service command
         @result: litp stops gracefully
         @step: create dummy files
            /var/run/litp_startup_lock, /var/run/litp_service.py.pid
            (dummy PID value, like 9999999, use an invalid value to make sure
            there's no actual process with same PID present),
            start litp
         @result: Check expected message and return code is returned
               and that litpd service starts successfully (return code 0)
        @step: restart litpd service
        @result: can be restarted
        @tms_test_precondition:
        - litpd service status   : inactive
        - litpd daemon status    : not running
        - PID file               : present (unexpected)
        - startup lock file      : present (unexpected)
        @tms_execution_type: Automated
        """

        self.log('info', '1. Stop litpd service')
        if not self._is_litpd_daemon_running():
            self.start_service(self.ms1, 'litpd')
        self._stop_litpd_service()

        self._create_file(const.LITP_PID_FILE)
        self._create_file(const.STARTUP_LOCK_FILE)

        self.log('info', '2. Check preconditions are met')
        self._assert_preconditions_are_met(
            litpd_service_status='inactive',
            litpd_daemon_status=NOT_RUNNING,
            pid_file=PRESENT,
            startup_lock_file=PRESENT)

        self.log('info', '3. Start litpd service')
        stdout, _, rc = self.start_service(self.ms1, 'litpd')

        self.log('info', '4. Check expected output and return code')
        self.assertEqual([], stdout)
        self.assertEqual(0, rc)

        self.log('info', '5. Check that the litpd service is running')
        self.get_service_status(self.ms1, 'litpd')

        self.log('info', '6. Verify that litpd service can be restarted')
        self.restart_litpd_service(self.ms1)

    @attr('all', 'revert', 'bug13125', 'bug13125_tc07')
    def test_07_n_litpd_not_running_pid_root(self):
        """
        @tms_id: litpcds_13125_tc07
        @tms_requirements_id: LITPCDS-177
        @tms_title: Verify litpd service starts normally when an unexpected
            pid file exists
        @tms_description: Test that litpd service can be started normally
            when shutdown was graceful but an unexpected dummy file
            /var/run/litp_service.py.pid exists
        @tms_test_steps:
         @step: issue service litpd stop command, create dummy file
            /var/run/litp_service.py.pid with contents
            (a dummy PID value, like 9999999, use an invalid value
            to make sure there's no actual process with same PID present)
         @result: litp stops gracefully
         @step: start litpd service
         @result: Check expected message and return code, starts eventually
         @step: restart litpd service
         @result: can be restarted
        @tms_test_precondition:
        - litpd service status   : inactive
        - litpd daemon status    : not running
        - PID file               : present (unexpected)
        - startup lock file      : missing
        @tms_execution_type: Automated
        """
        self.log('info', '1. Stop litpd service')
        if not self._is_litpd_daemon_running():
            self.start_service(self.ms1, 'litpd')
        self._stop_litpd_service()

        self._create_file(const.LITP_PID_FILE)

        self.log('info', '2. Check preconditions are met')
        self._assert_preconditions_are_met(
            litpd_service_status='inactive',
            litpd_daemon_status=NOT_RUNNING,
            pid_file=PRESENT,
            startup_lock_file=MISSING)

        self.log('info', '3. Start litpd service')
        stdout, _, rc = self.start_service(self.ms1, 'litpd')

        self.log('info', '4. Check expected output and return code')
        self.assertEqual([], stdout)
        self.assertEqual(0, rc)

        self.log('info', '5. Check that the litpd service is running')
        self.get_service_status(self.ms1, 'litpd')

        self.log('info', '6. Verify that litpd service can be restarted')
        self.restart_litpd_service(self.ms1)

    #attr('all', 'revert', 'bug13125', 'bug13125_tc08')
    def obsolete_08_n_litpd_not_running_pid_startup_lock_root(self):
        """
        #tms_id: litpcds_13125_tc08
        #tms_requirements_id: LITPCDS-177
        #tms_title: Verify litpd service starts normally when an unexpected
            pid file and startup lock file exists
        #tms_description: Test that litpd service can be started normally
            when shutdown was graceful but an unexpected dummy file
            /var/run/litp_service.py.pid exists and an unexpected
            /var/run/litp_startup_lock
        #tms_test_steps:
         #step: issue systemctl stop litpd.service command, create dummy file
            /var/run/litp_service.py.pid with contents
            (a dummy PID value, like 9999999, use an invalid value
            to make sure there's no actual process with same PID present)
            and a /var/run/litp_startup_lock file
         #result: litp stops gracefully
         #step: start litpd service
         #result: Check expected output and return code
               and that litpd service starts successfully (return code 0)
         #step: restart litpd service
         #result: can be restarted
        #tms_test_precondition:
        - litpd service status   : inactive
        - litpd daemon status    : not running
        - PID file               : present (unexpected)
        - subsystem lock file    : missing
        - startup lock file      : present (unexpected)
        #tms_execution_type: Automated
        """
        pass

    @attr('all', 'revert', 'bug13125', 'bug13125_tc09')
    def test_09_n_litpd_running_root(self):
        """
        @tms_id: litpcds_13125_tc09
        @tms_requirements_id: LITPCDS-177
        @tms_title:  Verify litpd service can be recovered if pid is missing.
        @tms_description: Test that if litpd service is running but mandatory
            file /var/run/litp_service.py.pid is missing and
            attempt to start doesn't cause unexpected behaviour
        @tms_test_steps:
         @step: while litp is running remove file /var/run/litp_service.py.pid
            start litpd service
         @result: Check expected message and return code
         @step: restart litpd service
         @result: can be restarted
        @tms_test_precondition:
        - litpd service status   : active
        - litpd daemon status    : running
        - PID file               : missing (unexpected)
        - startup lock file      : missing
        @tms_execution_type: Automated
        """
        self.log('info', '1. Check litpd service is running')
        if not self._is_litpd_daemon_running():
            self.start_service(self.ms1, 'litpd')

        self.remove_item(self.ms1, const.LITP_PID_FILE,
                         su_root=True)

        self.log('info', '2. Check preconditions are met')
        self._assert_preconditions_are_met(
            litpd_service_status='active',
            litpd_daemon_status=RUNNING,
            pid_file=MISSING,
            startup_lock_file=MISSING)

        self.log('info', '3. Start litpd service')
        stdout, _, rc = self.start_service(self.ms1, 'litpd')

        self.log('info', '4. Check expected output and return code')
        self.assertEqual([], stdout)
        self.assertEqual(0, rc)

        self.log('info', '5. Check that the litpd service is running')
        self.get_service_status(self.ms1, 'litpd')

        self.log('info', '6. Verify that litpd service can be restarted')
        self.restart_litpd_service(self.ms1)

    @attr('all', 'revert', 'bug13125', 'bug13125_tc10')
    def test_10_n_litpd_running_startup_lock_root(self):
        """
        @tms_id: litpcds_13125_tc10
        @tms_requirements_id: LITPCDS-177
        @tms_title: Verify litpd service can be recovered if pid is missing
            and unexpected startup lock file exists
        @tms_description: Test that if litpd service is running but mandatory
            file /var/run/litp_service.py.pid is missing and
            an unexpected /var/run/litp_startup_lock exists an
            attempt to start litp doesn't cause unexpected behaviour
        @tms_test_steps:
         @step: while litp is running remove files /var/run/litp_service.py.pid
            create /var/run/litp_startup_lock file
            and start litpd service
         @result: Check expected message and return code
         @step: restart litpd service
         @result: can be restarted
        @tms_test_precondition:
        - litpd service status   : active
        - litpd daemon status    : running
        - PID file               : missing (unexpected)
        - startup lock file      : present (unexpected)
        @tms_execution_type: Automated
        """
        self.log('info', '1. Check litpd service is running')
        if not self._is_litpd_daemon_running():
            self.start_service(self.ms1, 'litpd')

        self.remove_item(self.ms1, const.LITP_PID_FILE,
                         su_root=True)
        self._create_file(const.STARTUP_LOCK_FILE)

        self.log('info', '2. Check preconditions are met')
        self._assert_preconditions_are_met(
            litpd_service_status='active',
            litpd_daemon_status=RUNNING,
            pid_file=MISSING,
            startup_lock_file=PRESENT)

        self.log('info', '3. Start litpd service')
        stdout, _, rc = self.start_service(self.ms1, 'litpd')

        self.log('info', '4. Check expected output and return code')
        self.assertEqual([], stdout)
        self.assertEqual(0, rc)

        self.log('info', '5. Check that the litpd service is running')
        self.get_service_status(self.ms1, 'litpd')

        self.log('info', '6. Verify that litpd service can be restarted')
        self.restart_litpd_service(self.ms1)

    #attr('all', 'revert', 'bug13125', 'bug13125_tc11')
    def obsolete_11_n_litpd_running_subsys_root(self):
        """
        #tms_id: litpcds_13125_tc11
        #tms_requirements_id: LITPCDS-177
        #tms_title: Verify litpd service can be recovered if pid file missing
        #tms_description: Test that if litpd service is running but mandatory
            file /var/run/litp_service.py.pid is missing
            attempt to start litp doesn't cause unexpected behaviour
        #tms_test_steps:
         #step: whle litp is running remove file /var/run/litp_service.py.pid
            and start litpd service
         #result: Check expected output and return code.
         #step: restart litpd service
         #result: can be restarted
        #tms_test_precondition:
        - litpd service status   : active
        - litpd daemon status    : running
        - PID file               : missing (unexpected)
        - subsystem lock file    : missing
        - startup lock file      : missing
        #tms_execution_type: Automated
        """
        pass

    @attr('all', 'revert', 'bug13125', 'bug13125_tc12')
    def test_12_n_litpd_running_subsys_startup_root(self):
        """
        @tms_id: litpcds_13125_tc12
        @tms_requirements_id: LITPCDS-177
        @tms_title: Verify litpd service can be recovered if pid file missing
            and an unexpected startup lock file exists
        @tms_description: Test that if litpd service is running but mandatory
            file /var/run/litp_service.py.pid is missing and an unexpected
            /var/run/litp_startup_lock exists attempt to start litp
            doesn't cause unexpected behaviour
        @tms_test_steps:
         @step: whle litp is running remove file /var/run/litp_service.py.pid,
            create a dummy /var/run/litp_startup_lock and start litpd service
         @result: Check expected message and return code
         @step: restart litpd service
         @result: can be restarted
        @tms_test_precondition:
        - litpd service status   : active
        - litpd daemon status    : running
        - PID file               : missing (unexpected)
        - startup lock file      : present (unexpected)
        @tms_execution_type: Automated
        """
        self.log('info', '1. Check litpd service is running')
        if not self._is_litpd_daemon_running():
            self.start_service(self.ms1, 'litpd')

        self.remove_item(self.ms1, const.LITP_PID_FILE,
                         su_root=True)
        self._create_file(const.STARTUP_LOCK_FILE)

        self.log('info', '2. Check preconditions are met')
        self._assert_preconditions_are_met(
            litpd_service_status='active',
            litpd_daemon_status=RUNNING,
            pid_file=MISSING,
            startup_lock_file=PRESENT)

        self.log('info', '3. Start litpd service')
        stdout, _, rc = self.start_service(self.ms1, 'litpd')

        self.log('info', '4. Check expected output and return code')
        self.assertEqual([], stdout)
        self.assertEqual(0, rc)

        self.log('info', '5. Check that the litpd service is running')
        self.get_service_status(self.ms1, 'litpd')

        self.log('info', '6. Verify that litpd service can be restarted')
        self.restart_litpd_service(self.ms1)

    @attr('all', 'revert', 'bug13125', 'bug13125_tc13')
    def test_13_n_another_instance_litpd_running_root(self):
        """
        @tms_id: litpcds_13125_tc13
        @tms_requirements_id: LITPCDS-177
        @tms_title: Verify behaviour on starting litp if it's already running
        @tms_description: Test that 'systemctl start litpd.service' command
        can be issued when another instance of LITP is fully up and running
        and no unexpected behaviour occurs
        @tms_test_steps:
         @step: while litp is running start litpd service by issuing
            systemctl start litpd.service command
         @result: Check for expected message and return code
        @tms_test_precondition:
        - litpd service status   : active
        - litpd daemon status    : running
        - PID file               : present
        - startup lock file      : missing
        @tms_execution_type: Automated
        """
        self.log('info', '1. Check litpd service is running')
        if not self._is_litpd_daemon_running():
            self.start_service(self.ms1, 'litpd')
        stdout, _, _ = self.get_service_status(self.ms1, 'litpd')
        current_pid_num = self.get_service_pid(self.ms1, 'litpd')

        self.log('info', '2. Check preconditions are met')
        self._assert_preconditions_are_met(
            litpd_service_status='active',
            litpd_daemon_status=RUNNING,
            pid_file=PRESENT,
            startup_lock_file=MISSING)

        self.log('info', '3. Start litpd service')
        stdout, _, rc = self.start_service(self.ms1, 'litpd')

        self.log('info', '4. Check return code')
        pid_num = self.get_service_pid(self.ms1, 'litpd')
        #In systemctl start command the output is silent
        self.assertEqual(0, rc)
        self.assertEqual([], stdout)

        self.log('info', '5. Check litpd service is running and '
                         'was not restarted')
        self.get_service_status(self.ms1, 'litpd')
        self.assertEqual(current_pid_num, pid_num,
                         'litpd service was restarted unexpectedly')

        self.log('info', '6. Verify that litpd service can be restarted')
        self.restart_litpd_service(self.ms1)

    @attr('all', 'revert', 'bug13125', 'bug13125_tc14')
    def test_14_n_litpd_running_pid_subsys_startup_lock_root(self):
        """
        @tms_id: litpcds_13125_tc14
        @tms_requirements_id: LITPCDS-177
        @tms_title: Verify behaviour on starting litp if it's already running
            and unexpected startup lock file is present
        @tms_description: Test that issuing 'service litpd start' command
            causes no unexpected behaviour when another instance of LITP
            is running and an unexpected startup lock file exists
        @tms_test_steps:
         @step: while litp is running create a dummy /var/run/litp_startup_lock
            file and start litpd service by issuing
            systemctl start litpd.service command
         @result: Check for expected message and output and
                  litpd not restarted
        @tms_test_precondition:
        - litpd service status   : active
        - litpd daemon status    : running
        - PID file               : present
        - startup lock file      : present (unexpected)
        @tms_execution_type: Automated
        """

        self.log('info', '1. Check litpd service is running')
        if not self._is_litpd_daemon_running():
            self.start_service(self.ms1, 'litpd')
        stdout, _, _ = self.get_service_status(self.ms1, 'litpd')
        current_pid_num = self.get_service_pid(self.ms1, 'litpd')

        self._create_file(const.STARTUP_LOCK_FILE)

        self.log('info', '2. Check preconditions are met')
        self._assert_preconditions_are_met(
            litpd_service_status='active',
            litpd_daemon_status=RUNNING,
            pid_file=PRESENT,
            startup_lock_file=PRESENT)

        self.log('info', '3. Start litpd service')
        stdout, _, rc = self.start_service(self.ms1, 'litpd')

        self.log('info', '4. Check expected return code')
        #In systemctl start command output is empty
        pid_num = self.get_service_pid(self.ms1, 'litpd')
        self.assertEqual(0, rc)
        self.assertEqual([], stdout)

        self.log('info', '5. Check liptd service is running and '
                         'was not restarted')
        self.get_service_status(self.ms1, 'litpd')
        self.assertEqual(current_pid_num, pid_num,
                         'litpd service was restarted unexpectedly')

        self.log('info', '6. Verify that litpd service can be restarted')
        self.restart_litpd_service(self.ms1)

    #attr('all', 'revert', 'bug13125', 'bug13125_tc15')
    def obsolete_15_n_litpd_running_pid_root(self):
        """
        #tms_id: litpcds_13125_tc15
        #tms_requirements_id: LITPCDS-177
        #tms_title: Verify behaviour on starting litp if it's already running
            and mandatory subsys lock file is missing
        #tms_description: Test that issuing 'service litpd start' command
            causes no unexpected behaviour when another instance of LITP
            is running and a mandatory subsys lock file is missing
        #tms_test_steps:
         #step: whle litp is running, start litpd service by issuing
            service litpd start command
         #result: returned (return code 0)
        #tms_test_precondition:
        - litpd service status   : active
        - litpd daemon status    : running
        - PID file               : present
        - subsystem lock file    : missing
        - startup lock file      : missing
        #tms_execution_type: Automated
        """
        pass

    @attr('all', 'revert', 'bug13125', 'bug13125_tc16')
    def test_16_n_litpd_running_pid_startup_lock_root(self):
        """
        @tms_id: litpcds_13125_tc16
        @tms_requirements_id: LITPCDS-177
        @tms_title: Verify behaviour on starting litp if it's already
             running and an unexpected startup lock file is
             present.
        @tms_description: Test that issuing 'systemctl start litpd.service'
            command causes no unexpected behaviour when another
            instance of LITP is running and an unexpected /var/run/
            litp_startup_lock file is present.
        @tms_test_steps:
         @step: while litp is running create /var/run/litp_startup_lock start
            litpd service by issuing service litpd start command
         @result: Check expected message and return code, litp not restarted
        @tms_test_precondition:
        - litpd service status   : active
        - litpd daemon status    : running
        - PID file               : present
        - startup lock file      : present (unexpected)
        @tms_execution_type: Automated
        """

        self.log('info', '1. Check litpd service is running')
        if not self._is_litpd_daemon_running():
            self.start_service(self.ms1, 'litpd')
        stdout, _, _ = self.get_service_status(self.ms1, 'litpd')
        current_pid_num = self.get_service_pid(self.ms1, 'litpd')
        self._create_file(const.STARTUP_LOCK_FILE)

        self.log('info', '2. Check preconditions are met')
        self._assert_preconditions_are_met(
            litpd_service_status='active',
            litpd_daemon_status=RUNNING,
            pid_file=PRESENT,
            startup_lock_file=PRESENT)

        self.log('info', '3. Start litpd service')
        stdout, _, rc = self.start_service(self.ms1, 'litpd')

        self.log('info', '4. Check expected message and return code')
        pid_num = self.get_service_pid(self.ms1, 'litpd')
        self.assertEqual([], stdout)
        self.assertEqual(0, rc)

        self.log('info', '5. Check liptd service is running and '
                         'was not restarted')
        self.get_service_status(self.ms1, 'litpd')
        self.assertEqual(current_pid_num, pid_num,
                         'litpd service was restarted unexpectedly')

        self.log('info', '6. Verify that litpd service can be restarted')
        self.restart_litpd_service(self.ms1)

    @attr('all', 'revert', 'bug13125', 'bug13125_tc17')
    def test_17_n_cannot_start_litpd_service_non_root(self):
        """
        @tms_id: litpcds_13125_tc17
        @tms_requirements_id: LITPCDS-177
        @tms_title: Verify non root user cannot start litpd service
        @tms_description: Test that issuing 'systemctl start litpd.service'
            command by a non root user while litp is not running doesn't
            start litp.
        @tms_test_steps:
         @step: stop litpd service by systemctl stop litpd.service
         @result: litp stops gracefully
         @step: issue systemctl start litpd.service command as non root user
         @result: Check expected output and return code, litp not started
        @tms_test_precondition:
        - litpd service status   : inactive
        - litpd daemon status    : not running
        - PID file               : missing
        - startup lock file      : missing
        @tms_execution_type: Automated
        """
        self.get_service_status(self.ms1, 'litpd')
        self.log('info', '1. Stop litpd service as root')
        self._stop_litpd_service()
        self.remove_item(self.ms1, const.STARTUP_LOCK_FILE,
                         su_root=True)

        self.log('info', '2. Check preconditions are met')
        self._assert_preconditions_are_met(
            litpd_service_status='inactive',
            litpd_daemon_status=NOT_RUNNING,
            pid_file=MISSING,
            startup_lock_file=MISSING)

        self.log('info', '3. Start litpd service as non root')
        stdout, _, rc = self.start_service(self.ms1, 'litpd',
                                           assert_success=False,
                                           su_root=False)

        self.log('info', '4. Check expected output and return code')
        self.assertEqual([], stdout)
        self.assertEqual(1, rc)

        self.log('info', '5. Check litpd service has stopped')
        stdout, _, rc = self.get_service_status(self.ms1, 'litpd',
                             assert_running=False, su_root=False)
        self.assertTrue(self.is_text_in_list('inactive', stdout))
        self.assertEqual(3, rc)

        self.log('info', '6. Verify that litpd service can be restarted')
        self.restart_litpd_service(self.ms1)

    @attr('all', 'revert', 'bug13125', 'bug13125_tc18')
    def test_18_n_litpd_not_running_startup_lock_non_root(self):
        """
        @tms_id: litpcds_13125_tc18
        @tms_requirements_id: LITPCDS-177
        @tms_title: Verify non root user cannot start litpd service
            if there's an unexpected startup lock file present
        @tms_description: Test that issuing 'systemctl start litpd.service'
            command by a non root user while litp is running and
            an unexpected  /var/run/litp_startup_lock file doesn't
            start litp.
        @tms_test_steps:
         @step: stop litpd service by systemctl stop litpd.service
         @result: litp stops gracefully
         @step: create a dummy /var/run/litp_startup_lock file and issue
            systemctl start litpd.service command as non root user
         @result: Check expected message and return code, litp not start
         @step: service litpd restart as root
         @result: litp started
        @tms_test_precondition:
        - litpd service status   : inactive
        - litpd daemon status    : not running
        - PID file               : missing
        - startup lock file      : present (unexpected)
        @tms_execution_type: Automated
        """
        self.get_service_status(self.ms1, 'litpd')
        self.log('info', '1. Stop litpd service as root')
        self._stop_litpd_service()

        self._create_file(const.STARTUP_LOCK_FILE)

        self.log('info', '2. Check preconditions are met ')
        self._assert_preconditions_are_met(
            litpd_service_status='inactive',
            litpd_daemon_status=NOT_RUNNING,
            pid_file=MISSING,
            startup_lock_file=PRESENT)

        self.log('info', '3. Start litpd service as non root')
        stdout, _, rc = self.start_service(self.ms1, 'litpd',
                                           assert_success=False,
                                           su_root=False)

        self.log('info', '4. Check expected output and return code')
        self.assertEqual(1, rc)
        self.assertEqual([], stdout)

        self.log('info', '5. Check litpd service has stopped')
        stdout, _, rc = self.get_service_status(self.ms1, 'litpd',
                             assert_running=False, su_root=False)
        self.assertTrue(self.is_text_in_list('inactive', stdout))
        self.assertEqual(3, rc)

        self.log('info', '6. Verify that litpd service can be restarted')
        self.restart_litpd_service(self.ms1)

    @attr('all', 'revert', 'bug13125', 'bug13125_tc19')
    def test_19_n_litpd_service_previously_killed_non_root(self):
        """
        @tms_id: litpcds_13125_tc19
        @tms_requirements_id: LITPCDS-177
        @tms_title: Verify non root user cannot start litpd service
            if it was SIGKILL'd
        @tms_description: Test that issuing 'systemctl start litpd.service'
            commannd by a non root user doesn't start litp instantaneously
            but it starts after few secs. after it was stopped by a kill -9
            command.
        @tms_test_steps:
         @step: stop litpd service by kill -9 and try to start as non root
            by issuing systemctl start litpd.service.
         @result: Check expected message and return code, litp does not start
            instantaneously but it starts after few secs.
         @step: restart litpd as root by systemctl restart litpd.service
         @result: litp started
        @tms_test_precondition:
        - litpd service status   : active
        - litpd daemon status    : not running
        - PID file               : missing
        - startup lock file      : missing
        @tms_execution_type: Automated
        """

        self.get_service_status(self.ms1, 'litpd')
        self.log('info', '1. Stop litpd service as root')
        self.stop_service(self.ms1, 'litpd', kill_service=True)
        self._wait_for_service_killed(2)

        self.log('info', '2. Check preconditions are met ')
        self._assert_preconditions_are_met(
            litpd_service_status='active',
            litpd_daemon_status=NOT_RUNNING,
            pid_file=MISSING,
            startup_lock_file=MISSING)

        self.log('info', '3. Start litpd service as non root')
        stdout, _, rc = self.start_service(self.ms1, 'litpd',
                                           assert_success=False,
                                           su_root=False)

        self.log('info', '4. Check expected output and return code')
        self.assertEqual(1, rc)
        self.assertEqual([], stdout)

        self.log('info', '5. Check lipd service has started')
        stdout, _, rc = self.get_service_status(self.ms1, 'litpd',
                             assert_running=False, su_root=False)
        self.assertTrue(self.is_text_in_list('active', stdout))
        self.assertEqual(0, rc)

        self.log('info', '6. Verify that litpd service can be restarted')
        self.restart_litpd_service(self.ms1)

    #attr('all', 'revert', 'bug13125', 'bug13125_tc20')
    def obsolete_20_n_litpd_not_running_subsys_startup_lock_non_root(self):
        """
        #tms_id: litpcds_13125_tc20
        #tms_requirements_id: LITPCDS-177
        #tms_title: Verify non root user cannot start litpd service
            when an unexpected subsystem and startup lock files are present
        #tms_description: Test that issuing 'service litpd start' command
            by a non root user doesn't start litp while it's stopped and
            unexpected files /var/run/litp_startup_lock is present
        #tms_test_steps:
         #step: stop litpd service as root, create dummy files
            /var/run/litp_startup_lock
            try start as non root by issuing service litpd start
         #result: Check expected message and return code, litp does not start
         #step: restart litpd as root by service litpd restart
         #result: litp started
        #tms_test_precondition:
        - litpd service status   : inactive
        - litpd daemon status    : not running
        - PID file               : missing
        - subsystem lock file    : missing
        - startup lock file      : present (unexpected)
        #tms_execution_type: Automated
        """
        pass

    @attr('all', 'revert', 'bug13125', 'bug13125_tc21')
    def test_21_n_litpd_service_previously_sigkilled_non_root(self):
        """
        @tms_id: litpcds_13125_tc21
        @tms_requirements_id: LITPCDS-177
        @tms_title: Verify non root user cannot start litpd service
            when SIGKILL'd
        @tms_description: Test that issuing 'systemctl start litpd.service'
            command by a non root user doesn't start litp  instantaneously
            while its's stopped by kill -9
        @tms_test_steps:
         @step: kill -9 litpd service, create dummy files
            /var/run/litp_service.py.pid (dummy invalid value like 9999999)
            try start as non root by issuing
            systemctl start litpd service
         @result: Check expected output and return code, litp does not start
         @step: restart litpd as root by systemctl restart litpd.service
         @result: litp started
        @tms_test_precondition:
        - litpd service status   : active
        - litpd daemon status    : not running (killed -9)
        - PID file               : missing
        - startup lock file      : missing
        @tms_execution_type: Automated
        """
        self.get_service_status(self.ms1, 'litpd')
        self.log('info', 'Stop litpd service as root')
        self.stop_service(self.ms1, 'litpd', kill_service=True,
                          kill_args='-9')
        self._wait_for_service_killed(3)

        self.log('info', '2. Check preconditions are met ')
        self._assert_preconditions_are_met(
            litpd_service_status='failed',
            litpd_daemon_status=NOT_RUNNING,
            pid_file=MISSING,
            startup_lock_file=MISSING)

        self.log('info', '3. Start litpd service as non root')
        stdout, _, rc = self.start_service(self.ms1, 'litpd',
                                           assert_success=False,
                                           su_root=False)

        self.log('info', '4. Check expected output and return code')
        self.assertEqual([], stdout)
        self.assertEqual(1, rc)

        self.log('info', '5. Check litpd service has not started')
        stdout, _, rc = self.get_service_status(self.ms1, 'litpd',
                             assert_running=False, su_root=False)
        self.assertNotEqual(0, rc)

        self.log('info', '6. Verify that litpd service can be restarted')
        self.restart_litpd_service(self.ms1)

    @attr('all', 'revert', 'bug13125', 'bug13125_tc22')
    def test_22_n_litpd_not_running_pid_subsys_startup_lock_non_root(self):
        """
        @tms_id: litpcds_13125_tc22
        @tms_requirements_id: LITPCDS-177
        @tms_title: Verify non root user cannot start litpd service
            instantaneously when stopped and unexpected pid, startup lock
            files are present but it starts after few secs.
        @tms_description: Test that issuing 'systemctl start litpd.service'
            command by a non root user doesn't start litp while it's stopped by
            root instantaneously and unexpected files /var/run/litp_service.py
            .pid /var/run/litp_startup_lock is present but it starts after few
            secs.
        @tms_test_steps:
         @step: stop service as root, create dummy files
            /var/run/litp_startup_lock, /var/run/litp_service.py.pid
            (dummy invalid value like 9999999),
            try start as non root by issuing systemctl start litpd.service
         @result: Check expected message and return code, litp does not start
            instantaneously but it starts after few secs.
         @step: restart litpd as root by systemctl restart litpd.service
         @result: litp started
        @tms_test_precondition:
        - litpd service status   : inactive
        - litpd daemon status    : not running
        - PID file               : present (unexpected)
        - startup lock file      : present (unexpected)
        @tms_execution_type: Automated
        """

        self.get_service_status(self.ms1, 'litpd')
        self.log('info', '1. Stop litpd service as root')
        self._stop_litpd_service()

        self._create_file(const.LITP_PID_FILE)
        self._create_file(const.STARTUP_LOCK_FILE)

        self.log('info', '2. Check preconditions are met ')
        self._assert_preconditions_are_met(
            litpd_service_status='inactive',
            litpd_daemon_status=NOT_RUNNING,
            pid_file=PRESENT,
            startup_lock_file=PRESENT)

        self.log('info', '3. Start litpd service as non root')
        stdout, _, rc = self.start_service(self.ms1, 'litpd',
                                           assert_success=False,
                                           su_root=False)

        self.log('info', '4. Check expected output and return code')
        self.assertEqual([], stdout)
        self.assertEqual(1, rc)

        self.log('info', '5. Check lipd service has stopped for an instance')
        _, _, rc = self.get_service_status(self.ms1, 'litpd',
                             assert_running=False, su_root=False)
        self.assertEqual(3, rc)

        self.log('info', '6. Verify that litpd service can be restarted')
        self.restart_litpd_service(self.ms1)

    @attr('all', 'revert', 'bug13125', 'bug13125_tc23')
    def test_23_n_litpd_not_running_pid_non_root(self):
        """
        @tms_id: litpcds_13125_tc23
        @tms_requirements_id: LITPCDS-177
        @tms_title: Verify non root user cannot start litpd service
            instantaneously when stopped and unexpected pid file present
            but it starts afer few secs.
        @tms_description: Test that issuing 'systemctl start litpd.service'
            command by a non root user doesn't start litp instantaneoulsy
            but it starts after few secs.
            by root and unexpected file /var/run/litp_service.py.pid present
        @tms_test_steps:
         @step: stop service as root, create dummy file
            /var/run/litp_service.py.pid (dummy invalid value like 9999999)
            try start as non root by issuing systemctl start litpd.service
         @result: Check expected message and return code, litp does not start
            instantaneously but it starts after few secs.
         @step: restart litpd as root by systemctl restart litpd.service
         @result: litp started
        @tms_test_precondition:
        - litpd service status   : inactive
        - litpd daemon status    : not running
        - PID file               : present (unexpected)
        - startup lock file      : missing
        @tms_execution_type: Automated
        """

        self.get_service_status(self.ms1, 'litpd')
        self.log('info', '1. Stop litpd service as root')
        self._stop_litpd_service()

        self._create_file(const.LITP_PID_FILE)

        self.log('info', '2. Check preconditions are met ')
        self._assert_preconditions_are_met(
            litpd_service_status='inactive',
            litpd_daemon_status=NOT_RUNNING,
            pid_file=PRESENT,
            startup_lock_file=MISSING)

        self.log('info', '3. Start litpd service as non root')
        stdout, _, rc = self.start_service(self.ms1, 'litpd',
                                           assert_success=False,
                                           su_root=False)

        self.log('info', '4. Check expected output and return code')
        self.assertEqual([], stdout)
        self.assertEqual(1, rc)

        self.log('info', '5. Check litpd service has started')
        stdout, _, rc = self.get_service_status(self.ms1, 'litpd',
                             assert_running=False, su_root=False)
        self.assertEqual(3, rc)

        self.log('info', '6. Verify that litpd service can be restarted')
        self.restart_litpd_service(self.ms1)

    #attr('all', 'revert', 'bug13125', 'bug13125_tc24')
    def obsolete_24_n_litpd_not_running_pid_startup_lock_non_root(self):
        """
        #tms_id: litpcds_13125_tc24
        #tms_requirements_id: LITPCDS-177
        #tms_title: Verify non root user cannot start litpd service
            when stopped and unexpected pid file and startup lock file present
        #tms_description: Test that issuing 'systemctl start litpd.service'
            command  by a non root user doesn't start litp while it's stopped
            by root and unexpected files /var/run/litp_startup_lock,
            /var/run/litp_service.py.pid present
        #tms_test_steps:
         #step: stop service as root, create dummy file
            /var/run/litp_service.py.pid (dummy invalid value like 9999999)
            and /var/run/litp_startup_lock file, try to start litp as non root
            by issuing systemctl start litpd.service command
         #result: Check expected message and return code, litp does not start
         #step: restart litpd as root by systemctl restart litpd.service
         #result: litp started
        #tms_test_precondition:
        - litpd service status   : inactive
        - litpd daemon status    : not running
        - PID file               : present (unexpected)
        - subsystem lock file    : does not exist in RHEL7.7
        - startup lock file      : present (unexpected)
        #tms_execution_type: Automated
        """
        pass

    @attr('all', 'revert', 'bug13125', 'bug13125_tc25')
    def test_25_n_litpd_running_non_root(self):
        """
        @tms_id: litpcds_13125_tc25
        @tms_requirements_id: LITPCDS-177
        @tms_title: Verify non root user cannot start litpd service
            instantaneously when it's running but pid file is missing
        @tms_description: Test that issuing 'systemctl start litpd.service'
            command by a non root user doesn't start litp instantaneously
            while its daemon running, but it starts after few secs and
            expected files /var/run/litp_service.py.pid missing
        @tms_test_steps:
         @step: remove file
            /var/run/litp_service.py.pid try start as non root
            by issuing 'systemctl start litpd.service'command
         @result: Check expected message and return code, litp does not start
         instantaneously but it starts after few secs.
         @step: restart litpd as root by systemctl restart litpd.service.
         @result: litp restarted
        @tms_test_precondition:
        - litpd service status   : active
        - litpd daemon status    : running
        - PID file               : missing (unexpected)
        - startup lock file      : missing
        @tms_execution_type: Automated
        """
        self.log('info', '1. Start litpd service')
        if not self._is_litpd_daemon_running():
            self.start_service(self.ms1, 'litpd')

        self.log('info', '2. Remove pid file')
        self.remove_item(self.ms1, const.LITP_PID_FILE,
                         su_root=True)

        self.log('info', '3. Check that preconditions are met')
        self._assert_preconditions_are_met(
            litpd_service_status='active',
            litpd_daemon_status=RUNNING,
            pid_file=MISSING,
            startup_lock_file=MISSING)

        self.log('info', '4. Start litpd service as non root')
        stdout, _, rc = self.start_service(self.ms1, 'litpd',
                                    assert_success=False, su_root=False)

        self.log('info', '5. Check expected output and return code')
        self.assertEqual(1, rc)
        self.assertEqual([], stdout)

        self.log('info', '6. Check that litpd service has started')
        stdout, _, rc = self.get_service_status(self.ms1, 'litpd',
                         assert_running=False, su_root=False)
        self.assertTrue(self.is_text_in_list('active', stdout))
        self.assertEqual(0, rc)

        self.log('info', '7. Verify that litpd service can be restarted')
        self.restart_litpd_service(self.ms1)

    @attr('all', 'revert', 'bug13125', 'bug13125_tc26')
    def test_26_n_litpd_running_startup_lock_non_root(self):
        """
        @tms_id: litpcds_13125_tc26
        @tms_requirements_id: LITPCDS-177
        @tms_title: Verify non root user can start litpd service when
            it's stopped, daemon running pid file and unexpected startup
            lock file is present
        @tms_description: Test that issuing 'systemctl start litpd.service'
            command by a non root user doesn't start litp for instantaneously
            but it starts after few seconds while its' daemon running and
            /var/run/litp_service.py.pid
            is missing and an unexpected /var/run/litp_startup_lock file
            is present
        @tms_test_steps:
         @step: while litp is running remove file
            /var/run/litp_service.py.pid
            create a dummy /var/run/litp_startup_lock file
            try start as non root by issuing systemctl start litpd.service
            command
         @result: Check expected message and return code, litp does not start
            instantaneously but it starts after few seconds.
         @step: restart litpd as root by systemctl restart litpd.service
         @result: litp restarted
        @tms_test_precondition:
        - litpd service status   : active
        - litpd daemon status    : running
        - PID file               : missing (unexpected)
        - startup lock file      : present (unexpected)
        @tms_execution_type: Automated
        """
        self.log('info', '1. Start litpd service')
        if not self._is_litpd_daemon_running():
            self.start_service(self.ms1, 'litpd')

        self.log('info', '2. Remove the pid file as root user')
        self.remove_item(self.ms1, const.LITP_PID_FILE,
                         su_root=True)

        self.log('info', '3. Create the startup lock file')
        self._create_file(const.STARTUP_LOCK_FILE)

        self.log('info', '4. Check that preconditions are met')
        self._assert_preconditions_are_met(
            litpd_service_status='active',
            litpd_daemon_status=RUNNING,
            pid_file=MISSING,
            startup_lock_file=PRESENT)

        self.log('info', '5. Start litpd service as non root')
        stdout, _, rc = self.start_service(self.ms1, 'litpd',
                                    assert_success=False, su_root=False)

        self.log('info', '6. Check expected output and return code')
        #In RHEL7.7 when using systemctl to start litpd
        # it fails to start for an instant therefore rc=1
        #but after few secs
        #service starts instantaneusly
        self.assertEqual([], stdout)
        self.assertEqual(1, rc)

        self.log('info', '7. Check that litpd service has started')
        stdout, _, rc = self.get_service_status(self.ms1, 'litpd',
                         assert_running=False, su_root=False)
        self.assertTrue(self.is_text_in_list('active',
                                             stdout))
        self.assertEqual(0, rc)

        self.log('info', '8. Verify that litpd service can be restarted')
        self.restart_litpd_service(self.ms1)

    @attr('all', 'revert', 'bug13125', 'bug13125_tc27')
    def test_27_n_litpd_running_subsystem_non_root(self):
        """
        @tms_id: litpcds_13125_tc27
        @tms_requirements_id: LITPCDS-177
        @tms_title: Verify non root user cannot start litpd service
            instantaneously but it starts the service after few seconds
            with daemon running and pid file missing.
        @tms_description: Test that issuing 'systemctl start litpd.service'
            command by a non root user doesn't start litp instantaneously
            while its daemon running,
            /var/run/litp_service.py.pid missing
        @tms_test_steps:
         @step: while litp is running remove file /var/run/litp_service.py.pid
            and /var/run/litp_startup_lock_file try start as non root by
            issuing systemctl start litpd.service command
         @result: Check expected message and return code, litp does not start
            instantaneously but it starts after few seconds.
         @step: restart litpd as root by systemctl restart litpd.service.
         @result: litp restarted
        @tms_test_precondition:
        - litpd service status   : active
        - litpd daemon status    : running
        - PID file               : missing (unexpected)
        - startup lock file      : missing
        @tms_execution_type: Automated
        """
        self.log('info', '1. Start litpd service')
        if not self._is_litpd_daemon_running():
            self.start_service(self.ms1, 'litpd')

        self.log('info', '2. Remove the pid file as root user')
        self.remove_item(self.ms1, const.LITP_PID_FILE,
                         su_root=True)
        self.remove_item(self.ms1, const.STARTUP_LOCK_FILE,
                         su_root=True)

        self.log('info', '3. Check that preconditions are met')
        self._assert_preconditions_are_met(
            litpd_service_status='active',
            litpd_daemon_status=RUNNING,
            pid_file=MISSING,
            startup_lock_file=MISSING)

        self.log('info', '4. Start litpd service as non root')
        stdout, _, rc = self.start_service(self.ms1, 'litpd',
                                    assert_success=False, su_root=False)

        self.log('info', '5. Check expected output and return code')
        self.assertEqual([], stdout)
        self.assertEqual(1, rc)

        self.log('info', '6. Check that litpd service has started')
        stdout, _, rc = self.get_service_status(self.ms1, 'litpd',
                         assert_running=False, su_root=False)
        self.assertTrue(self.is_text_in_list('active', stdout))
        self.assertEqual(0, rc)

        self.log('info', '7. Verify that litpd service can be restarted')
        self.restart_litpd_service(self.ms1)

    @attr('all', 'revert', 'bug13125', 'bug13125_tc28')
    def test_28_n_litpd_running_subsystem_startup_lock_non_root(self):
        """
        @tms_id: litpcds_13125_tc28
        @tms_requirements_id: LITPCDS-177
        @tms_title: Verify non root user cannot start litpd service
             instantaneously when daemon is running, pid file missing,
             unexpected startup lock file present but it starts after few
             secs.
        @tms_description: Test that issuing 'systemctl start litpd.service'
            command  by a non root user doesn't start litp instantaneously
            while its daemon is running,
            /var/run/litp_service.py.pid missing, unexpected
            /var/run/litp_startup_lock file present but is starts after few
            secs.
        @tms_test_steps:
         @step: while litp is running remove file /var/run/litp_service.py.pid
            create a /var/run/litp_startup_lock dummy file, try start as
            non root by issuing systemctl start litpd.service command
         @result: Check expected output and return code, litp does not start
            instantaneously but it starts after few secs.
         @step: restart litpd as root by systemctl restart litpd.service.
         @result: litp restarted
        @tms_test_precondition:
        - litpd service status   : active
        - litpd daemon status    : running
        - PID file               : missing (unexpected)
        - startup lock file      : present
        @tms_execution_type: Automated
        """
        self.log('info', '1. Start litpd service')
        if not self._is_litpd_daemon_running():
            self.start_service(self.ms1, 'litpd')

        self.log('info', '2. Remove the pid file as root')
        self.remove_item(self.ms1, const.LITP_PID_FILE,
                         su_root=True)

        self.log('info', '3. Create the startup lock file')
        self._create_file(const.STARTUP_LOCK_FILE)

        self.log('info', '4. Check that preconditions are met')
        self._assert_preconditions_are_met(
            litpd_service_status='active',
            litpd_daemon_status=RUNNING,
            pid_file=MISSING,
            startup_lock_file=PRESENT)

        self.log('info', '5. Start litpd service as non root')
        stdout, _, rc = self.start_service(self.ms1, 'litpd',
                                    assert_success=False, su_root=False)

        self.log('info', '6. Check expected output and return code')
        self.assertEqual([], stdout)
        self.assertEqual(1, rc)

        self.log('info', '7. Check that litpd service has started')
        stdout, _, rc = self.get_service_status(self.ms1, 'litpd',
                         assert_running=False, su_root=False)
        self.assertTrue(self.is_text_in_list('active', stdout))
        self.assertEqual(0, rc)

        self.log('info', '8. Verify that litpd service can be restarted')
        self.restart_litpd_service(self.ms1)

    #attr('all', 'revert', 'bug13125', 'bug13125_tc29')
    def obsolete_29_n_litpd_running_pid_subsystem_non_root(self):
        """
        #tms_id: litpcds_13125_tc29
        #tms_requirements_id: LITPCDS-177
        #tms_title: Verify behaviour on non root user issuing
            service litpd start
        #tms_description: Test that issuing 'service litpd start' command
            by a non root user doesn't cause any unexpected behaviour when
            litp is already running
        #tms_test_steps:
         #step: while litp is running issue service litpd start as non root
         #result: Permission denied posted, litp does not start
         #step: restart litpd as root by service litpd restart
         #result: litp restarted
        #tms_test_precondition:
        - litpd service status   : active
        - litpd daemon status    : running
        - PID file               : present
        - subsystem lock file    : does not exist in RHEL7.7
        - startup lock file      : missing
        #tms_execution_type: Automated
        """
        pass

    #attr('all', 'revert', 'bug13125', 'bug13125_tc30')
    def obsolete_30_p_litpd_running_pid_subsys_startup_lock_non_root(self):
        """
        #tms_id: litpcds_13125_tc30
        #tms_requirements_id: LITPCDS-177
        #tms_title: Verify behaviour on non root user issuing
            service litpd start when unexpected startup lock file present
        #tms_description: Test that issuing 'service litpd start'
            command by a non root user doesn't cause any unexpected behaviour
            when litp is already running and unexpected
            /var/run/litp_startup_lock
            file is present
        #tms_test_steps:
         #step: while litp is running create dummy /var/run/litp_startup_lock
            issue service litpd start as non root
         #result: Check expected output and return code, litp does not start
         #step: restart litpd as root by service litpd restart
         #result: litp restarted
        #tms_test_precondition:
        - litpd service status   : active
        - litpd daemon status    : running
        - PID file               : present
        - subsystem lock file    : missing
        - startup lock file      : present (unexpected)
        #tms_execution_type: Automated
        """
        pass

    @attr('all', 'revert', 'bug13125', 'bug13125_tc31')
    def test_31_n_litpd_running_pid_non_root(self):
        """
        @tms_id: litpcds_13125_tc31
        @tms_requirements_id: LITPCDS-177
        @tms_title: Verify behaviour on non root user issuing
            service litpd start.
        @tms_description: Test that issuing 'systemctl start litpd.service'
            command by a non root user doesn't cause any unexpected
            behaviour when litp is already runnning.
        @tms_test_steps:
         @step: while litp is running
            issue service litpd start as non root user
         @result: litp does not start
         @step: restart litpd as root by systemctl restart litpd.service.
         @result: litp restarted
        @tms_test_precondition:
        - litpd service status   : active
        - litpd daemon status    : running
        - PID file               : present
        - startup lock file      : missing
        @tms_execution_type: Automated
        """
        self.log('info', '1. Start litpd service')
        if not self._is_litpd_daemon_running():
            self.start_service(self.ms1, 'litpd')

        self.log('info', '2. Prepare preconditions')
        self._create_file(const.LITP_PID_FILE)
        self.log('info', '3. Check that preconditions are met')
        self._assert_preconditions_are_met(
            litpd_service_status='active',
            litpd_daemon_status=RUNNING,
            pid_file=PRESENT,
            startup_lock_file=MISSING)

        self.log('info', '4. Start litpd service as non root')
        stdout, _, rc = self.start_service(self.ms1, 'litpd',
                                    assert_success=False, su_root=False)

        self.log('info', '5. Check expected output and return code')
        self.assertEqual([], stdout)
        self.assertEqual(1, rc)

        self.log('info', '6. Check that litpd service is still running')
        self.get_service_status(self.ms1, 'litpd', su_root=False)

        self.log('info', '7. Verify that litpd service can be restarted')
        self.restart_litpd_service(self.ms1)

    @attr('all', 'revert', 'bug13125', 'bug13125_tc32')
    def test_32_p_litpd_running_pid_startup_lock_non_root(self):
        """
        @tms_id: litpcds_13125_tc32
        @tms_requirements_id: LITPCDS-177
        @tms_title: Verify behaviour on non root user issuing
            service litpd start when unexpected startup lock file exists
        @tms_description: Test that issuing 'systemctl start litpd.service'
            command by a non root user doesn't cause any unexpected behavior
            when litp is already running and
            unexpected /var/run/litp_startup_lock exists
        @tms_test_steps:
         @step: when litp is running
            create a dummy /var/run/litp_startup_lock file
            issue service litpd start as non root
         @result: Check expected output and return code, litp does not start
            instantaneously but it starts after few secs.
         @step: restart litpd as root by systemctl restart litpd.service
         @result: litp restarted
        @tms_test_precondition:
        - litpd service status   : active
        - litpd daemon status    : running
        - PID file               : present
        - startup lock file      : present (unexpected)
        @tms_execution_type: Automated
        """
        self.log('info', '1. Start litpd service')
        if not self._is_litpd_daemon_running():
            self.start_service(self.ms1, 'litpd')

        self.log('info', '2. Create the startup lock file')
        self._create_file(const.STARTUP_LOCK_FILE)
        self._create_file(const.LITP_PID_FILE)

        self.log('info', '3. Check that preconditions are met')
        self._assert_preconditions_are_met(
            litpd_service_status='active',
            litpd_daemon_status=RUNNING,
            pid_file=PRESENT,
            startup_lock_file=PRESENT)

        self.log('info', '4. Start litpd service as non root')
        stdout, _, rc = self.start_service(self.ms1, 'litpd',
                                    assert_success=False, su_root=False)

        self.log('info', '5. Check expected output and return code')
        self.assertEqual([], stdout)
        self.assertEqual(1, rc)

        self.log('info', '6. Check that litpd service is running')
        self.get_service_status(self.ms1, 'litpd', su_root=False)

        self.log('info', '7. Verify that litpd service can be restarted')
        self.restart_litpd_service(self.ms1)

    @attr('all', 'revert', 'bug13125', 'bug13125_t33')
    def test_33_n_litpd_starting_root(self):
        """
        @tms_id: litpcds_13125_tc33
        @tms_requirements_id: LITPCDS-177
        @tms_title: Check behaviour on issuing 'systemctl start litpd.service'
            when the litpd service is starting and the startup lock file is
            unexpectedly missing
        @tms_description: Test that issuing 'systemctl start litpd.service'
            command by a root user doesn't cause any unexpected behaviour when
            litp is starting and expected /var/run/litp_startup_lock
            file is missing
        @tms_test_steps:
         @step: stop litp, patch to add sleep during startup, restart
         @result: litp starts
         @step: while litp is starting remove /var/run/litp_startup_lock file
            issue systemctl start litpd.service as root user.
         @result: Check expected output and return code.
         @step: check that initial litp start successful
         @result: litp started
        @tms_test_precondition:
        - litpd daemon status    : not running
        - PID file               : missing
        - startup lock file      : missing (unexpected)
        @tms_execution_type: Automated
        """
        litp_service_patch_file_path = '/tmp/13125_tc33.diff'
        try:
            self.log('info',
            '1. Stop litp')
            self._stop_litpd_service()

            self.log('info',
            '2. Patch litp service.py to inject a delay to daemonize '
               'the litpd process')
            self._apply_patch_to_litp_service(litp_service_patch_file_path)

            self.log('info',
            '3. Start litp in background')
            self._start_patched_litpd()

            self.log('info',
            '4. Remove startup lock file')
            self.remove_item(self.ms1, const.STARTUP_LOCK_FILE, su_root=True)

            self.log('info',
            '5. Check that preconditions are met')
            self._assert_preconditions_are_met(
                litpd_daemon_status=NOT_RUNNING,
                pid_file=MISSING,
                startup_lock_file=MISSING)

            self.log('info',
            '6. Start an instance of litpd while another one is already'
                'starting in the background and check the expected output'
                'and retun code')
            stdout, _, rc = self.start_service(self.ms1, 'litpd')
            self.assertEqual([], stdout)
            self.assertEqual(0, rc)

        finally:
            self.log('info', '7. Wait for "litpd" service to start')
            self.wait_for_cmd(self.ms1,
                              self.rhc.get_service_running_cmd('litpd'),
                              expected_rc=0,
                              default_time=2)
            self._remove_patch_to_litp_service(litp_service_patch_file_path)

    @attr('all', 'revert', 'bug13125', 'bug13125_t34')
    def test_34_n_litpd_starting_startup_lock_root(self):
        """
        @tms_id: litpcds_13125_tc34
        @tms_requirements_id: LITPCDS-177
        @tms_title: Check behaviour on issuing 'systemctl start litpd.service'
            when the litpd service is starting before daemonized
        @tms_description: Test that issuing 'systemctl start litpd.service'
            command by a root user doesn't cause any unexpected behaviour
            when litp is starting before daemonized
        @tms_test_steps:
         @step: stop litp, patch to add sleep during startup, restart
         @result: litp starts
         @step: while litp is starting issue service litpd start as root
         @result: Check expected output and return code
         @step: check that initial litp start successful
         @result: litp started
        @tms_test_precondition:
        - litpd daemon status    : not running
        - PID file               : missing
        - startup lock file      : present
        @tms_execution_type: Automated
        """
        litp_service_patch_file_path = '/tmp/13125_tc34.diff'
        try:
            self.log('info',
            '1. Stop litp')
            self._stop_litpd_service()

            self.log('info',
            '2. Patch litp service.py to inject a delay to daemonize '
               'the litpd process')
            self._apply_patch_to_litp_service(litp_service_patch_file_path)

            self.log('info',
            '3. Start litp in background')
            self._start_patched_litpd()

            self.log('info',
            '4. Check that preconditions are met')
            self._assert_preconditions_are_met(
                litpd_daemon_status=NOT_RUNNING,
                pid_file=MISSING,
                startup_lock_file=PRESENT)

            self.log('info',
            '5. start litp service while starting in background')
            stdout, _, rc = self.start_service(self.ms1, 'litpd')

            self.log('info',
            '6. Check expected output and return code')
            self.assertEqual(0, rc)
            self.assertEqual([], stdout)
        finally:
            self.log('info',
            '7. Check service starts')
            self.wait_for_cmd(self.ms1,
                              self.rhc.get_service_running_cmd('litpd'),
                              expected_rc=0,
                              default_time=2)
            self._remove_patch_to_litp_service(litp_service_patch_file_path)

    @attr('all', 'revert', 'bug13125', 'bug13125_t35')
    def test_35_n_litpd_starting_subsys_root(self):
        """
        @tms_id: litpcds_13125_tc35
        @tms_requirements_id: LITPCDS-177
        @tms_title: Check behaviour on issuing 'systemctl start litpd.service'
            when the litpd service is starting before daemonized,
            and an expected statup lock file is missing
        @tms_description: Test that issuing 'systemctl start litpd.service'
            command by a root user doesn't cause any unexpected behaviour when
            litp is starting before daemonized when
            /var/run/litp_startup_lock file is missing
        @tms_test_steps:
         @step: stop litp, patch to add sleep during startup, restart
         @result: litp starts
         @step: while litp is starting remove /var/run/litp_startup_lock
            and issue systemctl start litpd.service command as root user.
         @result: No output returned and return code is 0
         @step: check that initial litp start successful
         @result: litp started
        @tms_test_precondition:
        - litpd daemon status    : not running
        - PID file               : missing
        - startup lock file      : missing (unexpected)
        @tms_execution_type: Automated
        """
        litp_service_patch_file_path = '/tmp/13125_tc35.diff'
        try:
            self.log('info',
            '1. Stop litp')
            self._stop_litpd_service()

            self.log('info',
            '2. Patch litp service.py to inject a delay to daemonize '
               'the litpd process')
            self._apply_patch_to_litp_service(litp_service_patch_file_path)

            self.log('info',
            '3. Start litp in background')
            self._start_patched_litpd()

            self.log('info',
            '4. prepare preconditions')
            self.remove_item(self.ms1, const.STARTUP_LOCK_FILE, su_root=True)

            self.log('info',
            '5. Check that preconditions are met')
            self._assert_preconditions_are_met(
                litpd_daemon_status=NOT_RUNNING,
                pid_file=MISSING,
                startup_lock_file=MISSING)

            self.log('info',
            '6. start litp service while starting in background')
            stdout, _, rc = self.start_service(self.ms1, 'litpd')

            self.log('info',
            '6. Check expected output and return code')
            self.assertEqual([], stdout)
            self.assertEqual(0, rc)

        finally:
            self.log('info',
            '7. Check service starts')
            self.wait_for_cmd(self.ms1,
                              self.rhc.get_service_running_cmd('litpd'),
                              expected_rc=0,
                              default_time=2)
            self._remove_patch_to_litp_service(litp_service_patch_file_path)

    @attr('all', 'revert', 'bug13125', 'bug13125_t36')
    def test_36_n_litpd_starting_subsys_startup_lock_root(self):
        """
        @tms_id: litpcds_13125_tc36
        @tms_requirements_id: LITPCDS-177
        @tms_title: Check behaviour on issuing 'systemctl start litpd.service'
            when the litpd service is starting before daemonized.
        @tms_description: Test that issuing 'systemctl start litpd.service'
            command by a root user doesn't cause any unexpected behaviour when
            litp is starting before daemonized.
        @tms_test_steps:
         @step: stop litp, patch to add sleep during startup, restart
         @result: litp starts
         @step: while litp is starting remove /var/run/litp_startup_lock
            issue service litpd start as root
         @result: Check that the second start of litpd service returns no
                  output and return code 0.
         @step: check that initial litp start successful
         @result: litp started
        @tms_test_precondition:
        - litpd daemon status    : not running
        - PID file               : missing
        - startup lock file      : present
        @tms_execution_type: Automated
        """
        litp_service_patch_file_path = '/tmp/13125_tc36.diff'
        try:
            self.log('info',
            '1. Stop litp')
            self._stop_litpd_service()

            self.log('info',
            '2. Patch litp service.py to inject a delay to daemonize '
               'the litpd process')
            self._apply_patch_to_litp_service(litp_service_patch_file_path)

            self.log('info',
            '3. Start litp in background')
            self._start_patched_litpd()

            self.log('info',
            '4. Check that preconditions are met')
            self._assert_preconditions_are_met(
                litpd_daemon_status=NOT_RUNNING,
                pid_file=MISSING,
                startup_lock_file=PRESENT)

            self.log('info',
            '6. start litp service while starting in background')
            stdout, _, rc = self.start_service(self.ms1, 'litpd')

            self.log('info',
            '7. Check expected output and return code')
            self.assertEqual(0, rc)
            self.assertEqual([], stdout)

        finally:
            self.log('info',
            '8. Check service starts')
            self.wait_for_cmd(self.ms1,
                              self.rhc.get_service_running_cmd('litpd'),
                              expected_rc=0,
                              default_time=2)
            self._remove_patch_to_litp_service(litp_service_patch_file_path)

    @attr('all', 'revert', 'bug13125', 'bug13125_t37')
    def test_37_n_litpd_starting_pid_susbsys_root(self):
        """
        @tms_id: litpcds_13125_tc37
        @tms_requirements_id: LITPCDS-177
        @tms_title: Check behaviour on issuing 'systemctl start litpd.service'
            when the litpd service is starting before daemonized,
            an expected startup lock file is missing and unexpected
            pid file present
        @tms_description: Test that issuing 'systemctl start litpd.service'
            command by a root user doesn't cause any unexpected behaviour when
            litp is starting before daemonized when there's unexpected file
            /var/run/litp_service.py.pid present
            and the expected /var/run/litp_startup_lock file is missing
        @tms_test_steps:
         @step: stop litp, patch to add sleep during startup, restart
         @result: litp starts
         @step: while litp is starting remove /var/run/litp_startup_lock
            and create a dummy
            /var/run/litp_service.py.pid with an invalid value (like 9999999)
            issue service litpd start as root
         @result: Check expected output and return code
         @step: check that initial litp start successful
         @result: litp started
        @tms_test_precondition:
        - litpd daemon status    : not running
        - PID file               : present (unexpected)
        - startup lock file      : missing (unexpected)
        @tms_execution_type: Automated
        """
        litp_service_patch_file_path = '/tmp/13125_tc37.diff'
        try:
            self.log('info',
            '1. Stop litp')
            self._stop_litpd_service()

            self.log('info',
            '2. Patch litp service.py to inject a delay to daemonize '
               'the litpd process')
            self._apply_patch_to_litp_service(litp_service_patch_file_path)

            self.log('info',
            '3. Start litp in background')
            self._start_patched_litpd()

            self.log('info',
            '4. prepare preconditions')
            self._create_file(const.LITP_PID_FILE)
            self.remove_item(self.ms1, const.STARTUP_LOCK_FILE, su_root=True)

            self.log('info',
            '5. Check that preconditions are met')
            self._assert_preconditions_are_met(
                litpd_daemon_status=NOT_RUNNING,
                pid_file=PRESENT,
                startup_lock_file=MISSING)

            self.log('info',
            '6. start litp service while starting in background')
            stdout, _, rc = self.start_service(self.ms1, 'litpd')

            self.log('info',
            '7. Check expected output and return code')
            self.assertEqual(0, rc)
            self.assertEqual([], stdout)

        finally:
            self.log('info',
            '7. Check service starts')
            self.wait_for_cmd(self.ms1,
                              self.rhc.get_service_running_cmd('litpd'),
                              expected_rc=0,
                              default_time=2)
            self._remove_patch_to_litp_service(litp_service_patch_file_path)

    @attr('all', 'revert', 'bug13125', 'bug13125_t38')
    def test_38_n_litpd_starting_pid_subsys_startup_lock_root(self):
        """
        @tms_id: litpcds_13125_tc38
        @tms_requirements_id: LITPCDS-177
        @tms_title: Check behaviour on issuing 'systemctl start litpd.service'
            when the litpd service is starting before daemonized,
            and unexpected pid file present
        @tms_description: Test that issuing 'systemctl start litpd.service'
            command by a root user doesn't cause any unexpected behaviour when
            litp is starting before daemonized when there's unexpected file
            /var/run/litp_service.py.pid present
        @tms_test_steps:
         @step: stop litp, patch to add sleep during startup, restart
         @result: litp starts
         @step: while litp is starting,
            create a dummy /var/run/litp_service.py.pid with an invalid value
            (like 9999999) issue service litpd start as root
         @result: Check expected output and return code
         @step: check that initial litp start successful
         @result: litp started
        @tms_test_precondition:
        - litpd daemon status    : not running
        - PID file               : present (unexpected)
        - startup lock file      : present
        @tms_execution_type: Automated
        """
        litp_service_patch_file_path = '/tmp/13125_tc38.diff'
        try:
            self.log('info',
            '1. Stop litp, patch')
            self._stop_litpd_service()

            self.log('info',
            '2. Patch litp service.py to inject a delay to daemonize '
               'the litpd process')
            self._apply_patch_to_litp_service(litp_service_patch_file_path)

            self.log('info',
            '3. Start litp in background')
            self._start_patched_litpd()

            self.log('info',
            '4. prepare preconditions')
            self._create_file(const.LITP_PID_FILE)

            self.log('info',
            '5. Check that preconditions are met')
            self._assert_preconditions_are_met(
                litpd_daemon_status=NOT_RUNNING,
                pid_file=PRESENT,
                startup_lock_file=PRESENT)

            self.log('info',
            '6. start litp service while starting in background')
            stdout, _, rc = self.start_service(self.ms1, 'litpd')

            self.log('info',
            '7. Check expected output and return code')
            self.assertEqual(0, rc)
            self.assertEqual([], stdout)

        finally:
            self.log('info',
            '8. Check service starts')
            self.wait_for_cmd(self.ms1,
                              self.rhc.get_service_running_cmd('litpd'),
                              expected_rc=0,
                              default_time=2)
            self._remove_patch_to_litp_service(litp_service_patch_file_path)

    @attr('all', 'revert', 'bug13125', 'bug13125_t39')
    def test_39_n_litpd_starting_pid_root(self):
        """
        @tms_id: litpcds_13125_tc39
        @tms_requirements_id: LITPCDS-177
        @tms_title: Check behaviour on issuing 'systemctl start litpd.service'
            when the litpd service is starting before daemonized,
            an expected statup lock file is missing,
            unexpected pid file present
        @tms_description: Test that issuing 'systemctl start litpd.service'
            command by a root user doesn't cause any unexpected behaviour when
            litp is starting before daemonized when there's an unexpected file
            /var/run/litp_service.py.pid present and the expected
            /var/run/litp_startup_lock file is missing.
        @tms_test_steps:
         @step: stop litp, patch to add sleep during startup, restart
         @result: litp starts
         @step: while litp is starting remove /var/run/litp_startup_lock
            and create a dummy /var/run/litp_service.py.pid with an
            invalid value (like 9999999) issue service litpd start as root
         @result: Check expected output and return code
         @step: check that initial litp start successful
         @result: litp started
        @tms_test_precondition:
        - litpd daemon status    : not running
        - PID file               : present (unexpected)
        - startup lock file      : missing (unexpected)
        @tms_execution_type: Automated
        """
        litp_service_patch_file_path = '/tmp/13125_tc39.diff'
        try:
            self.log('info',
            '1. Stop litp')
            self._stop_litpd_service()

            self.log('info',
            '2. Patch litp service.py to inject a delay to daemonize '
               'the litpd process')
            self._apply_patch_to_litp_service(litp_service_patch_file_path)

            self.log('info',
            '3. Start litp in background')
            self._start_patched_litpd()

            self.log('info',
            '4. prepare preconditions')
            self._create_file(const.LITP_PID_FILE)
            self.remove_item(self.ms1, const.STARTUP_LOCK_FILE, su_root=True)

            self.log('info',
            '5. Check that preconditions are met')
            self._assert_preconditions_are_met(
                litpd_daemon_status=NOT_RUNNING,
                pid_file=PRESENT,
                startup_lock_file=MISSING)

            self.log('info',
            '6. start litp service while starting in background')
            stdout, _, rc = self.start_service(self.ms1, 'litpd')

            self.log('info',
            '7. Check expected output and return code')
            self.assertEqual(0, rc)
            self.assertEqual([], stdout)

        finally:
            self.log('info',
            '8. Check service starts')
            self.wait_for_cmd(self.ms1,
                              self.rhc.get_service_running_cmd('litpd'),
                              expected_rc=0,
                              default_time=2)
            self._remove_patch_to_litp_service(litp_service_patch_file_path)

    @attr('all', 'revert', 'bug13125', 'bug13125_t40')
    def test_40_n_litpd_starting_pid_startup_lock_root(self):
        """
        @tms_id: litpcds_13125_tc40
        @tms_requirements_id: LITPCDS-177
        @tms_title: Check behaviour on issuing 'service litpd start'
            when the litpd service is starting before daemonized,
            unexpected pid file present
        @tms_description: Test that issuing 'systemctl start litpd.service'
            command by a root user doesn't cause any unexpected behaviour when
            litp is starting before daemonized when there's an unexpected file
            /var/run/litp_service.py.pid present
        @tms_test_steps:
         @step: stop litp, patch to add sleep during startup, restart
         @result: litp starts
         @step: while litp is starting create a dummy
            /var/run/litp_service.py.pid with an invalid value (like 9999999)
             issue service litpd start as root
         @result: Check expected output and return code
         @step: check that initial litp start successful
         @result: litp started
        @tms_test_precondition:
        - litpd daemon status    : not running
        - PID file               : present (unexpected)
        - startup lock file      : present
        @tms_execution_type: Automated
        """
        litp_service_patch_file_path = '/tmp/13125_tc40.diff'
        try:
            self.log('info',
            '1. Stop litp')
            self._stop_litpd_service()

            self.log('info',
            '2. Patch litp service.py to inject a delay to daemonize '
               'the litpd process')
            self._apply_patch_to_litp_service(litp_service_patch_file_path)

            self.log('info',
            '3. Start litp in background')
            self._start_patched_litpd()

            self.log('info',
            '4. prepare preconditions')
            self._create_file(const.LITP_PID_FILE)

            self.log('info',
            '5. Check that preconditions are met')
            self._assert_preconditions_are_met(
                litpd_daemon_status=NOT_RUNNING,
                pid_file=PRESENT,
                startup_lock_file=PRESENT)

            self.log('info',
            '6. start litp service while starting in background')
            stdout, _, rc = self.start_service(self.ms1, 'litpd')

            self.log('info',
            '7. Check expected output and return code')
            self.assertEqual(0, rc)
            self.assertEqual([], stdout)

        finally:
            self.log('info',
            '7. Check service starts')
            self.wait_for_cmd(self.ms1,
                              self.rhc.get_service_running_cmd('litpd'),
                              expected_rc=0,
                              default_time=2)
            self._remove_patch_to_litp_service(litp_service_patch_file_path)

    @attr('all', 'revert', 'bug13125', 'bug13125_t41')
    def test_41_n_litpd_running_non_root(self):
        """
        @tms_id: litpcds_13125_tc41
        @tms_requirements_id: LITPCDS-177
        @tms_title: Check behaviour on issuing 'systemctl start litpd.service'
            by  non root when the litpd service is starting and the startup
            lock file is unexpectedly missing
        @tms_description: Test that issuing 'systemctl start litpd.service'
            command by a non root user doesn't cause any unexpected behaviour
            when  litp is starting and expected /var/run/litp_startup_lock
            file is missing
        @tms_test_steps:
         @step: stop litp, patch to add sleep during startup, restart
         @result: litp starts
         @step: while litp is starting remove /var/run/litp_startup_lock file
            issue service litpd start as non root
         @result: Check expected output and return code
         @step: check that initial litp start successful
         @result: litp started
        @tms_test_precondition:
        - litpd daemon status    : not running
        - PID file               : present
        - startup lock file      : missing (unexpected)
        @tms_execution_type: Automated
        """
        litp_service_patch_file_path = '/tmp/13125_tc41.diff'
        try:
            self.log('info',
            '1. Stop litp')
            self._stop_litpd_service()

            self.log('info',
            '2. Patch litp service.py to inject a delay to daemonize '
               'the litpd process')
            self._apply_patch_to_litp_service(litp_service_patch_file_path)

            self.log('info',
            '3. Start litp in background')
            self._start_patched_litpd()

            self.log('info',
            '4. prepare preconditions')
            self.remove_item(self.ms1, const.STARTUP_LOCK_FILE, su_root=True)

            self.log('info',
            '5. Check that preconditions are met')
            self._assert_preconditions_are_met(
                litpd_daemon_status=NOT_RUNNING,
                pid_file=MISSING,
                startup_lock_file=MISSING)

            self.log('info',
            '6. start litp as non-root while already starting')
            stdout, _, rc = self.start_service(self.ms1, 'litpd',
                                               assert_success=False,
                                               su_root=False)
            self.log('info',
            '7. Check expected output and return code')
            self.assertEqual([], stdout)
            self.assertEqual(1, rc, "returned code should be 1")

        finally:
            self.log('info',
            '8. Check initial service start successful')
            self.wait_for_cmd(self.ms1,
                              self.rhc.get_service_running_cmd('litpd'),
                              expected_rc=0,
                              default_time=2)
            self._remove_patch_to_litp_service(litp_service_patch_file_path)
