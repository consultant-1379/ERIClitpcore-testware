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
from litp_generic_test import GenericTest
from redhat_cmd_utils import RHCmdUtils


class Story2682(GenericTest):
    """
    LITPCDS-2682:
        As a system developer, I want to include a clean up phase in the plan
        so that LITP can remove items from the model which are no longer
        required
    """

    def setUp(self):
        """
        Description:
            Runs before every test to perform required setup
        """
        # call super class setup
        super(Story2682, self).setUp()
        # get the management node of the cluster
        self.management_node = self.get_management_node_filename()
        # set up required test item
        self.rhc = RHCmdUtils()
        self.test_plugins = (
            'ERIClitpstory2682api_CXP1234567-1.0.1-SNAPSHOT20140411105843.'\
            'noarch.rpm',
            'ERIClitpstory2682_CXP1234567-1.0.1-SNAPSHOT20140428150434.'\
            'noarch.rpm')
        self.item_extension = 'story2682'
        self.plugin = 'story2682'
        self.item_type = 'story2682'
        self.item = 'story2682'
        self.package = 'finger'
        self.package_type = 'package'
        self.url = '/story_2682'
        self.properties = (
            'name=\'{0}\'',
            'callback_task_true=\'{0}\'',
            'config_task_true=\'{0}\'',
            'no_task_true=\'{0}\'')
        self.relevant_urls = list()

    def tearDown(self):
        """
        Description:
            Runs after every test to perform required cleanup/teardown
        """

        # call super class teardown
        super(Story2682, self).tearDown()

    def _is_plugin_installed(self, plugin):
        """
        Desrcription:
            Check if the required dummy plugins, for the test to run, are
            already installed from a previous test run
        """

        # check if the given plugin rpm is installed or not
        _, stderr, rcode = self.run_command(self.management_node,
                        self.rhc.check_pkg_installed([plugin]))
        self.assertEqual([], stderr)

        if rcode == 0:
            return True

        return False

    def _check_installed_plugins(self):
        """
        Description:
            Check which, if any, dummy plugins are installed and get the list
            of those which aren't but are required
        """

        plugins_require_install = list()
        # for each plugin rpm in tuple test plugins, check if the rpm is
        # already installed and if not, mark it for installation
        for plugin in self.test_plugins:
            if not self._is_plugin_installed(plugin.split('.rpm')[0]):
                plugins_require_install.append(plugin)

        return plugins_require_install

    def _install_plugins(self):
        """
        Description:
            For any dummy plugin, required by the test, that aren't installed,
            install them
        """

        # get the directory path of where the current test file is located
        local_path = '{0}'.format(os.path.dirname(repr(__file__).strip('\'')))

        plugins_require_install = self._check_installed_plugins()
        if plugins_require_install:
            # for each plugin marked for installation, copy the rpm to the
            # management node where the test is running on
            for plugin in plugins_require_install:
                local_filepath = '{0}/{1}'.format(local_path, plugin)
                self.assertTrue(self.copy_file_to(self.management_node,
                                local_filepath, const.LITP_PKG_REPO_DIR,
                                                root_copy=True,
                                                  add_to_cleanup=False),
                    'Failed to copy file \'{0}\' to \'{1}\' on node \'{2}\''.\
                    format(local_filepath, const.LITP_PKG_REPO_DIR,
                                                        self.management_node))

            # recreate the yum repository to recognise the newly copied rpm
            # files
            stdout, stderr, rcode = self.run_command(self.management_node,
                                                self.rhc.get_createrepo_cmd(
                                                    const.LITP_PKG_REPO_DIR),
                                                su_root=True)
            self.assertEqual(0, rcode)
            self.assertEqual([], stderr)
            self.assertNotEqual([], stdout)

            # remove the .rpm extension from each of the plugins marked for
            # installation so yum will be able to recognise them and install
            # them
            plugins_require_install[:] = [plugin.split('.rpm')[0] \
                                         for plugin in plugins_require_install]

            # install the rpm files using yum
            stdout, stderr, rcode = self.run_command(self.management_node,
                                                self.rhc.get_yum_install_cmd(
                                                    plugins_require_install),
                                                su_root=True)
            self.assertEqual(0, rcode)
            self.assertEqual([], stderr)
            self.assertNotEqual([], stdout)

            # check that the plugins were successfully installed
            for plugin in plugins_require_install:
                self.assertTrue(self._is_plugin_installed(plugin),
                'Failed to install plugin \'{0}\''.format(plugin))

        self._check_plugin_is_registered()

    def _check_plugin_is_registered(self):
        """
        Description:
            Check the plugins required for the test run are registered with the
            litpd service
        """

        # check the plugin is registered with the litpd service
        expected_info_logs = ['INFO: Added ModelExtension: \\"{0}\\"'.format(
                                                        self.item_extension),
                              'INFO: Added Plugin: \\"{0}\\"'.format(
                                                                self.plugin)]

        stdout, stderr, rcode = self.run_command(self.management_node,
                                                self.rhc.get_grep_file_cmd(
                                                    const.GEN_SYSTEM_LOG_PATH,
                                                    expected_info_logs),
                                                su_root=True)
        self.assertEqual(0, rcode)
        self.assertEqual([], stderr)
        self.assertNotEqual([], stdout)

    def _exec_common_test_methods(self, item_type, properties, uri='',
                                 create_plan=True, run_plan=True):
        """
        Description:
            Add the test package, required for the test, to the model and
            execute the create_plan/run_plan so that it's installed before the
            test is executed
        """

        # get the software-item url from the model and append the test package
        # url and properties
        software_item_url = self.find(self.management_node, '/software',
                                    'software-item',
                                    rtn_type_children=False)[0]
        test_url = '{0}{1}{2}'.format(software_item_url, self.url, uri)

        # execute the create command
        self.execute_cli_create_cmd(self.management_node, test_url, item_type,
                                    properties)

        # check the state of the item is Initial
        state = self.execute_show_data_cmd(self.management_node, test_url,
                                          'state')
        self.assertEqual('Initial', state)

        self.relevant_urls.append(test_url)

        # get all the node urls and for each node, get the software-item url
        # child and link the test package url to the node and check the state
        # of the item is Initial
        nodes = self.find(self.management_node, '/deployments', 'node')
        nodes.append('/ms')
        link_urls = list()
        for node in nodes:
            software_item_url = self.find(self.management_node, node,
                                        'software-item',
                                        rtn_type_children=False)[0]
            link_url = '{0}{1}{2}'.format(software_item_url, self.url, uri)
            link_urls.append(link_url)
            self.execute_cli_inherit_cmd(
                self.management_node,
                link_url,
                test_url
            )
            state = self.execute_show_data_cmd(self.management_node, link_url,
                                              'state')
            self.assertEqual('Initial', state)

            self.relevant_urls.append(link_url)

        if create_plan:
            # execute the create_plan command
            self.execute_cli_createplan_cmd(self.management_node)

        # check if the plan is expected to be executed
        if run_plan:
            # execute the run_plan command and wait for plan completion
            self.execute_cli_runplan_cmd(self.management_node)
            self.assertTrue(self.wait_for_plan_state(self.management_node,
                                                    const.PLAN_COMPLETE))

            # check the item is set to Applied
            state = self.execute_show_data_cmd(self.management_node, test_url,
                                              'state')
            self.assertEqual('Applied', state)

            # check all the link urls are set to Applied
            for link_url in link_urls:
                state = self.execute_show_data_cmd(self.management_node,
                                                  link_url, 'state')
                self.assertEqual('Applied', state)

    def obsolete_01_p_remove_model_item_cleanup_phase(self):
        """
        Obsolete - already tested by ATs:
            ERIClitpcore/plan/plan_cleanup_phase.at
        Description:
            Execute the CLI remove command on an item in the model, which does
            not generate its own deconfigure/remove tasks from a separate
            plugin, execute the create_plan command and the item must be marked
            for removal/cleanup in the final phase in the plan and, after a
            successfule plan execution, the item will no longer exist in the
            model. Restoring those items, and executing a plan, will restore
            all items successfully

        Steps:
            1.  Execute the remove command on an item in the model
            2.  Item will be marked ForRemoval
            3.  Execute the create_plan command
            4.  Check that the item marked ForRemoval is listed in the cleanup
                phase
            5.  Execute the run_plan command
            6.  Wait for plan execution completion
            7,  Check that the item is indeed removed from the model tree
            8.  Execute a service litpd restart
            9.  Recreate the same item in the model
            10. Link the same item to all the nodes again
            11. Execute the create_plan command
            12. Execute the run_plan command
            13. Wait for successful plan execution
            14. Check the item is successfully restored

        Result:
            Model item must be removed from the tree and restored after the
            second plan execution
        """

        # install the test package required for the test
        properties = self.properties[0].format(self.package)
        self._exec_common_test_methods(self.package_type, properties)

        for relevant_url in self.relevant_urls:
            if '/software' not in relevant_url:
                self.execute_cli_remove_cmd(self.management_node, relevant_url)
                state = self.execute_show_data_cmd(self.management_node,
                                                  relevant_url, 'state')
                self.assertEqual('ForRemoval', state)

        # execute the create_plan command
        self.execute_cli_createplan_cmd(self.management_node)

        # execute the show_plan command and check there exists a task to
        # uninstall the test package using the package deconfigure() method
        stdout, _, _ = self.execute_cli_showplan_cmd(self.management_node)
        lookup_str = 'Remove package "{0}"'.format(self.package)
        self.assertTrue(self.is_text_in_list(lookup_str, stdout),
            'Expected string match \'{0}\' not found in \'{1}\''.format(
                                                                    lookup_str,
                                                                    stdout))

        self.execute_cli_runplan_cmd(self.management_node)
        self.assertTrue(
            self.wait_for_plan_state(
                self.management_node,
                const.PLAN_COMPLETE
            )
        )

        for relevant_url in self.relevant_urls:
            if '/software' in relevant_url:
                self.execute_cli_remove_cmd(self.management_node, relevant_url)
                state = self.execute_show_data_cmd(self.management_node,
                                                  relevant_url, 'state')
                self.assertEqual('ForRemoval', state)

        self.execute_cli_createplan_cmd(self.management_node)

        stdout, _, _ = self.execute_cli_showplan_cmd(self.management_node)

        # get all tasks of the final phase, which will be the cleanup phase
        # from the plan and check there exists a task to remove the
        # test package url from the model under software-item which is not part
        # of the package item deconfigure() task
        final_phase_index = [stdout.index(line) for line in stdout
                            if 'Phase' in line][-1]
        final_phase_list = stdout[final_phase_index:len(stdout)]
        lookup_str = self.url
        self.assertTrue(self.is_text_in_list(lookup_str, stdout),
            'Expected string match \'{0}\' not found in stdout: \'{1}\''.\
                                                    format(lookup_str, stdout))
        lookup_next_line = [final_phase_list[final_phase_list.index(line) + 1]
                                for line in final_phase_list
                                    if lookup_str in line][0]
        self.assertTrue(self.is_text_in_list('Remove Item',
                                            [lookup_next_line]),
            'Expected string match \'Remove Item\' not found in \'{0}\''.\
                                                    format(lookup_next_line))
        self.assertTrue(self.is_text_in_list(lookup_next_line, stdout),
            'Expected string match \'{0}\' not found in \'{1}\''.format(
                                                    lookup_next_line, stdout))

        # check that none of the linked package items are in the final phase,
        # since the deconfigure() task should handle their removal from the
        # model tree
        for relevant_url in self.relevant_urls:
            if '/software' in relevant_url:
                continue
            else:
                if 'nodes/' in relevant_url:
                    lookup_str = relevant_url.split('nodes/')[-1]
                else:
                    lookup_str = relevant_url
                self.assertFalse(self.is_text_in_list(lookup_str,
                                                     final_phase_list),
                    'Unexpected string match \'{0}\' found in \'{1}\''.format(
                                                            lookup_str,
                                                            final_phase_list))

        # execute the run_plan command and wait for plan completion
        self.execute_cli_runplan_cmd(self.management_node)
        self.assertTrue(self.wait_for_plan_state(self.management_node,
                                                const.PLAN_COMPLETE))

        # for each relevant package url, check that the urls no longer exist in
        # the model
        for relevant_url in self.relevant_urls:
            _, stderr, _ = self.execute_cli_show_cmd(self.management_node,
                                                    relevant_url,
                                                    expect_positive=False)
            expect_err = 'InvalidLocationError'
            self.assertTrue(self.is_text_in_list(expect_err, stderr),
                'Expected error message \'{0}\' not found in \'{1}\''.format(
                                                                    expect_err,
                                                                    stderr))

        # finally, restart the litpd service to test LITPCDS-2495, the service
        # must not crash after a deconfigure() task is run
        self.restart_litpd_service(self.management_node)

        # recreate the relevant urls in the model tree
        self.relevant_urls = list()
        self._exec_common_test_methods(self.package_type, properties,
                                      run_plan=False)

        # execute the show_plan command and check there exists a task to
        # install the test package
        lookup_str = '{0}'.format(self.url)
        stdout, _, _ = self.execute_cli_showplan_cmd(self.management_node)
        self.assertTrue(self.is_text_in_list(lookup_str, stdout),
            'Expected string match \'{0}\' not found in \'{1}\''.format(
                                                                    lookup_str,
                                                                    stdout))
        lookup_str = 'Install package "{0}"'.format(self.package)
        self.assertTrue(self.is_text_in_list(lookup_str, stdout),
            'Expected string match \'{0}\' not found in \'{1}\''.format(
                                                                    lookup_str,
                                                                    stdout))

    def obsolete_02_p_remove_multiple_items(self):
        """
        Obsolete - already tested by ATs:
            ERIClitpcore/plan/plan_cleanup_phase.at
        Description:
            Execute the CLI remove command on an item's links in the model,
            and after plan execution, the item's links must be removed but the
            item itself, under software-item, will remain in the model tree
            and will remain in an Applied state

        Steps:
            1.  Execute the remove command on multiple item links in the model
            2.  Items will be marked ForRemoval
            3.  Execute the create_plan command
            4.  Check that the items marked ForRemoval have tasks in the plan
            5.  Execute the run_plan command
            6.  Wait for plan execution completion
            7,  Check that the all the model item links are removed and the
                software-item remains in Applied state

        Result:
            Model item links are removed, but the software-item remains in the
            tree and in Applied state
            """

        # install the test package required for the test
        properties = self.properties[0].format(self.package)
        self._exec_common_test_methods(self.package_type, properties)

        # get a list of all node urls from the model and for each node, get all
        # the linked package items, searching for the test package; if found,
        # add it to the relevant urls list and execute the remove command on
        # the link; finally check the item state is ForRemoval
        nodes = self.find(self.management_node, '/deployments', 'node')
        nodes.append('/ms')

        for relevant_url in self.relevant_urls:
            if '/software' not in relevant_url:
                self.execute_cli_remove_cmd(self.management_node,
                                            relevant_url)
                state = self.execute_show_data_cmd(self.management_node,
                                                    relevant_url, 'state')
                self.assertEqual('ForRemoval', state)

        # execute the create_plan command
        self.execute_cli_createplan_cmd(self.management_node)

        # execute the show_plan command and check there exists a task to
        # uninstall the test package using the package deconfigure() method
        # for each link
        stdout, _, _ = self.execute_cli_showplan_cmd(self.management_node)
        for node in nodes:
            lookup_str = '{0}/items{1}'.format(node.split('/')[-1],
                                                self.url)
            self.assertTrue(self.is_text_in_list(lookup_str, stdout),
                'Expected string match \'{0}\' not found in \'{1}\''.format(
                                                                    lookup_str,
                                                                    stdout))
        lookup_str = 'Remove package "{0}"'.format(self.package)
        self.assertTrue(self.is_text_in_list(lookup_str, stdout),
            'Expected string match \'{0}\' not found in \'{1}\''.format(
                                                                    lookup_str,
                                                                    stdout))

        # since there is no remove for the software-item package, there should
        # be no cleanup task for the item
        lookup_str = [relevant_url for relevant_url in self.relevant_urls
                        if '/software' in relevant_url][0]
        self.assertFalse(self.is_text_in_list(lookup_str, stdout),
            'Unexpected string match \'{0}\' found in \'{1}\''.format(
                                                                    lookup_str,
                                                                    stdout))

        # execute the run_plan command and wait for plan completion
        self.execute_cli_runplan_cmd(self.management_node)
        self.assertTrue(self.wait_for_plan_state(self.management_node,
                                                const.PLAN_COMPLETE))

        # check the package links are removed but the package remains under
        # software-item
        expect_err = 'InvalidLocationError'
        for relevant_url in self.relevant_urls:
            if '/software' not in relevant_url:
                _, stderr, _ = self.execute_cli_show_cmd(self.management_node,
                                                        relevant_url,
                                                        expect_positive=False)
                self.assertTrue(self.is_text_in_list(expect_err, stderr),
                    'Expected error message \'{0}\' not found in \'{1}\''.\
                                                                    format(
                                                                    expect_err,
                                                                    stderr))
        package_url = [relevant_url for relevant_url in self.relevant_urls
                        if '/software' in relevant_url][0]
        state = self.execute_show_data_cmd(self.management_node, package_url,
                                            'state')
        self.assertEqual('Applied', state)

    def obs_03_p_remove_multiple_items_confitask_callbactask_notask(self):
        """
        Obsolete - already tested by ATs:
            ERIClitpcore/plan/plan_cleanup_phase.at
        Description:
            Execute the CLI remove command on an item and its links in the
            model, tasks that are created via a plugin (one callback, one
            config and one that generates no tasks at all) and after plan
            execution, the item must be removed and both the links and the
            item itself will not exist in the model

        Steps:
            1.  Execute the remove command on multiple item links in the model
            2.  Items will be marked ForRemoval
            3.  Execute the create_plan command
            4.  Check that the items marked ForRemoval have tasks in the plan
            5.  Execute the run_plan command
            6.  Wait for plan execution completion
            7.  Check that item links are removed but the software item remains
                in the model

        Result:
            Model item and links must be removed from the tree
        """

        # check if the plugin, required for the test, is installed and, if not,
        # install it
        self._install_plugins()

        # create the test items in the model required for the test
        first_item = '{0}_1'.format(self.item)
        properties = '{0} {1}'.format(self.properties[0].format(first_item),
                                     self.properties[1].format('true'))
        self._exec_common_test_methods(self.item_type, properties, uri='_1',
                                      create_plan=False, run_plan=False)
        second_item = '{0}_2'.format(self.item)
        properties = '{0} {1}'.format(self.properties[0].format(second_item),
                                  self.properties[2].format('true'))
        self._exec_common_test_methods(self.item_type, properties, uri='_2',
                                      create_plan=False, run_plan=False)
        third_item = '{0}_3'.format(self.item)
        properties = '{0} {1}'.format(self.properties[0].format(third_item),
                                  self.properties[3].format('true'))
        self._exec_common_test_methods(self.item_type, properties, uri='_3',
                                      create_plan=False, run_plan=False)

        # execute the create_plan command
        self.execute_cli_createplan_cmd(self.management_node)

        # execute the show_plan command and check tasks exist for callback_true
        # and config_true properties but not for no_task_true property
        stdout, _, _ = self.execute_cli_showplan_cmd(self.management_node)
        # check for plan task for callbacktask()
        string_match = 'Apply callback item'
        self.assertTrue(self.is_text_in_list(string_match, stdout),
            'Expected item \'{0}\' not found in stdout: \'{1}\''.format(
                                                                string_match,
                                                                stdout))
        string_match = 'Apply config item'
        # check for plan task for configtask()
        self.assertTrue(self.is_text_in_list(string_match, stdout),
            'Expected item \'{0}\' not found in stdout: \'{1}\''.format(
                                                                string_match,
                                                                stdout))
        # check that the third plugin property, no_task does not have any plan
        # tasks associated with it; it will be set to Applied state after the
        # successful plan run, but it will not actually do anything
        string_match = third_item
        self.assertFalse(self.is_text_in_list(third_item, stdout),
            'Unexpected item \'\' found in stdout: \'{1}\''.format(third_item,
                                                                  stdout))

        # execute the run_plan command and wait for plan to complete
        self.execute_cli_runplan_cmd(self.management_node)
        self.assertTrue(self.wait_for_plan_state(self.management_node,
                                                const.PLAN_COMPLETE))

        # check all the created items are set to Applied state
        for relevant_url in self.relevant_urls:
            state = self.execute_show_data_cmd(self.management_node,
                                              relevant_url, 'state')
            self.assertEqual('Applied', state)

        # remove the software-item and check that the item,including all its
        # links are set to For Removal
        software_item = [relevant_url for relevant_url in self.relevant_urls if
                            '/software' in relevant_url]
        for relevant_url in self.relevant_urls:
            if relevant_url not in software_item:
                self.execute_cli_remove_cmd(self.management_node, relevant_url)
                state = self.execute_show_data_cmd(self.management_node,
                                              relevant_url, 'state')
                self.assertEqual('ForRemoval', state)

        # execute the create_plan command again
        self.execute_cli_createplan_cmd(self.management_node)

        # execute the show_plan command and check tasks exist for callback_true
        # and config_ture but not for no_task_true property; finally check the
        # cleanup phase has a remove item task for all three model item
        # properties in the final cleanup phase
        stdout, _, _ = self.execute_cli_showplan_cmd(self.management_node)
        # get the index of where the final phase begins in the plan output
        final_phase_index = [stdout.index(line) for line in stdout
                            if 'Phase' in line][-1]
        # get the complete final phase of the plan from the complete plan
        # output
        final_phase_list = stdout[final_phase_index:len(stdout)]

        # check callback_true property has a callback task and a cleanup task
        # in cleanup phase
        lookup_str = 'Remove Item'
        self.assertTrue(self.is_text_in_list(lookup_str, stdout),
            'Expected string match \'{0}\' not found in stdout: \'{1}\''.\
                                                    format(lookup_str, stdout))
        lookup_str = '{0}_1'.format(self.url)
        self.assertTrue(self.is_text_in_list(lookup_str, final_phase_list),
            'Expected string match \'{0}\' not found in stdout: \'{1}\''.\
                                                    format(lookup_str,
                                                          final_phase_list))
        # loop through the entire final phase and check if the lookup string is
        # matched and, if found, get the immediate next line and check 'Remove
        # item' is the description
        lookup_next_line = [final_phase_list[final_phase_list.index(line) + 1]
                                for line in final_phase_list
                                    if lookup_str in line][0]
        self.assertTrue(self.is_text_in_list('Remove Item',
                                            [lookup_next_line]),
            'Expected string match \'Remove Item\' not found in \'{0}\''.\
                                                    format(lookup_next_line))

        # check config_true property has a config task and a cleanup task
        # in cleanup phase
        lookup_str = 'Remove Item'
        self.assertTrue(self.is_text_in_list(lookup_str, stdout),
            'Expected string match \'{0}\' not found in stdout: \'{1}\''.\
                                                    format(lookup_str, stdout))
        lookup_str = '{0}_2'.format(self.url)
        self.assertTrue(self.is_text_in_list(lookup_str, final_phase_list),
            'Expected string match \'{0}\' not found in final phase: \'{1}\''.\
                                                    format(lookup_str,
                                                          final_phase_list))

        # check no_task_true property has a cleanup task in cleanup phase and
        # no other task in the plan
        lookup_str = '{0}_3'.format(self.url)
        self.assertTrue(self.is_text_in_list(lookup_str, stdout),
            'Expected string match \'{0}\' not found in stdout: \'{1}\''.\
                                                    format(lookup_str, stdout))
        self.assertTrue(self.is_text_in_list(lookup_str, final_phase_list),
            'Expected string match \'{0}\' not found in final phase: \'{1}\''.\
                                                    format(lookup_str,
                                                          final_phase_list))

        # get all phases except the last phase and check no_task_true property
        # contains no other tasks except in the cleanup phase
        stdout[:] = [line for line in stdout if line not in final_phase_list]
        self.assertFalse(self.is_text_in_list(lookup_str, stdout),
            'Unexpected string match \'{0}\' found in stdout: \'{1}\''.format(
                                                            lookup_str,
                                                            stdout))

        # execute the run_plan command and wait for plan completion
        self.execute_cli_runplan_cmd(self.management_node)
        self.assertTrue(self.wait_for_plan_state(self.management_node,
                                                const.PLAN_COMPLETE))

        for item in software_item:
            self.execute_cli_remove_cmd(self.management_node, item)

        self.execute_cli_createplan_cmd(self.management_node)
        self.execute_cli_runplan_cmd(self.management_node)
        self.assertTrue(self.wait_for_plan_state(self.management_node,
                                                const.PLAN_COMPLETE))

        # check that none of the model items exist in the model tree
        expect_err = 'InvalidLocationError'
        for relevant_url in self.relevant_urls:
            _, stderr, _ = self.execute_cli_show_cmd(self.management_node,
                                                    relevant_url,
                                                    expect_positive=False)
            self.assertTrue(self.is_text_in_list(expect_err, stderr),
                'Expected error message \'{0}\' not found in \'{1}\''.format(
                                                                    expect_err,
                                                                    stderr))
