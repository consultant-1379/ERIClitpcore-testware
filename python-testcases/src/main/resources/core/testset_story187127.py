"""
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     May 2017
@author:    Laura Forbes
@summary:   TORF-187127
            As a LITP user I want the ability to resume a plan so that I can
            resume execution of a failed plan without having to re-run already
            successfully executed tasks again.
"""
import os
from litp_generic_test import GenericTest, attr
import test_constants as const
from redhat_cmd_utils import RHCmdUtils
from litp_cli_utils import CLIUtils
from vcs_utils import VCSUtils


class Story187127(GenericTest):
    """
        As a LITP user I want the ability to resume a plan so that I can
            resume execution of a failed plan without having to re-run already
            successfully executed tasks again.
    """

    def setUp(self):
        """ Runs before every single test """
        super(Story187127, self).setUp()

        self.vcs = VCSUtils()
        self.redhatutils = RHCmdUtils()
        self.cli = CLIUtils()
        self.ms_node = self.get_management_node_filename()
        self.mn_nodes = self.get_managed_node_filenames()
        self.node_urls = self.find(self.ms_node, "/deployments", "node")
        self.software_items = "/software/items/"
        self.plugin_id = 'torf187127'
        self.story_files = "187127_files"

    def tearDown(self):
        """ Runs after every single test """
        super(Story187127, self).tearDown()
        self._uninstall_rpms()

    @staticmethod
    def get_local_rpm_paths(path, rpm_id):
        """
        Description:
            Method that returns a list of absolute paths to the
            RPMs required to be installed for testing.
        Args:
            path (str): Path dir to check for RPMs.
            rpm_id (str): RPM name to check for in path.
        """
        # Get all RPMs in 'path' that contain 'rpm_id' in their name
        rpm_names = [rpm for rpm in os.listdir(path) if rpm_id in rpm]

        if not rpm_names:
            return None

        # Return a list of absolute paths to the RPMs found in 'rpm_names'
        return [
            os.path.join(rpath, rpm)
            for rpath, rpm in
            zip([os.path.abspath(path)] * len(rpm_names), rpm_names)
            ]

    def _install_rpms(self):
        """
        Description:
            Method that installs plugin and extension on
            the MS if they are not already installed.
        """
        # Check if the plugin is already installed
        _, _, rcode = self.run_command(
            self.ms_node, self.rhc.check_pkg_installed([self.plugin_id]),
            su_root=True)

        # If not, copy plugin and extension onto MS
        if rcode == 1:
            local_rpm_paths = self.get_local_rpm_paths(
                os.path.abspath(
                    os.path.join(os.path.dirname(__file__), 'plugins')
                ),
                self.plugin_id
            )
            self.assertTrue(
                self.copy_and_install_rpms(self.ms_node, local_rpm_paths),
                "There was an error installing the test plugin on the MS.")

    def _uninstall_rpms(self):
        """
        Description:
            Method that uninstalls plugin and extension on
            the MS.
        """
        local_rpm_paths = self.get_local_rpm_paths(
            os.path.join(
                os.path.dirname(repr(__file__).strip("'")), "plugins"
                ),
            self.plugin_id
            )
        if local_rpm_paths:
            installed_rpm_names = []
            for rpm in local_rpm_paths:
                std_out, std_err, rc = self.run_command_local(
                    self.rhc.get_package_name_from_rpm(rpm))
                self.assertEquals(0, rc)
                self.assertEquals([], std_err)
                self.assertEquals(1, len(std_out))

                installed_rpm_names.append(std_out[0])

            _, _, rc = self.run_command(self.ms_node,
                                        self.rhc.get_yum_remove_cmd(
                                            installed_rpm_names),
                                        add_to_cleanup=False,
                                        su_root=True
                                       )
            self.assertEquals(0, rc)

    def create_and_inherit_187127_item(self, item_id, inheriting_node):
        """
        Description:
            Creates an item of type 'torf-187127' with the
            given name and inherits it to the specified node.
        Args:
            item_id (str): Name of the item to create
            inheriting_node (str): URL of node to inherit the item
        """
        item_type = "torf-187127"
        props = 'date="Not-Yet-Set"'
        url_path = self.software_items + item_id
        self.execute_cli_create_cmd(self.ms_node, url_path, item_type, props)

        node_deployment = inheriting_node + "/items/" + item_id
        self.execute_cli_inherit_cmd(
            self.ms_node, node_deployment, url_path)

    def create_stat_file(self, node, item_id):
        """
        Description:
            Creates a file in the /tmp/ directory on
            the MS for the specified node.
            The filenames are of the format 'node_hostname-item_id'.
            These files are to be used by the ERIClitptorf187127 plugin.
        Args:
            node (str): Nodes to create a file for.
            item_id (str): Item ID to use in filenames.
        """
        file_to_create = "/tmp/{0}-{1}".format(node, item_id)
        self.log('info', 'Creating file {0} on MS.'.format(file_to_create))
        self.create_file_on_node(self.ms_node, file_to_create, ['Nada'])

    def check_file_exists(self, node, path_to_file):
        """
        Description:
            Checks if a file at the specified path exists on the given node.
        Args:
            node (str): Node to check if file exists on.
            path_to_file (str): File to the existence of.
        Returns:
            bool: True if file exists, False otherwise.
        """
        cmd = "ls {0}".format(path_to_file)
        std_out, _, rc = self.run_command(
            node, cmd, su_root=True, default_asserts=False)

        no_file = "No such file or directory"

        if not any(no_file in s for s in std_out) and rc == 0:
            return True
        return False

    def immutable_file(self, node, filename, operation):
        """
        Description:
            Set/unset a file to be immutable.
        Args:
            node (str): Node on which file resides.
            filename (str): File to perform operation on.
            operation (str): Add or remove immutable
                property. Must be "set" or "clear".
        """
        # Ensure file exists
        self.assertTrue(self.check_file_exists(node, filename),
                        "Cannot perform chattr operation on file {0} on {1} "
                        "as file does not exist.".format(filename, node))

        cmd = "chattr {0}i {1}".format(
            "+" if operation == "set" else "-", filename)
        std_out, std_err, rc = self.run_command(
            node, cmd, su_root=True, default_asserts=False)

        self.assertEqual([], std_out)
        self.assertEqual([], std_err)
        self.assertEqual(0, rc)

    #attr('all', 'revert', 'story187127', 'story187127_tc01')
    def obsolete_test_01_p_resume_multiple_failures(self):
        """
        #tms_id: torf_187127_tc01
        #tms_requirements_id: TORF-187127
        #tms_title: Resume Multiple Failures
        #tms_description:
            1) When I issue the command to resume the plan after
               a failed node VCS lock task, then the plan resumes
            2) When I issue the command to resume the plan after
               a failed node VCS unlock task, then the plan resumes
            3) When I issue the command to resume the plan after
               a failed Callback task, then the plan resumes
            4) When I issue the command to resume the plan after
               a failed Config task, then the plan resumes
            5) When I issue the command to resume the plan after
               multiple failed Config tasks, then the plan resumes
            6) When I issue the command to resume the plan twice
               after failures, then it will still fail
            17) Resume the plan which is in state initial
            18) Resume the plan which is in state successful
            20) Resume plan execution when no plan exists
        #tms_test_steps:
            #step: Install test plugin RPM on MS
            #result: Test plugin RPM successfully installed on MS
            #step: Create model items for the test and
                inherit them to a test node
            #result: Model items successfully created and
                inherited to the test node
            #step: Remove any existing LITP plan
            #result: No LITP plan exists
            #step: Execute "run_plan" command with the resume option
            #result: Error message 'Plan does not exist' is returned
            #step: Execute "create_plan" command
            #result: Plan created successfully
            #step: Execute "run_plan" command with the resume option
            #result: Error message 'Cannot resume
                plan in state "initial"' is returned
            #step: Modify httpd file on test node to
                force the locking of the node to fail
            #result: httpd file updated
            #step: Create a file on test node. The presence of
                this file with the modified httpd script will
                  cause the lock task to fail
            #result: File successfully created
            #step: Execute "run_plan" command
            #result: Plan transitions to Running
            #result: Plan fails on the lock task
            #step: Remove file on test node which caused lock task to fail
            #result: File successfully removed
            #step: Stop httpd service on the test node
            #result: httpd service successfully stopped
            #step: Create immutable file on test node to
                fail first Config task
            #result: File successfully created
            #step: Execute "run_plan" command with the resume option
            #result: Plan transitions to Running
            #result: Plan fails on Config task
            #step: Create immutable file on test node to
                fail second Config task
            #result: File successfully created
            #step: Execute "run_plan" command with the resume option
            #result: Plan transitions to Running
            #result: Plan fails on first and second Config tasks
            #step: Unset the immutable flag on the created files
            #result: Restriction removed from files
            #step: Execute "run_plan" command with the
                resume option (Do this step twice)
            #result: Plan transitions to Running
            #result: Plan fails on Callback task
            #step: Create stat files on MS to pass Callback tasks
            #result: Files successfully created
            #step: Create a file on test node. The presence of
                this file with the modified httpd script will
                  cause the unlock task to fail
            #result: File successfully created
            #step: Execute "run_plan" command with the resume option
            #result: Plan transitions to Running
            #result: Plan fails on the unlock task
            #step: Remove file on test node that caused unlock task to fail
            #result: File successfully removed
            #step: Clear the httpd service group
            #result: SG successfully cleared
            #step: Execute "run_plan" command with the resume option
            #result: Plan transitions to Running
            #result: Plan succeeds
            #step: Execute "run_plan" command with the resume option
            #result: Error message 'Cannot resume plan
                in state "successful"' is returned
            #step: Replace httpd file with original file
            #result: httpd file replaced with original contents
        #tms_test_precondition: ERIClitptorf187127 RPM available
        #tms_execution_type: Automated
        """
        pass

    @attr('all', 'revert', 'story187127', 'story187127_tc23')
    def test_23_p_resume_plan_after_litpd_restart(self):
        """
            @tms_id: torf_187127_tc23
            @tms_requirements_id: TORF-187127
            @tms_title: Resume plan works after a litpd restart
            @tms_description:
                23) Verify that when after plan has failed and after litpd has
                    restarted that resume works
                8) When I issue the command to resume the plan after the model
                    has been updated successfully by an executed task, then the
                    plan should resume and complete successfully
                7) When I issue the command to resume the plan after the model
                    has updated, the resumed running plan should fail
            @tms_test_steps:
                @step: Install test plugin RPM on MS
                @result: Test plugin RPM successfully installed on MS
                @step: Create model items for the test and
                    inherit them to a test node
                @result: Model items successfully created and
                    inherited to the test node
                @step: Create/run a plan to set up all the new items
                @result: Plan runs successfully
                @step: Create immutable file on the test node to
                    fail first Config task
                @result: Immutable file successfully created
                @step: Execute "create_plan" command
                @result: Plan created successfully
                @step: Execute "run_plan" command
                @result: Plan transitions to Running
                @result: Plan fails
                @step: Remove immutable property on file
                @result: File no longer immutable
                @step: Restart the litpd daemon
                @result: litpd restarts successfully
                @step: Create stat file on MS to pass first Callback task
                @result: File successfully created
                @step: Execute "run_plan" command with the resume option
                @result: Plan transitions to Running
                @result: Plan fails
                @result: Value of the "date" property on
                    the first Callback item was updated
                @step: Make a property update to a model item
                @result: Item successfully updated
                @step: Execute "run_plan" command with the resume option
                @result: Assert that plan fails to resume with correct error
            @tms_test_precondition: ERIClitptorf187127 RPM available
            @tms_execution_type: Automated
        """
        # Model items to create for test
        item_ids = ["foobar{0}".format(x) for x in range(5)]
        # Keep track of files created on nodes to remove later
        node_files = []
        test_node = self.mn_nodes[0]
        test_node_url = self.node_urls[0]

        try:
            self.log('info', '1. Install test plugin RPM on the MS.')
            self._install_rpms()

            self.log('info', '2. Create model items for the test and '
                             'inherit them to {0}.'.format(test_node))
            for item in item_ids:
                self.create_and_inherit_187127_item(item, test_node_url)

            self.log('info', '3. Create/run a plan to '
                             'set up all the new items.')
            self.log('info', '3a. Create stat files on '
                             'MS to pass Callback tasks.')
            for item in item_ids:
                self.create_stat_file(test_node, item)
            self.execute_cli_createplan_cmd(self.ms_node)
            self.execute_cli_runplan_cmd(self.ms_node)
            self.assertEqual(True, self.wait_for_plan_state(
                self.ms_node, const.PLAN_COMPLETE),
                             "Plan did not complete successfully.")
            self.log('info', '3b. Remove stat files on MS.')
            for item in item_ids:
                cmd = "rm -f /tmp/{0}-{1}".format(test_node, item)
                std_out, std_err, rc = self.run_command(
                    self.ms_node, cmd, su_root=True, default_asserts=False)

                self.assertEqual([], std_out)
                self.assertEqual([], std_err)
                self.assertEqual(0, rc)

            self.log("info", "BEGINNING 'LITPD RESTART' TEST.")
            self.log('info', '4. Create immutable file on {0} to'
                             ' fail first Config task.'.format(test_node))
            config_file = "/tmp/{0}-{1}".format(test_node, item_ids[0])
            node_files.append(config_file)
            self.generate_file(test_node, config_file, 1)
            self.immutable_file(test_node, config_file, "set")

            self.log('info', '5. Execute "create_plan" command.')
            self.execute_cli_createplan_cmd(self.ms_node)

            self.log('info', '6. Execute "run_plan" command.')
            self.execute_cli_runplan_cmd(self.ms_node)

            self.log('info', '7. Wait for the plan to fail.')
            self.assertEqual(True, self.wait_for_plan_state(
                self.ms_node, const.PLAN_FAILED),
                             "Plan not in expected Failed state.")

            self.log('info', '8. Remove immutable property on file.')
            self.immutable_file(test_node, config_file, "clear")
            node_files.remove(config_file)

            self.log('info', '9. Restart the litpd daemon.')
            # Tests TC23 - Resume plan works after a litpd restart
            self.restart_litpd_service(self.ms_node)

            self.log('info',
                     '10. Create stat file on MS to pass first Callback task.')
            self.create_stat_file(test_node, item_ids[0])

            # Tests TC8 - Plugin updates model during plan execution
            #  For "plugin model update" test
            self.log('info', 'Note the value of the "date" property '
                             'on the first Callback item.')
            item_urls = self.find(
                self.ms_node, self.node_urls[0], "torf-187127")
            first_item_url = [s for s in item_urls if "foobar0" in s][0]
            date_prop = self.get_props_from_url(
                self.ms_node, first_item_url, filter_prop="date")
            expected_prop_value = "value-from-plugin-create-plan-configuration"
            self.assertTrue(
                expected_prop_value in date_prop,
                "Date property of {0} not expected value of"
                " '{1}':\n{2}".format(first_item_url,
                                      expected_prop_value, date_prop))

            self.log('info', '11. Execute "run_plan" command '
                             'with the resume option.')
            self.execute_cli_runplan_cmd(self.ms_node, args="--resume")

            self.log('info', '12. Wait for the plan to fail.')
            self.assertEqual(True, self.wait_for_plan_state(
                self.ms_node, const.PLAN_FAILED),
                             "Plan not in expected Failed state.")

            self.log("info", "BEGINNING 'PLUGIN MODEL UPDATE' TEST.")
            self.log('info', '13. Ensure the value of the "date" property on '
                             'the first Callback item has been updated.')
            date_prop = self.get_props_from_url(
                self.ms_node, first_item_url, filter_prop="date")
            expected_prop_value = "value-from-plugin-callback"
            self.assertTrue(expected_prop_value in date_prop,
                            "Date property of {0} not expected value "
                            "of '{1}':\n{2}".format(
                                first_item_url, expected_prop_value,
                                date_prop))

            # Tests TC7 - Update model after failure
            self.log("info", "BEGINNING 'MODEL UPDATE AFTER FAILURE' TEST.")
            self.log('info', '14. Make a property update to a model item.')
            self.execute_cli_update_cmd(self.ms_node, first_item_url,
                                        args='date="Updated-Property-Value"')

            self.log('info',
                     '15. Execute "run_plan" command with the resume option.')
            std_out, std_err, rc = self.execute_cli_runplan_cmd(
                self.ms_node, args="--resume", expect_positive=False)

            self.log('info', '16. Assert that the plan fails to '
                             'resume with the correct error.')
            self.assertEqual([], std_out)
            self.assertEqual(1, rc)
            invalid_request_error = 'Cannot resume plan in state "invalid"'
            self.assertTrue(any(invalid_request_error in s for s in std_err),
                            "Expected error message '{0}' not "
                            "returned.".format(invalid_request_error))

        finally:
            # In case of test failure, ensure that the created file is no
            # longer immutable so it may be deleted in the test cleanup
            # Iterate backwards to so that list can be modified in-place
            for node in node_files[::-1]:
                self.immutable_file(test_node, node, "clear")
                node_files.remove(node)

    @attr('all', 'revert', 'story187127', 'story187127_tc25')
    def test_25_p_resume_plan_after_model_deletions(self):
        """
            @tms_id: torf_187127_tc25
            @tms_requirements_id: TORF-187127
            @tms_title: Resume plan works after plan
                failure with deletion of model items
            @tms_description:
                Verify that resuming a plan works after a failed plan where
                    model items were being deleted and a subsequent plan
                        also runs successfully.
            @tms_test_steps:
                @step: Install test plugin RPM on MS
                @result: Test plugin RPM successfully installed on MS
                @step: Create model items for the test and
                    inherit them to a test node
                @result: Model items successfully created and
                    inherited to the test node
                @step: Create stat files on MS to pass Callback tasks
                @result: Files successfully created
                @step: Execute "create_plan" command
                @result: Plan created successfully
                @step: Execute "run_plan" command
                @result: Plan transitions to Running
                @result: Plan succeeds
                @step: Remove all test items from the model
                @result: Items transition to ForRemoval state
                @step: Create immutable files on the test node to
                    fail Config tasks
                @result: Immutable files successfully created
                @step: Execute "create_plan" command
                @result: Plan created successfully
                @step: Execute "run_plan" command
                @result: Plan transitions to Running
                @result: Plan fails
                @step: Remove immutable property on files
                @result: Files no longer immutable
                @step: Execute "run_plan" command with the resume option
                @result: Plan transitions to Running
                @result: Plan succeeds
                @step: Create a model item and inherit it to the test node
                @result: Model item successfully created and
                    inherited to the test node
                @step: Execute "create_plan" command
                @result: Plan created successfully
                @step: Execute "run_plan" command
                @result: Plan transitions to Running
                @result: Plan succeeds
            @tms_test_precondition: ERIClitptorf187127 RPM available
            @tms_execution_type: Automated
        """
        # Model items to create for test
        item_ids = ["foobar{0}".format(x) for x in range(5)]
        # Keep track of files created on nodes to remove later
        node_files = []
        test_node = self.mn_nodes[0]
        test_node_url = self.node_urls[0]

        try:
            self.log('info', '1. Install test plugin RPM on the MS.')
            self._install_rpms()

            self.log('info', '2. Create model items for the test and '
                             'inherit them to {0}.'.format(test_node))
            self.log('info', '3. Create stat files on '
                             'MS to pass Callback tasks.')
            for item in item_ids:
                self.create_and_inherit_187127_item(item, test_node_url)
                self.create_stat_file(test_node, item)

            self.log('info', '4. Execute "create_plan" command.')
            self.execute_cli_createplan_cmd(self.ms_node)

            self.log('info', '5. Execute "run_plan" command '
                             'without the resume option.')
            self.execute_cli_runplan_cmd(self.ms_node)

            self.log('info', '6. Wait for the plan to succeed.')
            self.assertEqual(True, self.wait_for_plan_state(
                self.ms_node, const.PLAN_COMPLETE),
                             "Plan did not complete.")

            self.log('info', '7. Remove all test items from the model.')
            for item in item_ids:
                url_path = self.software_items + item
                self.execute_cli_remove_cmd(self.ms_node, url_path)

            self.log('info', '8. Create immutable files on {0} to '
                             'fail Config tasks.'.format(test_node))
            fail_tasks = [item_ids[1], item_ids[3]]
            for item in fail_tasks:
                config_file = "/tmp/{0}-{1}".format(test_node, item)
                node_files.append(config_file)
                self.generate_file(test_node, config_file, 1)
                self.immutable_file(test_node, config_file, "set")

            self.log('info', '9. Execute "create_plan" command.')
            self.execute_cli_createplan_cmd(self.ms_node)

            self.log('info', '10. Execute "run_plan" command '
                             'without the resume option.')
            self.execute_cli_runplan_cmd(self.ms_node)

            self.log('info', '11. Wait for the plan to fail.')
            self.assertEqual(True, self.wait_for_plan_state(
                self.ms_node, const.PLAN_FAILED),
                             "Plan not in expected Failed state.")

            self.log('info', '12. Remove immutable property on files.')
            # Iterate backwards to so that list can be modified in-place
            for node in node_files[::-1]:
                self.immutable_file(test_node, node, "clear")
                node_files.remove(node)

            self.log('info', '13. Execute "run_plan" command '
                             'with the resume option.')
            self.execute_cli_runplan_cmd(self.ms_node, args="--resume")

            self.log('info', '14. Wait for the plan to succeed.')
            self.assertEqual(True, self.wait_for_plan_state(
                self.ms_node, const.PLAN_COMPLETE),
                             "Plan did not complete.")

            self.log('info', '15. Create one model item and '
                             'inherit it to {0}.'.format(test_node))
            self.create_and_inherit_187127_item(item_ids[0], test_node_url)

            self.log('info', '16. Execute "create_plan" command.')
            self.execute_cli_createplan_cmd(self.ms_node)

            self.log('info', '17. Execute "run_plan" command '
                             'without the resume option.')
            self.execute_cli_runplan_cmd(self.ms_node)

            self.log('info', '18. Wait for the plan to succeed.')
            self.assertEqual(True, self.wait_for_plan_state(
                self.ms_node, const.PLAN_COMPLETE),
                             "Plan did not complete.")

        finally:
            # In case of test failure, ensure that the created file is no
            # longer immutable so it may be deleted in the test cleanup
            # Iterate backwards to so that list can be modified in-place
            for node in node_files[::-1]:
                self.immutable_file(test_node, node, "clear")
                node_files.remove(node)
