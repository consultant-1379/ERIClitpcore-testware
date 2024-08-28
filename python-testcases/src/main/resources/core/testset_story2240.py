'''
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     October 2013
@author:    Ares
@summary:   Integration test for ___
            Agile:
                Epic:
                Story:
                Sub-Task:
'''
import os
import test_constants as const
from litp_generic_test import GenericTest, attr
from litp_cli_utils import CLIUtils
from rest_utils import RestUtils
from redhat_cmd_utils import RHCmdUtils


class Story2240(GenericTest):
    """
    LITPCDS-2240: As a system designer I want of the states of the plan
                  represented in the execution manager so that plan feedback is
                  more understandable.
    """

    def setUp(self):
        """
        Description:
            Runs before every test to perform required test setup
        """
        # call super class setup
        super(Story2240, self).setUp()
        # management server to run test on
        self.management_node = self.get_management_node_filename()
        self.rhc = RHCmdUtils()
        self.ms_ip_address = self.get_node_att(self.management_node, 'ipv4')
        # setup test utilities
        self.cli = CLIUtils()
        self.rest = RestUtils(self.ms_ip_address)
        # packages to be used for the test
        self.package = 'finger'
        self.fail = 'fingeerr'
        self.plugin_id = 'story2240'

    def tearDown(self):
        """
        Description:
            Runs after every test to perform required cleanup/teardown
        """

        # call super class teardown
        super(Story2240, self).tearDown()

    def _exec_common_test_methods(self, package):
        """not needed anymore but obsolete_* need it or pylint will weep"""
        pass

    @staticmethod
    def get_local_rpm_paths(path, rpm_substring):
        """
        given a path (which should contain some RPMs) and a substring
        which is present in the RPM names you want, return a list of
        absolute paths to the RPMS that are local to your test
        """
        # get all RPMs in 'path' that contain 'rpm_substring' in their name
        rpm_names = [rpm for rpm in os.listdir(path) if rpm_substring in rpm]

        if not rpm_names:
            return None

        # return a list of absolute paths to the RPMs found in 'rpm_names'
        return [
            os.path.join(rpath, rpm)
            for rpath, rpm in
            zip([os.path.abspath(path)] * len(rpm_names), rpm_names)
        ]

    def _install_item_extension(self):
        """
        check if a plugin/extension rpm is installed and if not, install it
        """
        _, _, rcode = self.run_command(
            self.management_node,
            self.rhc.check_pkg_installed([self.plugin_id]),
            su_root=True
        )

        if rcode == 1:
            # copy over and install RPMs
            local_rpm_paths = self.get_local_rpm_paths(
                os.path.abspath(os.path.join(os.path.dirname(__file__),
                                             'plugins')), self.plugin_id
            )

            self.assertTrue(
                self.copy_and_install_rpms(
                    self.management_node, local_rpm_paths
                )
            )

    def create_lock(self, lock_file):
        """create lock file that'll keep a task from succeeding"""
        self.run_command(self.management_node, "touch {0}".format(lock_file))

    def release_lock(self, lock_file):
        """remove lock file that keeps a task from succeeding"""
        self.run_command(self.management_node, "rm -f {0}".format(lock_file))

    def get_ms_node(self):
        """what says on the tin"""
        return self.find(self.management_node, '/', 'ms')[0]

    def create_ms_config_item(self, item_id):
        """create test items; their type extends node-config base type"""
        ms_ = self.get_ms_node()
        path = '{0}/configs/{1}'.format(ms_, item_id)
        _, _, rcode = self.execute_cli_create_cmd(self.management_node, path,
                                                  "story2240-node-config")
        if rcode == 0:
            return path

    @attr('all', 'revert', 'story2240', 'story2240_tc01')
    def test_01_n_no_remove_create_run_plan_state_running(self):
        """
        @tms_id: litpcds_2240_tc01
        @tms_requirements_id: LITPCDS-2240
        @tms_title: Reject plan commands while plan is running
        @tms_description:
            While a plan is currently running, if a user executes the
            remove_plan/create_plan/run_plan/
            create_snapshot/remove_snapshot/restore_snapshot commands, an error
            must be given stating that a deployment/snapshot plan cannot be
            removed/created/run/(restored) while running and the running plan
            must proceed unimpeded.
        @tms_test_steps:
            @step: Install plugin that blocks a task until a file is deleted
            @result: block task plugin is installed
            @step: Install plugin that stops snapshot plans in the first phase
            @result: Stop snapshot plan plugin is installed
            @step: Create/Run plan
            @result: Plan is running
            @step: Execute the remove_plan command
            @result: InvalidRequestError is raised
            @step: Execute the create_plan command
            @result: InvalidRequestError is raised
            @step: Execute the run_plan command
            @result: InvalidRequestError is raised
            @step: Execute the create_snapshot command
            @result: InvalidRequestError is raised
            @step: Execute the remove_snapshot command
            @result: InvalidRequestError is raised
            @step: Execute the restore_snapshot command
            @result: InvalidRequestError is raised
            @step: Delete locking file
            @result: Task completes
            @result: PLan completes
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        self.log('info',
                 'Install plugin that blocks a task until a file is deleted')

        self._install_item_extension()
        plugin_name = \
            "ERIClitp_fail_snapshotplan_CXP1234567-1.0.1-0.noarch.rpm"

        rpm_path = os.path.join(os.path.dirname(__file__),
                                '2240_rpms/{0}'.format(plugin_name))

        self.log('info',
                 'Install plugin that stops snapshot plans in the first phase')
        self.copy_and_install_rpms(self.management_node, [rpm_path])

        lock_item = "story2240_tc01_lock"
        lock_path = "/tmp/" + lock_item
        errors = dict()
        try:
            # create config item
            self.create_ms_config_item(lock_item)

            self.log('info', 'Create/Run plan')
            # execute the create_plan command
            self.execute_cli_createplan_cmd(self.management_node)

            # create lock file that's checked by callback task
            self.create_lock(lock_path)

            # execute the run_plan command
            self.execute_cli_runplan_cmd(self.management_node)
            self.assertTrue(self.wait_for_plan_state(self.management_node,
                                                     const.PLAN_IN_PROGRESS))

            self.log('info',
                     'execute the remove_plan command and check for errors')
            _, stderr, _ = self.execute_cli_removeplan_cmd(
                self.management_node,
                expect_positive=False)
            expected_errors = [{
                'url': '/plans/plan',
                'error_type': 'InvalidRequestError',
                'msg': 'Removing a running/stopping plan is not allowed'}]
            errors['remove_plan'] = \
                self.check_cli_errors(expected_errors, stderr)

            self.log('info',
                     'execute the create_plan command and check for errors')
            _, stderr, _ = self.execute_cli_createplan_cmd(
                self.management_node, expect_positive=False)
            expected_errors = [{
                'url': '/plans/plan',
                'error_type': 'InvalidRequestError',
                'msg': 'Plan already running'}]

            errors['create_plan'] = \
                self.check_cli_errors(expected_errors, stderr)

            self.log('info',
                     'execute the run_plan command and check for errors')
            _, stderr, _ = self.execute_cli_runplan_cmd(self.management_node,
                                                        expect_positive=False)
            expected_errors = [{
                'url': '/plans/plan',
                'error_type': 'InvalidRequestError',
                'msg': 'Plan is currently running or stopping'}]
            errors['run_plan'] = \
                self.check_cli_errors(expected_errors, stderr)

            self.log('info',
                     'execute the create_snapshot command '
                     'and check for errors')
            _, stderr, _ = self.execute_cli_createsnapshot_cmd(
                    self.management_node, expect_positive=False)
            expected_errors = [{
                'error_type': 'InvalidRequestError',
                'msg': 'Plan already running'}]
            errors['create_snapshot'] = \
                self.check_cli_errors(expected_errors, stderr)

            self.log('info',
                     'execute the remove_snapshot command and'
                     ' check for errors')
            _, stderr, _ = self.execute_cli_removesnapshot_cmd(
                    self.management_node, expect_positive=False)
            errors['remove_snapshot'] = \
                self.check_cli_errors(expected_errors, stderr)

            self.log('info',
                     'execute the restore_snapshot command and check '
                     'for errors')
            _, stderr, _ = self.execute_cli_restoresnapshot_cmd(
                    self.management_node, expect_positive=False)
            errors['restore_snapshot'] = \
                self.check_cli_errors(expected_errors, stderr)

            # allow locked task complete
            self.release_lock(lock_path)
            # wait for plan to complete
            self.assertTrue(self.wait_for_plan_state(self.management_node,
                                                     const.PLAN_COMPLETE))

            # check for errors
            self.assertFalse(any([any(error) for error in errors.values()]),
                             errors)
        finally:
            self.release_lock(lock_path)
            self.wait_for_plan_state(self.management_node,
                                     const.PLAN_COMPLETE)
            # plan has to be removed before the snapshot plugin can be
            # deinstalled otherwise litp could not load the (failed)
            # snapshot plan
            remove_plan_cmd = self.cli.get_remove_plan_cmd()
            self.run_command(self.management_node, remove_plan_cmd)
            self.remove_rpm_on_node(self.management_node, plugin_name)

    @attr('all', 'revert')
    def obsolete_02_p_stop_plan_state_running(self):
        """
        Obsolete:
            TC03 already asserts every aspect of this test while
            performing negative tests against a stopping plan. Removing as part
            of KGB time maintenance
        Description:
            While a plan is currently running, if a user executes the stop_plan
            command, the plan will stop successfully.

        Pre-Requisites:
            1. A running litpd service

        Actions:
            1. Execute the create command on an item in the model tree
            2. Execute the create_plan command
            3. Execute the run_plan command
            4. Check the plan state is set to Running
            5. Execute the stop_plan command
            6. Check the plan state changes to Stopping
            7. Check the plan state is finally set to Stopped

        Restore:
            1. Remove the created model item from the model tree
            2. Execute the create_plan command

        Results:
            Stopping a running plan is allowed
        """
        self._install_item_extension()

        lock_item = "story2240_tc02_lock"
        lock_path = "/tmp/" + lock_item
        after_item = "story2240_tc02_after"
        try:
            # create config items
            self.create_ms_config_item(lock_item)
            self.create_ms_config_item(after_item)
            # execute the create_plan command
            self.execute_cli_createplan_cmd(self.management_node)

            # create lock file that's checked by callback task
            self.create_lock(lock_path)
            # execute the run_plan command
            self.execute_cli_runplan_cmd(self.management_node)
            self.assertTrue(self.wait_for_plan_state(self.management_node,
                                                     const.PLAN_IN_PROGRESS))
            # execute the stop_plan command and check plan state changes from
            # Running to Stopping and finally Stopped
            self.execute_cli_stopplan_cmd(self.management_node)
            self.assertTrue(self.wait_for_plan_state(self.management_node,
                                                     const.PLAN_STOPPING))
            # enable completion of the locked task
            self.release_lock(lock_path)
            self.assertTrue(self.wait_for_plan_state(self.management_node,
                                                     const.PLAN_STOPPED))
        finally:
            self.release_lock(lock_path)

    @attr('all', 'revert', 'story2240', 'story2240_tc03')
    def test_03_n_no_remove_create_run_stop_plan_state_stopping(self):
        """
        @tms_id: litpcds_2240_tc03
        @tms_requirements_id: LITPCDS-2240
        @tms_title: Verify the user can't execute the
             remove_plan/create_plan/run_plan/stop_plan commands
             while stopping and the running plan must stop unimpeded.
        @tms_description:
            While a plan is currently stopping, if a user executes the
            remove_plan/create_plan/run_plan/stop_plan commands, an error is
            given stating that a plan cannot be removed/created/run/stopped
            while stopping and the running plan will stop unimpeded.
            Note: TC02 and TC11 merged for brevity and said TCs have been made
            obsolete
        @tms_test_steps:
            @step: Execute the create command on an item in the model tree,
                create and run plan.
            @result: The plan state is set to Running
            @step: Execute the stop_plan command, and execute
                 the remove_plan command.
            @result: An error message is displayed, and the plan state
                 is still Stopping.
            @step: While stop_plan command is not finished, execute
                 the create_plan command.
            @result: An error message is displayed, and the plan state
                 is still Stopping.
            @step: While stop_plan command is not finished, execute
                 the run_plan command.
            @result: An error message is displayed, and the plan state
                 is still Stopping.
            @step: While stop_plan command is not finished, execute
                 the stop_plan command.
            @result: An error message is displayed, and the plan state
                 is still Stopping.
            @step: After the plan status is changed to Stopped execute
                 the run_plan and create_plan commands.
            @result: The successful tasks were not added to the plan a
                 second time.
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        self._install_item_extension()

        lock_item = "story2240_tc03_lock"
        after_item = "story2240_tc03_after"
        lock_path = "/tmp/" + lock_item
        try:
            self.log('info',
                     'Execute the create command on an item in the model tree,'
                     ' create and run plan.')
            # create config items
            self.create_ms_config_item(lock_item)
            self.create_ms_config_item(after_item)
            # execute the create_plan command
            self.execute_cli_createplan_cmd(self.management_node)

            # create lock file that's checked by callback task
            self.create_lock(lock_path)

            # execute the run_plan command
            self.execute_cli_runplan_cmd(self.management_node)
            self.assertTrue(self.wait_for_plan_state(self.management_node,
                                                     const.PLAN_IN_PROGRESS))
            self.log('info',
                     'Execute the stop_plan command, and execute'
                     ' the remove_plan command.')
            # execute the stop_plan command
            self.execute_cli_stopplan_cmd(self.management_node)
            self.assertTrue(self.wait_for_plan_state(self.management_node,
                                                     const.PLAN_STOPPING))
            # execute the remove_plan command, while plan is Stopping and check
            # for errors
            _, stderr, _ = self.execute_cli_removeplan_cmd(
                self.management_node, expect_positive=False)
            expect_err = ('InvalidRequestError    '
                          'Removing a running/stopping plan is not allowed')
            self.assertTrue(self.is_text_in_list(expect_err, stderr),
                            "Expected error message '{0}' "
                            "not found in stderr: '{1}'".format(expect_err,
                                                                stderr))
            self.log('info',
                     'While stop_plan command is not finished execute,'
                     ' the create_plan command.')
            # execute the create_plan command while is Stopping and check for
            # errors
            _, stderr, _ = self.execute_cli_createplan_cmd(
                self.management_node, expect_positive=False)
            expect_err = ('InvalidRequestError    '
                          'Create plan failed: '
                          'Previous plan is still stopping')
            self.assertTrue(self.is_text_in_list(expect_err, stderr),
                            "Expected error message '{0}' "
                            "not found in stderr: '{1}'".format(expect_err,
                                                                stderr))
            self.log('info',
                     'While stop_plan command is not finished, execute'
                     ' the run_plan command.')
            # execute the run_plan command while plan is Stopping and check for
            # errors
            _, stderr, _ = self.execute_cli_runplan_cmd(self.management_node,
                                                        expect_positive=False)
            expect_err = ('InvalidRequestError    '
                          'Plan is currently running or stopping')
            self.assertTrue(self.is_text_in_list(expect_err, stderr),
                            "Expected error message '{0}' "
                            "not found in stderr: '{1}'".format(expect_err,
                                                                stderr))
            self.log('info',
                     'While stop_plan command is not finished, execute'
                     ' the stop_plan command.')
            # execute the stop_plan command while plan is Stopping and check
            # for errors
            _, stderr, _ = self.execute_cli_stopplan_cmd(self.management_node,
                                                         expect_positive=False)
            expect_err = 'InvalidRequestError    Plan not currently running'
            self.assertTrue(self.is_text_in_list(expect_err, stderr),
                            "Expected error message '{0}' "
                            "not found in stderr: '{1}'".format(expect_err,
                                                                stderr))
            self.release_lock(lock_path)
            self.log('info',
                     'After the plan status is changed to Stopped execute'
                     ' run_plan and create_plan commands.')
            # check plan state is finally set to Stopped
            self.assertTrue(self.wait_for_plan_state(self.management_node,
                                                     const.PLAN_STOPPED))
            # execute the run_plan command while plan is Stopped and check for
            # errors
            _, stderr, _ = self.execute_cli_runplan_cmd(self.management_node,
                                                        expect_positive=False)
            expect_err = 'InvalidRequestError    Plan not in initial state'
            self.assertTrue(self.is_text_in_list(expect_err, stderr),
                            "Expected error message '{0}' "
                            "not found in stderr: '{1}'".format(expect_err,
                                                                stderr))
            # execute the show_plan command
            stdout, _, _ = self.execute_cli_showplan_cmd(self.management_node)
            self.assertNotEqual([], stdout)
            # retrieve the tasks that were successful during the plan run
            successful_tasks = [line for line in stdout
                                if 'Success\t\t' in line]
            # execute the create_plan command again to overwrite the Stopped
            # plan
            self.execute_cli_createplan_cmd(self.management_node)
            self.assertTrue(self.wait_for_plan_state(self.management_node,
                                                     const.PLAN_NOT_RUNNING))
            # check that the successful tasks were not added to the plan a
            # second time
            stdout, _, _ = self.execute_cli_showplan_cmd(self.management_node)
            self.assertNotEqual([], stdout)
            if successful_tasks:
                for line in successful_tasks:
                    self.assertFalse(self.is_text_in_list(line, stdout),
                                     "Previously successful task '{0}' "
                                     "found in stdout: '{1}'".format(line,
                                                                     stdout))
        finally:
            self.release_lock(lock_path)

    def obsolete_04_p_remove_plan_state_invalid(self):
        """
        Obsolete -replaced by AT:
            ERIClitpcore/ats/Story_2240/test_04_p_remove_plan_state_invalid.at
        Description:
            While a plan is currently invalid, if a user executes the
            remove_plan command, the plan will be removed successfully.

        Pre-Requisites:
            1. A running litpd service
            2. An installed and configured cluster

        Actions:
            1. Execute the create command on an item in the model tree
            2. Execute the link command on a node in the model tree
            3. Execute the create_plan command
            4. Execute the update command an item in the model tree
            5. Check the plan state is Invalid
            6. Execute the remove_plan command
            7. Check the plan is removed

        Restore:
            1. Remove the created model item from the model tree
            2. Remove the model item link from the node
            3. Execute the create_plan command

        Results:
            Removing an invalid plan is allowed
        """

        # execute a set of common test methods required for the test
        self._exec_common_test_methods(self.package)
        # for each package item in the model, check if package is the test
        # package and if it is, execute an update command
        for url in self.find(self.management_node, '/', 'package'):
            stdout, _, _ = self.execute_cli_show_cmd(self.management_node, url,
                                                     '-j', load_json=False)
            package_name = self.cli.get_properties(stdout)['name']
            if package_name == self.package:
                self.execute_cli_update_cmd(self.management_node, url,
                                            'version=\'10\''
                                            ' release=\'39.el6\'')
        # check the plan state becomes Invalid
        self.assertTrue(self.wait_for_plan_state(self.management_node,
                                                 const.PLAN_INVALID))
        # execute the remove_plan command
        self.execute_cli_removeplan_cmd(self.management_node)
        # execute the show_plan command and check no plan exists
        _, stderr, _ = self.execute_cli_showplan_cmd(self.management_node,
                                                     expect_positive=False)
        expect_err = 'InvalidLocationError    Plan does not exist'
        self.assertTrue(self.is_text_in_list(expect_err, stderr),
                        'Expected error message \'{0}\' not found in stderr: '
                        '\'{1}\''.format(expect_err, stderr))

    def obsolete_05_p_create_plan_state_invalid(self):
        """
        Obsolete -replaced by AT:
            ERIClitpcore/ats/Story_2240/test_05_p_create_plan_state_invalid.at
        Description:
            While a plan is currently invalid, if a user executes the
            create_plan command, the plan will be recreated successfully and
            any new tasks added/updated must appear in the new plan.

        Pre-Requisites:
            1. A running litpd service
            2. An installed and configured cluster

        Actions:
            1. Execute the create command on an item in the model tree
            2. Execute the link command on a node in the model tree
            3. Execute the create_plan command
            4. Execute the update command an item in the model tree
            5. Check the plan state is Invalid
            6. Execute the create_plan command
            7. Check the plan is recreated in Initial state

        Restore:
            1. Remove the created model item from the model tree
            2. Remove the model item link from the node
            3. Execute the create_plan command

        Results:
            Recreating an invalid plan is allowed
        """

        # execute a set of common methods required for the test
        self._exec_common_test_methods(self.package)
        # for each package item under /software, if the package is the test
        # package then update the version
        for url in self.find(self.management_node, '/software', 'package'):
            stdout, _, _ = self.execute_cli_show_cmd(self.management_node, url,
                                                  '-j', load_json=False)
            package_name = self.cli.get_properties(stdout)['name']
            if package_name == self.package:
                self.execute_cli_update_cmd(self.management_node, url,
                                'version=\'10.0\' release=\'39.el6\'')
        # check plan state is now Invalid
        self.assertTrue(self.wait_for_plan_state(self.management_node,
                                                        const.PLAN_INVALID))
        # execute the create_plan command on an Invalid plan and check that the
        # plan is updated and set back to state Initial
        self.execute_cli_createplan_cmd(self.management_node)
        self.assertTrue(self.wait_for_plan_state(self.management_node,
                                                    const.PLAN_NOT_RUNNING))
        # for each test package again, execute the remove command
        for url in self.find(self.management_node, '/software', 'package'):
            stdout, _, _ = self.execute_cli_show_cmd(self.management_node, url,
                                                  '-j', load_json=False)
            package_name = self.cli.get_properties(stdout)['name']
            if package_name == self.package:
                self.execute_cli_remove_cmd(self.management_node, url)
        # check the plan state is again Invalid
        self.assertTrue(self.wait_for_plan_state(self.management_node,
                                                        const.PLAN_INVALID))

    def obsolete_06_n_no_run_stop_plan_state_invalid(self):
        """
        Obsolete -replaced by AT
            ERIClitpcore/ats/Story_2240/\
                test_06_n_no_run_stop_plan_state_invalid.at
        Description:
            While a plan is currently invalid, if a user executes the
            run_plan/stop_plan commands, an error must be given stating that a
            plan cannot be run/stopped while invalid.

        Pre-Requisites:
            1. A running litpd service
            2. An installed and configured cluster

        Actions:
            1. Execute the create command on an item in the model tree
            2. Execute the link command on a node in the model tree
            3. Execute the create_plan command
            4. Execute the update command an item in the model tree
            5. Check the plan state is Invalid
            6. Execute the run_plan command
            7. Check for error message
            8. Execute the create_plan command
            9. Check for error message

        Restore:
            1. Remove the created model item from the model tree
            2. Remove the model item link from the node
            3. Execute the create_plan command

        Results:
            Running/Stopping an invalid plan is not allowed
        """

        # execute a set of common methods required for the test
        self._exec_common_test_methods(self.package)
        # get the software-item url from the model
        url = self.find(self.management_node, '/software', 'software-item',
                        rtn_type_children=False)[0]
        # execute a create command in the model to set the plan to Invalid
        # state
        self.execute_cli_create_cmd(self.management_node,
                                    '{0}/model_change'.format(url),
                                    'package',
                                    'name=\'{0}\''.format(self.fail))
        # get the ms url
        ms_ = self.find(self.management_node, '/', 'ms')
        ms_ = ms_[0]
        # get the software-item url of ms
        url_ = self.find(self.management_node, ms_, 'software-item',
                        rtn_type_children=False)[0]
        # execute the inherit command
        self.execute_cli_inherit_cmd(
            self.management_node,
            '{0}/model_change'.format(url_),
            '{0}/model_change'.format(url)
        )
        # check that plan state is Invalid
        self.assertTrue(self.wait_for_plan_state(self.management_node,
                                                        const.PLAN_INVALID))
        # execute the run_plan command and check for errors
        _, stderr, _ = self.execute_cli_runplan_cmd(self.management_node,
                                                    expect_positive=False)
        expect_err = 'InvalidRequestError    Plan is invalid - model changed'
        self.assertTrue(self.is_text_in_list(expect_err, stderr),
        'Expected error message \'{0}\' not found in stderr: \'{1}\''.format(
                                                        expect_err, stderr))
        # execute the stop_plan command and check for errors
        _, stderr, _ = self.execute_cli_stopplan_cmd(self.management_node,
                                                    expect_positive=False)
        expect_err = 'InvalidRequestError    Plan not currently running'
        self.assertTrue(self.is_text_in_list(expect_err, stderr),
        'Expected error message \'{0}\' not found in stderr: \'{1}\''.format(
                                                        expect_err, stderr))

    def obsolete_07_p_remove_plan_state_initial(self):
        """
        Obsolete -replaced by AT:
            ERIClitpcore/ats/Story_2240/test_07_p_remove_plan_state_initial.at
        Description:
            While a plan is currently in Initial state, if a user executes the
            remove_plan command, the plan will be successfully removed.

        Pre-Requisites:
            1. A running litpd service
            2. An installed and configured cluster

        Actions:
            1. Execute the create command on an item in the model tree
            2. Execute the link command on a node in the model tree
            3. Execute the create_plan command
            4. Check the plan state is Initial
            5. Execute the remove_plan command
            6. Check plan is removed

        Restore:
            1. Remove the created model item from the model tree
            2. Remove the model item link from the node
            3. Execute the create_plan command

        Results:
            Removing an initial plan is allowed
        """

        # execute a set of common methods required for the test
        self._exec_common_test_methods(self.package)
        # check the plan state is set to Initial
        self.assertTrue(self.wait_for_plan_state(self.management_node,
                                                const.PLAN_NOT_RUNNING))
        # execute the remove_plan command
        self.execute_cli_removeplan_cmd(self.management_node)
        # execute the show_plan command and check there is no plan
        _, stderr, _ = self.execute_cli_showplan_cmd(self.management_node,
                                                    expect_positive=False)
        expect_err = 'InvalidLocationError    Plan does not exist'
        self.assertTrue(self.is_text_in_list(expect_err, stderr),
        'Expected error message \'{0}\' not found in stderr: \'{1}\''.format(
                                                        expect_err, stderr))

    def obsolete_08_p_create_plan_state_initial(self):
        """
        Obsolete -replaced by AT:
            ERIClitpcore/ats/Story_2240/test_08_p_create_plan_state_initial.at
        Description:
            While a plan is currently in Initial state, if a user executes the
            create_plan command, the plan will be successfully overwritten and
            recreated.

        Pre-Requisites:
            1. A running litpd service
            2. An installed and configured cluster

        Actions:
            1. Execute the create command on an item in the model tree
            2. Execute the link command on a node in the model tree
            3. Execute the create_plan command
            4. Check the plan state is Initial
            5. Execute the create_plan command
            6. Check plan is recreated and in Initial state

        Restore:
            1. Remove the created model item from the model tree
            2. Remove the model item link from the node
            3. Execute the create_plan command

        Results:
            Recreating the same initial plan is allowed
        """

        # execute a set of common methods required for the test
        self._exec_common_test_methods(self.package)
        # check the plan state is set to Initial
        self.assertTrue(self.wait_for_plan_state(self.management_node,
                                                const.PLAN_NOT_RUNNING))
        # execute the create_plan command and check that the plan is recreated
        self.execute_cli_createplan_cmd(self.management_node)
        # execute the show_plan command and check that plan exists
        stdout, _, _ = self.execute_cli_showplan_cmd(self.management_node)
        self.assertNotEqual([], stdout)

    def obsolete_09_n_no_stop_plan_state_initial(self):
        """
        Obsolete -replaced by AT:
            ERIClitpcore/ats/Story_2240/test_09_n_no_stop_plan_state_initial.at
        Description:
            While a plan is currently in Initial state, if a user executes the
            stop_plan command, an error must be given stating that a plan
            cannot be stopped if not running

        Pre-Requisites:
            1. A running litpd service
            2. An installed and configured cluster

        Actions:
            1. Execute the create command on an item in the model tree
            2. Execute the link command on a node in the model tree
            3. Execute the create_plan command
            4. Check the plan state is Initial
            5. Execute the stop_plan command
            6. Check for error message

        Restore:
            1. Remove the created model item from the model tree
            2. Remove the model item link from the node
            3. Execute the create_plan command

        Results:
            Stopping a plan in initial state is not allowed
        """

        # execute a set of common methods required for the test
        self._exec_common_test_methods(self.package)
        # check that plan state is Initial
        self.assertTrue(self.wait_for_plan_state(self.management_node,
                                                const.PLAN_NOT_RUNNING))
        # execute the stop_plan command and check for errors
        _, stderr, _ = self.execute_cli_stopplan_cmd(self.management_node,
                                                    expect_positive=False)
        expect_err = 'InvalidRequestError    Plan not currently running'
        self.assertTrue(self.is_text_in_list(expect_err, stderr),
        'Expected error message \'{0}\' not found in stderr: \'{1}\''.format(
                                                        expect_err, stderr))

    def obsolete_10_p_remove_plan_state_stopped(self):
        """
        Obsolete -replaced by AT:
            ERIClitpcore/ats/Story_2240/test_10_p_remove_plan_state_stopped.at
        Description:
            While a plan is currently in Stopped state, if a user executes the
            remove_plan command, the plan will be successfully removed.

        Pre-Requisites:
            1. A running litpd service
            2. An installed and configured cluster

        Actions:
            1. Execute the create command on an item in the model tree
            2. Execute the link command on a node in the model tree
            3. Execute the create_plan command
            4. Execute the run_plan command
            5. Execute the stop_plan command
            6. Wait for plan state to be Stopped
            7. Execute the remove_plan command
            8. Check the plan is removed

        Restore:
            1. Remove the created model item from the model tree
            2. Remove the model item link from the node
            3. Execute the create_plan command

        Results:
            Removing a stopped plan is allowed
        """

        # execute a set of common methods required for the test
        self._exec_common_test_methods(self.package)
        # execute the run_command
        self.execute_cli_runplan_cmd(self.management_node)
        self.assertTrue(self.wait_for_plan_state(self.management_node,
                                                const.PLAN_IN_PROGRESS))
        # execute the stop_plan command and wait for the Running plan to stop
        self.execute_cli_stopplan_cmd(self.management_node)
        self.assertTrue(self.wait_for_plan_state(self.management_node,
                                                const.PLAN_STOPPING))
        self.assertTrue(self.wait_for_plan_state(self.management_node,
                                                const.PLAN_STOPPED))
        # execute the remove_plan command
        self.execute_cli_removeplan_cmd(self.management_node)
        # execute the show_plan command and check no plan exists
        _, stderr, _ = self.execute_cli_showplan_cmd(self.management_node,
                                                    expect_positive=False)
        expect_err = 'InvalidLocationError    Plan does not exist'
        self.assertTrue(self.is_text_in_list(expect_err, stderr),
        'Expected error message \'{0}\' not found in stderr: \'{1}\''.format(
                                                        expect_err, stderr))

    @attr('all', 'revert')
    def obsolete_11_p_create_plan_state_stopped(self):
        """
        Description:
            While a plan is currently in Stopped state, if a user executes the
            create_plan command, the plan will be successfully recreated,
            omitting any tasks that were successful before the plan was
            stopped *as long as their model items are in Applied state.*

        Pre-Requisites:
            1. A running litpd service

        Actions:
            1. Execute the create command on an item in the model tree
            2. Execute the create_plan command
            3. Execute the run_plan command
            4. Execute the stop_plan command
            5. Wait for plan state to be Stopped
            6. Execute the create_plan command
            7. Check the plan is recreated without any previously successful
               tasks

        Restore:
            1. Remove the created model item from the model tree
            2. Execute the create_plan command

        Results:
            Recreating a stopped plan is allowed with any tasks that were not
            previously successful
        """
        self._install_item_extension()

        lock_item = "story2240_tc11_lock"
        after_item = "story2240_tc11_after"
        before_item = "story2240_tc11_before"
        lock_path = "/tmp/" + lock_item
        try:
            # create config items
            self.create_ms_config_item(lock_item)
            self.create_ms_config_item(before_item)
            self.create_ms_config_item(after_item)
            # execute the create_plan command
            self.execute_cli_createplan_cmd(self.management_node)

            # create lock file that's checked by callback task
            self.create_lock(lock_path)

            # execute the run_plan command
            self.execute_cli_runplan_cmd(self.management_node)
            self.assertTrue(self.wait_for_plan_state(self.management_node,
                                                     const.PLAN_IN_PROGRESS))
            # execute the stop_plan command and wait for the Running plan to be
            # Stopped
            self.execute_cli_stopplan_cmd(self.management_node)
            self.assertTrue(self.wait_for_plan_state(self.management_node,
                                                     const.PLAN_STOPPING))

            self.release_lock(lock_path)

            self.assertTrue(self.wait_for_plan_state(self.management_node,
                                                     const.PLAN_STOPPED))
            # execute the show_plan command
            stdout, _, _ = self.execute_cli_showplan_cmd(self.management_node)
            self.assertNotEqual([], stdout)
            # retrieve the tasks that were successful during the plan run
            successful_tasks = [line for line in stdout
                                if 'Success\t\t' in line]
            # execute the create_plan command again to overwrite the Stopped
            # plan
            self.execute_cli_createplan_cmd(self.management_node)
            self.assertTrue(self.wait_for_plan_state(self.management_node,
                                                     const.PLAN_NOT_RUNNING))
            # check that the successful tasks were not added to the plan a
            # second time
            stdout, _, _ = self.execute_cli_showplan_cmd(self.management_node)
            self.assertNotEqual([], stdout)
            if successful_tasks:
                for line in successful_tasks:
                    self.assertFalse(self.is_text_in_list(line, stdout),
                                     "Previously successful task '{0}' "
                                     "found in stdout: '{1}'".format(line,
                                                                     stdout))
        finally:
            self.release_lock(lock_path)

    def obsolete_12_n_no_stop_plan_state_stopped(self):
        """
        Obsolete -replaced by AT:
            ERIClitpcore/ats/Story_2240/test_12_n_no_stop_plan_state_stopped.at
        Description:
            While a plan is currently in Stopped state, if a user executes the
            stop_plan command, an error message must be given stating that a
            stopped plan cannot be stopped.

        Pre-Requisites:
            1. A running litpd service
            2. An installed and configured cluster

        Actions:
            1. Execute the create command on an item in the model tree
            2. Execute the link command on a node in the model tree
            3. Execute the create_plan command
            4. Execute the run_plan command
            5. Execute the stop_plan command
            6. Wait for plan state to be Stopped
            7. Execute the stop_plan command
            8. Check for error message

        Restore:
            1. Remove the created model item from the model tree
            2. Remove the model item link from the node
            3. Execute the create_plan command

        Results:
            Stopping an already stopped plan is not allowed
        """

        # execute a set of common methods required for the test
        self._exec_common_test_methods(self.package)
        # execute the run_plan command
        self.execute_cli_runplan_cmd(self.management_node)
        self.assertTrue(self.wait_for_plan_state(self.management_node,
                                                const.PLAN_IN_PROGRESS))
        # execute the stop_plan command and wait for the Running plan to be
        # Stopped
        self.execute_cli_stopplan_cmd(self.management_node)
        self.assertTrue(self.wait_for_plan_state(self.management_node,
                                                const.PLAN_STOPPING))
        self.assertTrue(self.wait_for_plan_state(self.management_node,
                                                const.PLAN_STOPPED))
        # execute the stop_plan command again and check for errors
        _, stderr, _ = self.execute_cli_stopplan_cmd(self.management_node,
                                                    expect_positive=False)
        expect_err = 'InvalidRequestError    Plan not currently running'
        self.assertTrue(self.is_text_in_list(expect_err, stderr),
        'Expected error message \'{0}\' not in stderr: \'{1}\''.format(
                                                        expect_err, stderr))

    def obsolete_13_p_remove_plan_state_failed(self):
        """
        Obsolete -replaced by AT:
            ERIClitpcore/ats/Story_2240/test_13_p_remove_plan_state_failed.at
        Description:
            While a plan is currently in Failed state, if a user executes the
            remove_plan command, the plan will be successfully removed.

        Pre-Requisites:
            1. A running litpd service
            2. An installed and configured cluster

        Actions:
            1. Execute the create command on an item in the model tree
            2. Execute the link command on a node in the model tree
            3. Execute the create_plan command
            4. Execute the run_plan command
            5. Wait for plan state Failed
            6. Execute the remove_plan command
            7. Check plan is removed

        Restore:
            1. Remove the created model item from the model tree
            2. Remove the model item link from the node
            3. Execute the create_plan command

        Results:
            Removing a failed plan is allowed
        """

        # execute a set of common methods required for the test
        self._exec_common_test_methods(self.fail)
        # execute the run_plan command and wait for the plan to Fail
        self.execute_cli_runplan_cmd(self.management_node)
        self.assertTrue(self.wait_for_plan_state(self.management_node,
                                                const.PLAN_IN_PROGRESS))
        self.assertTrue(self.wait_for_plan_state(self.management_node,
                                                const.PLAN_FAILED))
        # execute the remove_plan command
        self.execute_cli_removeplan_cmd(self.management_node)
        # check that no plan exists
        _, stderr, _ = self.execute_cli_showplan_cmd(self.management_node,
                                                    expect_positive=False)
        expect_err = 'InvalidLocationError    Plan does not exist'
        self.assertTrue(self.is_text_in_list(expect_err, stderr),
        'Expected error message \'{0}\' not in stderr: \'{1}\''.format(
                                                        expect_err, stderr))

    @attr('all', 'revert', 'story2240', 'story2240_tc14')
    def test_14_p_create_plan_state_failed(self):
        """
        @tms_id: litpcds_2240_tc14
        @tms_requirements_id: LITPCDS-2240
        @tms_title: Verify when plan fails there, the successful tasks are not
             added to the next plan.
        @tms_description:
            While a plan is currently in Failed state, if a user executes the
            create_plan command, the plan will be successfully recreated,
            omitting any tasks that were successful before the plan was
            stopped *as long as their model items are in Applied state.* Failed
            tasks and Initial tasks will be back in the new plan.
        @tms_test_steps:
            @step: Execute the create command on an item in the model tree,
                create and run plan.
            @result: The plan is failing with several successful tasks.
            @step: Execute the create_plan command, and check the plan.
            @result: The plan is recreated without any previously successful
               tasks.
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        self._install_item_extension()

        lock_item = "story2240_tc14_lock"
        fail_item = "story2240_tc14_fail"
        lock_path = "/tmp/" + lock_item
        try:
            self.log('info',
                     'Execute the create command on an item in the model tree,'
                     ' create and run plan.')
            # create config items
            item1 = self.create_ms_config_item(lock_item)
            item2 = self.create_ms_config_item(fail_item)
            # execute the create_plan command
            self.execute_cli_createplan_cmd(self.management_node)

            self.create_lock(lock_path)

            # execute the run_plan command
            self.execute_cli_runplan_cmd(self.management_node)

            self.assertTrue(self.wait_for_plan_state(self.management_node,
                                                     const.PLAN_IN_PROGRESS))
            self.release_lock(lock_path)
            self.assertTrue(self.wait_for_plan_state(self.management_node,
                                                     const.PLAN_FAILED))
            # execute the show_plan command
            stdout, _, _ = self.execute_cli_showplan_cmd(self.management_node)
            # get the failed tasks from the plan
            failed_tasks = [line.split('Failed\t\t')[1] for line in stdout
                            if 'Failed\t\t' in line]
            self.assertNotEqual([], failed_tasks)
            # Check states of model items after plan failure
            item1_state = self.execute_show_data_cmd(
                self.management_node, item1, "state")
            self.assertEqual("Applied", item1_state)
            item2_state = self.execute_show_data_cmd(
                self.management_node, item2, "state")
            self.assertEqual(
                "Initial (deployment of properties indeterminable)",
                item2_state)
            self.log('info',
                     'Execute the create_plan command, and check the plan.')
            # execute the create_plan command
            self.execute_cli_createplan_cmd(self.management_node)
            self.assertTrue(self.wait_for_plan_state(self.management_node,
                                                     const.PLAN_NOT_RUNNING))
            # check that the failed tasks exist in the recreated plan
            stdout, _, _ = self.execute_cli_showplan_cmd(self.management_node)
            self.assertNotEqual([], stdout)
            for line in failed_tasks:
                self.assertTrue(self.is_text_in_list(line, stdout),
                                'Previously failed task \'{0}\' not found in '
                                'new plan stdout: \'{1}\''.format(line,
                                                                  stdout))
        finally:
            self.release_lock(lock_path)

    def obsolete_15_n_no_stop_plan_state_failed(self):
        """
        Obsolete -replaced by AT:
            ERIClitpcore/ats/Story_2240/test_15_n_no_stop_plan_state_failed.at
        Description:
            While a plan is currently in Failed state, if a user executes the
            stop_plan command, an error message must be given stating that a
            failed plan cannot be stopped.

        Pre-Requisites:
            1. A running litpd service
            2. An installed and configured cluster

        Actions:
            1. Execute the create command on an item in the model tree
            2. Execute the link command on a node in the model tree
            3. Execute the create_plan command
            4. Execute the run_plan command
            5. Wait for plan state Failed
            6. Execute the stop_plan command
            7. Check for error message
            8. Execute the run_plan command
            9. Check for error message

        Restore:
            1. Remove the created model item from the model tree
            2. Remove the model item link from the node
            3. Execute the create_plan command

        Results:
            Stopping a failed plan is not allowed
        """

        # execute a set of common methods required for the test
        self._exec_common_test_methods(self.fail)
        # execute the run_plan command and wait for the plan to Fail
        self.execute_cli_runplan_cmd(self.management_node)
        self.assertTrue(self.wait_for_plan_state(self.management_node,
                                                const.PLAN_IN_PROGRESS))
        self.assertTrue(self.wait_for_plan_state(self.management_node,
                                                const.PLAN_FAILED))
        # execute the stop_plan command and check for errors
        _, stderr, _ = self.execute_cli_stopplan_cmd(self.management_node,
                                                    expect_positive=False)
        expect_err = 'InvalidRequestError    Plan not currently running'
        self.assertTrue(self.is_text_in_list(expect_err, stderr),
        'Expected error message \'{0}\' not found in stderr: \'{1}\''.format(
                                                        expect_err, stderr))
        # execute the run_plan command and check for errors
        _, stderr, _ = self.execute_cli_runplan_cmd(self.management_node,
                                                    expect_positive=False)
        expect_err = 'InvalidRequestError    Plan not in initial state'
        self.assertTrue(self.is_text_in_list(expect_err, stderr),
        'Expected error message \'{0}\' not found in stderr: \'{1}\''.format(
                                                        expect_err, stderr))

    def obsolete_16_p_remove_plan_state_success(self):
        """
        Obsolete -replaced by AT:
            ERIClitpcore/ats/Story_2240/test_16_p_remove_plan_state_success.at
        Description:
            While a plan is currently in Successful state, if a user executes
            the remove_plan command, the plan will be successfully removed.

        Pre-Requisites:
            1. A running litpd service
            2. An installed and configured cluster

        Actions:
            1. Execute the create command on an item in the model tree
            2. Execute the link command on a node in the model tree
            3. Execute the create_plan command
            4. Execute the run_plan command
            5. Wait for plan state Successful
            6, Execute the remove_plan command
            7. Check plan is removed

        Restore:
            1. Remove the created model item from the model tree
            2. Remove the model item link from the node
            3. Execute the create_plan command

        Results:
            Removing a successful plan is allowed
        """

        # execute a set of common methods required for the test
        self._exec_common_test_methods(self.package)
        # execute the run_plan command and wait for plan Success
        self.execute_cli_runplan_cmd(self.management_node)
        self.assertTrue(self.wait_for_plan_state(self.management_node,
                                                const.PLAN_IN_PROGRESS))
        self.assertTrue(self.wait_for_plan_state(self.management_node,
                                                const.PLAN_COMPLETE))
        # execute the remove_plan command
        self.execute_cli_removeplan_cmd(self.management_node)
        # execute the show_plan command and check that no plan exists
        _, stderr, _ = self.execute_cli_showplan_cmd(self.management_node,
                                                    expect_positive=False)
        expect_err = 'InvalidLocationError    Plan does not exist'
        self.assertTrue(self.is_text_in_list(expect_err, stderr),
        'Expected error message \'{0}\' not found in stderr: \'{1}\''.format(
                                                        expect_err, stderr))

    def obsolete_17_n_create_plan_state_success_no_model_change(self):
        """
        Obsolete -replaced by AT:
            ERIClitpcore/ats/Story_2240/\
                test_17_n_create_plan_state_success_no_model_change.at
        Description:
            While a plan is currently in Successful state, if a user executes
            the create_plan command without having made any new changes to the
            model, an error must be given stating there is not plan required to
            be created.

        Pre-Requisites:
            1. A running litpd service
            2. An installed and configured cluster

        Actions:
            1. Execute the create command on an item in the model tree
            2. Execute the link command on a node in the model tree
            3. Execute the create_plan command
            4. Execute the run_plan command
            5. Wait for plan state Successful
            6. Execute the create_plan command
            7. Check for error message

        Restore:
            1. Remove the created model item from the model tree
            2. Remove the model item link from the node
            3. Execute the create_plan command

        Results:
            Recreating a successful plan, without any further model changes, is
            not allowed
        """

        # execute a set of common methods required for the test
        self._exec_common_test_methods(self.package)
        # execute the run_plan command and wait for plan Success
        self.execute_cli_runplan_cmd(self.management_node)
        self.assertTrue(self.wait_for_plan_state(self.management_node,
                                                const.PLAN_IN_PROGRESS))
        self.assertTrue(self.wait_for_plan_state(self.management_node,
                                                const.PLAN_COMPLETE))
        # execute the create_plan command and check for error
        _, stderr, _ = self.execute_cli_createplan_cmd(self.management_node,
                                                      expect_positive=False)
        expect_err = 'DoNothingPlanError    Create plan failed: no tasks '\
                     'were generated'
        self.assertTrue(self.is_text_in_list(expect_err, stderr),
        'Expected error message \'{0}\' not found in stderr: \'{1}\''.format(
                                                        expect_err, stderr))
        # execute the run_plan command and check for errors
        _, stderr, _ = self.execute_cli_runplan_cmd(self.management_node,
                                                    expect_positive=False)
        expect_err = 'InvalidLocationError    Plan does not exist'
        self.assertTrue(self.is_text_in_list(expect_err, stderr),
        'Expected error message \'{0}\' not found in stderr: \'{1}\''.format(
                                                        expect_err, stderr))

    def obsolete_18_p_create_plan_state_success(self):
        """
        Obsolete - replaced by AT:
            ERIClitpcore/ats/Story_2240/test_18_p_create_plan_state_success.at
        Description:
            While a plan is currently in Successful state, if a user executes
            the create_plan command after having made new changes to the model,
            the plan will be successfully created.

        Pre-Requisites:
            1. A running litpd service
            2. An installed and configured cluster

        Actions:
            1. Execute the create command on an item in the model tree
            2. Execute the link command on a node in the model tree
            3. Execute the create_plan command
            4. Execute the run_plan command
            5. Wait for plan state Successful
            6. Execute the create_plan command
            7. Execute the show_plan command
            8. Check plan exists

        Restore:
            1. Remove the created model item from the model tree
            2. Remove the model item link from the node
            3. Execute the create_plan command

        Results:
            Recreating a successful plan, after model changes, is allowed
        """

        # execute a set of commone methods required for the test
        self._exec_common_test_methods(self.package)
        # execute the run_plan command and wait for Plan Success
        self.execute_cli_runplan_cmd(self.management_node)
        self.assertTrue(self.wait_for_plan_state(self.management_node,
                                                const.PLAN_IN_PROGRESS))
        self.assertTrue(self.wait_for_plan_state(self.management_node,
                                                const.PLAN_COMPLETE))

        # get the software-item url
        url = self.find(self.management_node, '/software', 'software-item',
                        rtn_type_children=False)[0]
        self.execute_cli_create_cmd(self.management_node,
                                    '{0}/model_change'.format(url),
                                    'package',
                                    'name=\'{0}\''.format(self.fail))
        # get the ms url
        ms_ = self.find(self.management_node, '/', 'ms')
        ms_ = ms_[0]
        # get the software-item url for ms
        url_ = self.find(self.management_node, ms_, 'software-item',
                        rtn_type_children=False)[0]
        # execute the inherit command
        self.execute_cli_inherit_cmd(
            self.management_node,
            '{0}/model_change'.format(url_),
            '{0}/model_change'.format(url)
        )
        # execute the create_plan command and check that a new Initial plan
        # exists
        self.execute_cli_createplan_cmd(self.management_node)
        self.assertTrue(self.wait_for_plan_state(self.management_node,
                                                const.PLAN_NOT_RUNNING))
        # execute the show_plan command and check that the previous successful
        # package is not part of the new plan
        stdout, _, _ = self.execute_cli_showplan_cmd(self.management_node)
        self.assertFalse(self.is_text_in_list(self.package, stdout),
        'Successful task for installing package \'{0}\' reintroduced into new'\
        ' plan in stdout: \'{1}\''.format(self.package, stdout))
        self.assertTrue(self.is_text_in_list(self.fail, stdout),
        'Task for installing package \'{0}\' not found in stdout: \'{1}\''.\
                                                    format(self.fail, stdout))

    def obsolete_19_n_no_stop_plan_state_success(self):
        """
        Obsolete - replaced by AT:
            ERIClitpcore/ats/Story_2240/test_19_n_no_stop_plan_state_success.at
        Description:
            While a plan is currently in Successful state, if a user executes
            the stop_plan command, an error must be given stating that a
            successful plan cannot be stopped.

        Pre-Requisites:
            1. A running litpd service
            2. An installed and configured cluster

        Actions:
            1. Execute the create command on an item in the model tree
            2. Execute the link command on a node in the model tree
            3. Execute the create_plan command
            4. Execute the run_plan command
            5. Wait for plan state Successful
            6. Execute the stop_plan command
            7. Check for error message

        Restore:
            1. Remove the created model item from the model tree
            2. Remove the model item link from the node
            3. Execute the create_plan command

        Results:
            Stopping a successfully complete plan is not allowed
        """

        # execute a set of common methods for test
        self._exec_common_test_methods(self.package)
        # execute the run_plan command and wait for plan Success
        self.execute_cli_runplan_cmd(self.management_node)
        self.assertTrue(self.wait_for_plan_state(self.management_node,
                                                const.PLAN_IN_PROGRESS))
        self.assertTrue(self.wait_for_plan_state(self.management_node,
                                                const.PLAN_COMPLETE))
        # execute the stop_plan command and check for errors
        _, stderr, _ = self.execute_cli_stopplan_cmd(self.management_node,
                                                    expect_positive=False)
        expect_err = 'InvalidRequestError    Plan not currently running'
        self.assertTrue(self.is_text_in_list(expect_err, stderr),
        'Expected error message \'{0}\' not found in \'{1}\''.format(
                                                        expect_err, stderr))

    @attr('all', 'revert', 'story2240', 'story2240_tc20')
    def test_20_p_load_xml_item_plan_state_invalid(self):
        """
        @tms_id: litpcds_2240_tc20
        @tms_requirements_id: LITPCDS-2240
        @tms_title: Verify the plan must be Invalid and the linked item must
             be in state Updated after a successful XML load
        @tms_description:
            After a successful plan execution, all items in the model are set
            to Applied. Exporting those items and then removing will produce a
            new plan. If those items are then loaded back in, they are set to
            Updated and as such, should cause the plan to become Invalid.
            Note: TC21 merged into this test load/load --merge for brevity and
             made obsolete.
        @tms_test_steps:
            @step: Execute the create command on an item in the model tree.
            @result: New test item is created.
            @step: Execute the export command to XML file for the item
                 from the previous step, execute the remove command for that
                  item, and run create_plan command
            @result: The previously created item is removed and backup XML
                is available.
            @step: Execute load command for the exported XML file.
            @result: The item is loaded back.
            @step: Execute create plan, create lock file in ms and run the
                 plan, and remove the lock while plan is running.
            @result: The plan succeed.
            @step: Execute the export command to XML file for previously
                 installed item, execute the remove command for that item,
                 and run create_plan command
            @result: The previously created item is removed and backup XML
                is available.
            @step: Execute load/load --merge commands for
                 the exported XML file.
            @result: The items are loaded back with state Updated,
                 and plan status is "Invalid".
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        self._install_item_extension()

        lock_item = "story2240_tc20_lock"
        lock_path = "/tmp/" + lock_item
        try:
            self.log('info',
                     'Execute the create command on an item '
                     'in the model tree.')
            # create config items
            lock_item_path = self.create_ms_config_item(lock_item)
            filepath = '/tmp/{0}.xml'.format(lock_item)
            self.log('info',
                     'Execute the export command to XML file for all items,'
                     'execute the remove command for all items, '
                     'and run create_plan command')
            self.execute_cli_export_cmd(self.management_node, lock_item_path,
                                        filepath)
            self.execute_cli_remove_cmd(self.management_node, lock_item_path)
            # get the ms url
            ms_ = self.find(self.management_node, '/', 'ms')[0]
            configs_path = self.find(self.management_node, ms_,
                                     'node-config',
                                     rtn_type_children=False)[0]
            self.log('info',
                     'Execute load command for the exported XML file.')
            self.execute_cli_load_cmd(self.management_node, configs_path,
                                      filepath)
            self.log('info',
                     'Execute create plan, create lock file in ms and run the'
                     ' plan, and remove the lock while plan is running.')
            # execute the create_plan command
            self.execute_cli_createplan_cmd(self.management_node)

            self.create_lock(lock_path)
            # execute the run_plan command and wait for plan Success
            self.execute_cli_runplan_cmd(self.management_node)
            self.assertTrue(self.wait_for_plan_state(self.management_node,
                                                     const.PLAN_IN_PROGRESS))
            self.release_lock(lock_path)
            self.assertTrue(self.wait_for_plan_state(self.management_node,
                                                     const.PLAN_COMPLETE))
            self.log('info',
                     'Execute the export command to XML file for all items,'
                     'execute the remove command for the item created in step '
                     ' 1, and run create_plan command')
            # for each package link to the nodes, if the package is the test
            # package export the link to an XML file and then remove it from
            # the model
            filepath = '/tmp/{0}.xml'.format(lock_item)
            self.execute_cli_export_cmd(self.management_node, lock_item_path,
                                        filepath)
            self.execute_cli_remove_cmd(self.management_node, lock_item_path)
            # execute the create_plan command
            self.execute_cli_createplan_cmd(self.management_node)
            self.assertTrue(self.wait_for_plan_state(self.management_node,
                                                     const.PLAN_NOT_RUNNING))
            self.log('info',
                     'Execute load command for the exported XML file')
            # load the exported xml link back
            self.execute_cli_load_cmd(self.management_node, configs_path,
                                      filepath, expect_positive=False)
            # execute load --merge
            self.execute_cli_load_cmd(self.management_node, configs_path,
                                      filepath, '--merge')
            # check the plan state is Invalid
            self.assertTrue(self.wait_for_plan_state(self.management_node,
                                                     const.PLAN_INVALID))
        finally:
            self.release_lock(lock_path)
            self.execute_cli_remove_cmd(self.management_node, lock_item_path)
            # execute the create_plan command
            self.execute_cli_createplan_cmd(self.management_node)
            self.execute_cli_runplan_cmd(self.management_node)
            self.assertTrue(self.wait_for_plan_state(self.management_node,
                                                     const.PLAN_COMPLETE))

    @attr('all', 'revert')
    def obsolete_21_p_load_xml_merge_item_plan_state_invalid(self):
        """
        Note: Merged into TC20
        Description:
            After a successful plan execution, all items in the model are set
            to Applied. Exporting those items and then removing will produce a
            new plan. If those items are then loaded back in, they are set to
            Updated and as such, should cause the plan to become Invalid

        Pre-Requisites:
            1. A running litpd service
            2. An installed and configured cluster

        Actions:
            1.  Execute the create command on an item in the model tree
            2.  Execute the create_plan command
            3.  Execute the run_plan command
            4.  Wait for plan state Successful
            5.  Execute the export command to XML file for all items
            6.  Execute the remove command for all items
            7.  Check the create_plan command
            8.  Execute the load command for all exported XML files with
                --merge
            10. Check the items loaded back in with state Updated
            11. Check plan state is now Invalid

        Restore:
            1. Remove the created model item from the model tree
            2. Remove the model item link from the node
            3. Execute the create_plan command

        Results:
            The plan must be Invalid and the linked item must be in state
            Updated after a successful XML load with --merge
        """
        self._install_item_extension()

        lock_item = "story2240_tc21_lock"
        lock_path = "/tmp/" + lock_item
        try:
            # create config items
            lock_item_path = self.create_ms_config_item(lock_item)

            self.create_lock(lock_path)

            # execute the create_plan command
            self.execute_cli_createplan_cmd(self.management_node)

            # execute the run_plan command and wait for plan completion
            self.execute_cli_runplan_cmd(self.management_node)
            self.assertTrue(self.wait_for_plan_state(self.management_node,
                                                     const.PLAN_IN_PROGRESS))
            self.release_lock(lock_path)
            self.assertTrue(self.wait_for_plan_state(self.management_node,
                                                     const.PLAN_COMPLETE))
            # export the item to an XML file then execute the remove command on
            # it
            filepath = '/tmp/{0}.xml'.format(lock_item)
            self.execute_cli_export_cmd(self.management_node, lock_item_path,
                                        filepath)
            self.execute_cli_remove_cmd(self.management_node, lock_item_path)

            # execute the create_plan command and check plan is in Inital state
            self.execute_cli_createplan_cmd(self.management_node)
            self.assertTrue(self.wait_for_plan_state(self.management_node,
                                                     const.PLAN_NOT_RUNNING))
            # execute an update via the exported XML file and check the state
            # after the load for the item is now Updated
            ms_ = self.find(self.management_node, '/', 'ms')[0]
            configs_path = self.find(self.management_node, ms_,
                                        'node-config',
                                        rtn_type_children=False)[0]
            self.execute_cli_load_cmd(self.management_node, configs_path,
                                      filepath, '--merge')
            # check the plan state is Invalid
            self.assertTrue(self.wait_for_plan_state(self.management_node,
                                                     const.PLAN_INVALID))
        finally:
            self.release_lock(lock_path)
            self.execute_cli_remove_cmd(self.management_node, lock_item_path)
            # execute the create_plan command
            self.execute_cli_createplan_cmd(self.management_node)
            self.execute_cli_runplan_cmd(self.management_node)
            self.assertTrue(self.wait_for_plan_state(self.management_node,
                                                     const.PLAN_COMPLETE))

    @attr('all', 'revert', 'story2240', 'story2240_tc22')
    def test_22_p_rest_plan_invalid(self):
        """
        @tms_id: litpcds_2240_tc22
        @tms_requirements_id: LITPCDS-2240
        @tms_title: Verify the plan must be Invalid and the inherited item must
             be in state "Updated" after a successful REST PUT request
        @tms_description:
            After a successful plan execution, all items in the model are set
            to Applied. Executing a REST DELETE request on those items will
            produce a new plan. If those items are then updated using a REST
            PUT, they are set to Updated and as such, will cause the plan to
            become Invalid
        @tms_test_steps:
            @step: Execute the create command on an items in the model tree,
                execute the create_plan and run_plan commands.
            @result: New test items are created and the plan is
                 executed successfully.
            @step: Execute a REST DELETE request on the items and
                 execute the create_plan command.
            @result: The items are marked for deletion in the plan.
            @step: Execute a REST PUT command on the items and check
                 plan status
            @result: The items have state Updated and the plan status is
                 "Invalid".
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        self._install_item_extension()

        lock_item = "story2240_tc22_lock"
        lock_path = "/tmp/" + lock_item
        after_item = "story2240_tc22_after"
        self.log('info',
                 'Execute the create command on an items in the model tree,'
                 'execute the create_plan and run_plan commands.')
        lock_item_path = self.create_ms_config_item(lock_item)
        after_item_path = self.create_ms_config_item(after_item)

        try:
            # execute the create_plan command
            self.execute_cli_createplan_cmd(self.management_node)
            # execute the run_plan command and wait for plan Success
            self.create_lock(lock_path)
            self.execute_cli_runplan_cmd(self.management_node)
            self.assertTrue(self.wait_for_plan_state(self.management_node,
                                                     const.PLAN_IN_PROGRESS))
            self.release_lock(lock_path)
            self.assertTrue(self.wait_for_plan_state(self.management_node,
                                                     const.PLAN_COMPLETE))
            self.log('info',
                     'Execute a REST DELETE request on the items and'
                     ' execute the create_plan command.')
            # if the package is the test package,
            # then delete the item using a REST DELETE request
            for url in [lock_item_path, after_item_path]:
                stdout, _, _ = self.execute_cli_show_cmd(self.management_node,
                                                         url, '-j',
                                                         load_json=False)
                stdout, stderr, status = self.rest.delete(url)
                self.assertEqual(200, status)
                self.assertEqual('', stderr)
                self.assertNotEqual('', stdout)

            # execute the create_plan command and check plan is set to state
            # Initial
            self.execute_cli_createplan_cmd(self.management_node)
            self.assertTrue(self.wait_for_plan_state(self.management_node,
                                                     const.PLAN_NOT_RUNNING))
            self.log('info',
                     'Execute a REST PUT command on the items and check'
                     ' plan status')
            # update each test item using a REST PUT request and check
            # the state of the item is now Updated
            for url in [lock_item_path, after_item_path]:
                stdout, _, _ = self.execute_cli_show_cmd(self.management_node,
                                                         url, '-j',
                                                         load_json=False)
                data = '{"properties":{"name":"new_val"}}'
                stdout, stderr, status = self.rest.put(url,
                                                       self.rest.HEADER_JSON,
                                                       data)
                self.assertEqual(200, status)
                self.assertEqual('', stderr)
                self.assertNotEqual('', stdout)
                stdout, stderr, rcode = self.run_command(
                    self.management_node,
                    self.cli.get_show_data_value_cmd(url, 'state'))
                self.assertEqual(0, rcode)
                self.assertEqual([], stderr)
                self.assertNotEqual([], stdout)
                self.assertTrue(self.is_text_in_list('Updated', stdout),
                                "Expected state 'Updated' not found "
                                "in stdout: '{0}'".format(stdout))

            # check the plan is now Invalid
            self.assertTrue(self.wait_for_plan_state(self.management_node,
                                                     const.PLAN_INVALID))
        finally:
            self.release_lock(lock_path)

    @attr('all', 'revert', 'story2240', 'story2240_tc23', 'story12781')
    def test_23_p_stop_plan_state_success_final_phase(self):
        """
        @tms_id: litpcds_2240_tc23
        @tms_requirements_id: LITPCDS-2240, LITPCDS-12781, LITPCDS-184
        @tms_title: Verify after successful execution of the phase, the plan
             must be in Successful state and the items will be set to Applied
              state in the model
        @tms_description:
            Tests for stopping a plan during its final phase.
            Tests for configuration tasks with persisted flag set to False.
            LITPCDS-3499 - When a plan is executing its final phase, if the
            stop_plan command is executed then, after the successful phase
            completion, the plan must be in state Successful and the items must
            be set to Applied state in the model.

            LITPCDS-12781 As a LITP developer I want the ability to set whether
            a ConfigTask is persisted or not
            Added a config task with persist flag set to False
            and validate that the task reappears in the plan after the plan
            is stopped and recreated.
        @tms_test_steps:
            @step: Execute the create command on items in the model tree,
                execute the create_plan and run_plan commands.
            @result: New test items are created and the plan has
                 status "Running".
            @step: Wait for plan state Running on final Phase and execute the
                 stop_plan command
            @result: The plan state is Successful.
            @step: For each package item in the model, if the package is the
                 test package, check the state.
            @result: The state is set to Applied.
            @step: Execute the create_plan command and show plan.
            @result: A config task with persist flag set to False is in plan.
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        self._install_item_extension()

        lock_item = "story2240_tc23_lock"
        lock_path = "/tmp/" + lock_item
        before_item = "story2240_tc23_before"
        non_persist_item = "story2240_tc23_persist"
        self.log('info',
                 'Execute the create command on an items in the model tree,'
                 ' execute the create_plan and run_plan commands.')
        lock_item_path = self.create_ms_config_item(lock_item)
        before_item_path = self.create_ms_config_item(before_item)
        self.create_ms_config_item(non_persist_item)

        try:
            self.execute_cli_createplan_cmd(self.management_node)
            # execute the run_plan command and wait for plan Success
            self.create_lock(lock_path)

            # execute the show_plan command and get the last phase in the plan
            stdout, _, _ = self.execute_cli_showplan_cmd(self.management_node)
            final_plan_phase = [stdout.index(line) for line in stdout
                                if 'Phase' in line][-1]
            # execute the run_plan command and check the plan state is Running
            self.execute_cli_runplan_cmd(self.management_node)
            self.assertTrue(self.wait_for_plan_state(self.management_node,
                                                     const.PLAN_IN_PROGRESS))

            # while the plan state is Running, check if the running tasks are
            # those of the last phase in the plan and, if they are,
            # then execute the stop_plan command then check the plan state is
            # Successful
            self.assertTrue(self.wait_for_task_state(
                    self.management_node,
                    'Polling task for {0}'.format(lock_path),
                    const.PLAN_TASKS_RUNNING,
                    ignore_variables=False,
                    timeout_mins=3))
            stdout, _, _ = self.execute_cli_showplan_cmd(self.management_node)
            running_tasks = [stdout[indx] for indx
                             in xrange(final_plan_phase, len(stdout))
                             if 'Running' in stdout[indx] and
                             '/' in stdout[indx]]
            self.log('info',
                     'Wait for plan state Running on final Phase and execute'
                     ' the stop_plan command')
            if running_tasks:
                self.execute_cli_stopplan_cmd(self.management_node)
                self.assertEqual(
                    const.PLAN_STOPPING,
                    self.get_current_plan_state(self.management_node))
                self.release_lock(lock_path)

            self.assertTrue(self.wait_for_plan_state(self.management_node,
                                                     const.PLAN_COMPLETE))
            self.log('info',
                     'For each package item in the model, if the package is'
                     ' the test package, check the state.')
            # for each package item in the model, if the package is the test
            # package, check the state is set to Applied
            for url in [lock_item_path, before_item_path]:
                stdout, _, _ = self.execute_cli_show_cmd(
                    self.management_node, url, '-j', load_json=False)
                stdout, stderr, rcode = self.run_command(
                    self.management_node,
                    self.cli.get_show_data_value_cmd(url, 'state'))

                self.assertEqual(0, rcode)
                self.assertEqual([], stderr)
                self.assertNotEqual([], stdout)
                self.assertTrue(
                    self.is_text_in_list('Applied', stdout),
                    'Expected state \'Applied\' not found '
                    'in stdout: \'{0}\''.format(stdout))
            self.log('info',
                     'Execute the create_plan command and show plan.')
            # LITPCDS-12781
            # execute the create_plan command and show plan
            self.execute_cli_createplan_cmd(self.management_node)
            stdout, _, _ = self.execute_cli_showplan_cmd(self.management_node)
            plan = self.cli.parse_plan_output(stdout)
            # check config task with persist flag set to False is in plan
            self.assertEqual(
                "Config task with persist flag set to False",
                plan[1][1]['DESC'][1]
                )
        finally:
            self.release_lock(lock_path)
