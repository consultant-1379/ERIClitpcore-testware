"""
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     April 2015
@author:    Maria Varley
@summary:   LITPCDS-8260
            As a LITP Developer, I want the LITP execution / puppet manager
            to take a copy of the puppet manifests when a plan fails,
            so that I can troubleshoot failures
"""

from litp_generic_test import GenericTest, attr
from redhat_cmd_utils import RHCmdUtils
import test_constants as const


class Story8260(GenericTest):
    """
    As a LITP Developer, I want the LITP execution / puppet manager
    to take a copy of the puppet manifests when a plan fails,
    so that I can troubleshoot failures
    """
    def setUp(self):
        """ Runs before every single test """
        super(Story8260, self).setUp()
        self.ms_node = self.get_management_node_filename()
        self.redhatutils = RHCmdUtils()
        self.expect_access = "-rw-r-----"
        self.node1_path = self.find(self.ms_node, "/deployments", "node",
                            True)[0]
        self.peer_nodes = self.get_managed_node_filenames()
        self.sysparam_node1_config = self.find(self.ms_node, self.node1_path,
                                        "sysparam-node-config")[0]
        self.site_pp = 'site.pp'

    def tearDown(self):
        """ Runs after every single test """
        super(Story8260, self).tearDown()

    def _check_backed_up_manifests_permissions(self):
        """
        Description: Function that finds the access rights in human
            readable form of each of the puppet manifests
            in the back-up puppet manifest directory
        """
        dir_contents = self.list_dir_contents(self.ms_node,
                                              const.PUPPET_FAILED_DIR)

        # For each of the puppet manifest files listed in the
        # directory, and using the stat command, find the
        # access rights in human readable form for each file
        for pfile in dir_contents:
            cmd = '{0} -c %A {1}/{2}'. \
                format(const.STAT_PATH,
                       const.PUPPET_FAILED_DIR,
                       pfile)
            stdout, _, _ = self.run_command(self.ms_node, cmd, su_root=True,
                default_asserts=True)
            self.assertTrue(self.is_text_in_list(self.expect_access, stdout))

    def _find_all_specific_tasks_in_plan(self, stdout, description, node_path):
        """
        Description: Searches through the plan and returns a list of matching
            tasks.
        Args:
            stdout (str): Output of the show command used
            description (str): Plan description from show plan cmd
            node_path (str): Node to search for in show plan cmd
        Return:
            matching_tasks (list): The tasks that match the description and
                node
        """
        matching_tasks = []
        plan_d = self.cli.parse_plan_output(stdout)
        for phase in plan_d.keys():
            for task in plan_d[phase].keys():
                # Only find matching tasks
                desc = plan_d[phase][task]['DESC']
                if description in desc and node_path in desc:
                    matching_tasks.append(plan_d[phase][task])
        return matching_tasks

    def _get_checksums(self, folder):
        """
        Description:
            Calculate the checksum of the content of each files in the
            given directory
        Args:
            folder (str): Fully qualified name of the file we want the
                            checksum of
        Return:
            list, The checksum of the content of each file in dir
        """
        if not folder.endswith('/'):
            folder += '/'
        files = self.list_dir_contents(self.ms_node, folder)
        md5 = {}
        for filename in files:
            file_path = '{0}{1}'.format(folder, filename)
            cmd = self.redhatutils.get_md5sum_cmd('', file_path)
            out = self.run_command(self.ms_node, cmd, default_asserts=True,
                su_root=True)[0]
            md5[filename] = (out[0].split(' '))[0]
        return md5

    @attr('all', 'revert', 'story8260', 'story8260_tc01')
    def test_01_p_manifest_backup_config_task_fail(self):
        """
        @tms_id: litpcds_8260_tc01
        @tms_requirements_id: LITPCDS-8260
        @tms_title: Verify all puppet manifests are saved when a plan fails
                    due to a config task failure
        @tms_description: Test that when a plan fails due to a config tasks
                          failure, a copy of all the puppet manifests is saved
                          to /var/lib/litp/core/puppet_failed/*.pp. Test that
                          these files are overwritten when a 2nd plan fails due
                          to a config task failure. Test that these files are
                          not overwritten when a subsequent plan is successful
        @tms_test_steps:
            @step: Assert the site.pp file is not present on the MS
            @result: File site.pp verified to not exist on system
            @step: Create a model item
            @result: Item model successfully created
            @step: Define system-param on node1 with pre-existing key in the
            file
            @result: system-param successfully created from existing key
            @step: Check the puppet manifest backup directory does not exist
            @result: Puppet manifest backup directory verified to not exist
            @step: Create, run, and wait for plan to complete
            @result: Plan completes successfully
            @step: Check that puppet manifest backup directory still does not
            exist
            @result: Puppet backup directory verified to not exist
            @step: Update model item
            @result: Model item in Initial state
            @step: Create, run, and wait for plan to complete
            @result: Plan fails
            @step: Assert the site.pp file is not present on the MS
            @result: File site.pp verified to not exist on MS node
            @step: Check that a copy of the puppet manifests has been taken
            and added to the directory
            @result: Copy of the puppet manifests verified to exist in
            directory
            @step: Check that a backup of the manifest files has been taken
            and that they have the right permission set
            @result: Latest manifest files verified to be in directory and
            permissions verified to match expected values
            @step: Update the item with an invalid property value
            @result: Item updated and in Initial state
            @step: Create, run, and wait for plan to complete
            @result: Plan fails
            @step: Check puppet manifest and manifest backup files have not
            changed with the exception of backup manifest file of node1
            @result: Puppet manifest and manifest backup files verified to be
            unchanged
            @step: Update the previously failing model item with a valid input
            @result: Item updated and in Initial state
            @step: Create, run, and wait for plan to complete
            @result: Plan succeeds
            @step: Check that a copy of the puppet manifests has not been taken
            @result: Copy of the puppet manifests verified to not have been
            taken
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        self.log('info',
            '1. Assert that site.pp file is not present on the ms')
        manifest_files = self.list_dir_contents(self.ms_node,
                            const.PUPPET_MANIFESTS_DIR)
        self.assertFalse(self.is_text_in_list(self.site_pp, manifest_files),
            'site.pp file was found unexpectedly in {0}'
            .format(const.PUPPET_MANIFESTS_DIR))

        expected_pp_files = sorted(self.list_dir_contents(self.ms_node,
                                    const.PUPPET_MANIFESTS_DIR))
        self.log('info',
            'Make a backup of current PUPPET_FAILED_DIR and remove the folder')
        if self.remote_path_exists(self.ms_node, const.PUPPET_FAILED_DIR,
        expect_file=False):
            self.backup_file(self.ms_node, const.PUPPET_FAILED_DIR)
            self.remove_item(self.ms_node, const.PUPPET_FAILED_DIR,
                su_root=True)

        self.log('info', 'Backup current sysparam configuration')
        ms_pp = '{0}.pp'.format(self.ms_node)
        mn1_pp = '{0}.pp'.format(self.peer_nodes[0])
        mn2_pp = '{0}.pp'.format(self.peer_nodes[1])

        sysctl_backup_dir = "/tmp/sysctl"
        self.assertTrue(self.cp_file_on_node(self.peer_nodes[0],
                                             const.SYSCTL_CONFIG_FILE,
                                             sysctl_backup_dir,
                                             su_root=True))

        pp_md5_initial = self._get_checksums(const.PUPPET_MANIFESTS_DIR)
        self.assertEqual(expected_pp_files, sorted(pp_md5_initial))

        self.log('info', '2. Create and deploy a new sysparam item')
        sysctl_key1 = "net.ipv4.ip_forward"
        sysctl_val1 = "599"
        sysctl_val2 = "val2"
        sysctl_val3 = "val3"

        self.log('info', '3. Define system-param on node1 with pre-existing '
            'key in the file')
        try:
            props = 'key="{0}" value="{1}"'.format(sysctl_key1, sysctl_val1)
            sys_param_path = "{0}{1}".format(self.sysparam_node1_config,
                                            "/params/8260tc01")

            self.log('info', '4. Check the that puppet manifest backup '
                   'directory does not exist')
            self.assertFalse(self.remote_path_exists(self.ms_node,
                                                     const.PUPPET_FAILED_DIR,
                                                     expect_file=False))
            self.execute_cli_create_cmd(self.ms_node,
                                        sys_param_path,
                                        "sysparam",
                                        props)

            self.log('info', '5. Create, run and wait for plan to complete')
            self.run_and_check_plan(self.ms_node,
                                    const.PLAN_COMPLETE,
                                    plan_timeout_mins=20)

            self.log('info', 'Calculate md5 checksum of puppet manifest files')
            pp_md5_1 = self._get_checksums(const.PUPPET_MANIFESTS_DIR)
            self.assertEqual(expected_pp_files, sorted(pp_md5_1))

            self.log('info', '6. Check the that puppet manifest backup '
                   'directory still does not exist')
            self.assertFalse(self.remote_path_exists(self.ms_node,
                                                     const.PUPPET_FAILED_DIR,
                                                     expect_file=False))

            self.log('info', '7. Update the item with an invalid '
                   'property value to cause the plan to fail')
            # Since node1 is the only node with a config task in the plan
            # we expect that when the plan fails only the backup manifest file
            # of node 1 only differs from node1's manifest file
            props = 'key="{0}" value="{1}"'.format(sysctl_key1, sysctl_val2)
            self.execute_cli_update_cmd(self.ms_node, sys_param_path, props)

            self.log('info', '8. Create, run and wait for plan to complete')
            self.run_and_check_plan(self.ms_node,
                                    const.PLAN_FAILED,
                                    plan_timeout_mins=20)

            self.log('info',
                '9. Verify that site.pp file is not present on the ms')
            puppet_files = {
                const.PUPPET_MANIFESTS_DIR: self.list_dir_contents(
                    self.ms_node, const.PUPPET_MANIFESTS_DIR),
                const.PUPPET_FAILED_DIR: self.list_dir_contents(
                    self.ms_node, const.PUPPET_FAILED_DIR)
            }

            for directory, files in puppet_files.iteritems():
                self.assertFalse(self.is_text_in_list(self.site_pp, files),
                'site.pp file was found unexpectedly in {0}'
                .format(directory))

            self.log('info', '10. Check that a backup of the manifest files '
                    'has been taken and that they have the right permission '
                    'set')
            pp_md5_2 = self._get_checksums(const.PUPPET_MANIFESTS_DIR)
            bkp_md5_1 = self._get_checksums(const.PUPPET_FAILED_DIR)
            self.assertEqual(expected_pp_files, sorted(pp_md5_2))
            self.assertEqual(expected_pp_files, sorted(bkp_md5_1))
            self.assertEqual(bkp_md5_1[ms_pp], pp_md5_2[ms_pp])
            self.assertEqual(bkp_md5_1[mn2_pp], pp_md5_2[mn2_pp])
            self.assertNotEqual(bkp_md5_1[mn1_pp], pp_md5_2[mn1_pp])
            self._check_backed_up_manifests_permissions()

            self.log('info', '11. Update the item with a different invalid '
                   'property value to cause the plan to fail again')
            # Since node1 is the only node with a config task in the plan
            # we expect that when the plan fails a new backup manifest file
            # of node 1 only is created and override the existing one
            props = 'key="{0}" value="{1}"'.format(sysctl_key1, sysctl_val3)
            self.execute_cli_update_cmd(self.ms_node, sys_param_path, props)

            self.log('info', '12. Create, run and wait for plan to complete')
            self.run_and_check_plan(self.ms_node,
                                    const.PLAN_FAILED,
                                    plan_timeout_mins=20)

            self.log('info', '13. Check puppet manifest and manifest backup '
                   'files have not changed with the exception of '
                   'backup manifest file of node1')
            pp_md5_3 = self._get_checksums(const.PUPPET_MANIFESTS_DIR)
            bkp_md5_2 = self._get_checksums(const.PUPPET_FAILED_DIR)
            self.assertEqual(expected_pp_files, sorted(pp_md5_3))
            self.assertEqual(expected_pp_files, sorted(bkp_md5_1))
            self.assertEqual(bkp_md5_2[ms_pp], pp_md5_3[ms_pp])
            self.assertEqual(bkp_md5_2[mn2_pp], pp_md5_3[mn2_pp])
            self.assertNotEqual(bkp_md5_2[mn1_pp], bkp_md5_1[mn1_pp])

            self.log('info', '14. Remove the item created in this test to '
                   'create and run a that should succeed')
            self.execute_cli_remove_cmd(self.ms_node,
                                        sys_param_path,
                                        add_to_cleanup=False)

            # LITPCDS-5890:
            # When a node Unlock task fails I want the next plan run to
            # identify that a Node with no model updates is in an locked
            # state and needs to be unlocked
            # Test LITPCDS-6170:
            # VCS unlock task in two different phases runs simultaneously
            is_locked = self.get_props_from_url(self.ms_node,
                                                self.node1_path,
                                                filter_prop='is_locked')
            self.assertEqual('true', is_locked)

            self.execute_cli_createplan_cmd(self.ms_node)

            # Assert that there are 2 unlock tasks in the plan
            stdout = self.execute_cli_showplan_cmd(self.ms_node)[0]
            first_unlock_task = self.cli.parse_plan_output(stdout)[1][1]
            matching_unlock_tasks = \
                self._find_all_specific_tasks_in_plan(
                                                stdout,
                                                first_unlock_task["DESC"][1],
                                                first_unlock_task['DESC'][0])
            self.assertEqual(2, len(matching_unlock_tasks),
                        "Two 'unlock' tasks not found in plan.")

            self.log('info', '15. Create, run, and wait for plan to complete')
            self.execute_cli_runplan_cmd(self.ms_node)
            self.assertTrue(self.wait_for_plan_state(self.ms_node,
                                                     const.PLAN_COMPLETE))

            self.log('info', '16. Check that puppet manifest files have '
                   'changed while the manifest backup files have not changed')
            pp_md5_4 = self._get_checksums(const.PUPPET_MANIFESTS_DIR)
            bkp_md5_3 = self._get_checksums(const.PUPPET_FAILED_DIR)
            self.assertEqual(expected_pp_files, sorted(pp_md5_4))
            self.assertEqual(expected_pp_files, sorted(bkp_md5_1))
            self.assertEqual(sorted(pp_md5_4), sorted(pp_md5_initial))
            self.assertEqual(bkp_md5_3[ms_pp], bkp_md5_3[ms_pp])
            self.assertEqual(bkp_md5_3[mn2_pp], bkp_md5_3[mn2_pp])
            self.assertEqual(bkp_md5_3[mn1_pp], bkp_md5_3[mn1_pp])

        finally:
            self.log('info', 'FINALLY: Restore initial configuration')
            self.remove_item(self.ms_node, const.PUPPET_FAILED_DIR,
                su_root=True)

            self.assertTrue(self.cp_file_on_node(self.peer_nodes[0],
                                                 sysctl_backup_dir,
                                                 const.SYSCTL_CONFIG_FILE,
                                                 su_root=True))

            cmd = self.redhatutils.get_sysctl_cmd(
                                '-e -p {0}'.format(const.SYSCTL_CONFIG_FILE))
            stdout = self.run_command(self.peer_nodes[0],
                                            cmd,
                                            default_asserts=True,
                                            su_root=True)[0]
            self.assertNotEqual([], stdout)
