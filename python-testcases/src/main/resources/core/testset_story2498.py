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
                Epic: N/A
                Story: LITPCDS-2498
                Sub-Task: LITPCDS-2724, LITPCDS-2725, LITPCDS-2726
'''

import test_constants as const
from litp_generic_test import GenericTest
from litp_cli_utils import CLIUtils


class Story2498(GenericTest):
    """
    LITPCDS-2498: As a product designer I want puppet to clean up manifest
    entries relating to removed Model Items, so that the remove case is
    supported.
    """

    def setUp(self):
        """
        Description:
            Runs before every test to perform test set up
        """
        # call super class setup

        super(Story2498, self).setUp()

        # get cluster information

        self.management_node = self.get_management_node_filename()

        # packages to use for the test

        self.package = 'finger'

        # setup required items for test

        self.cli = CLIUtils()

    def tearDown(self):
        """
        Description:
            Runs after every test to perform test tear down/cleanup
        """

        # call super class teardown
        super(Story2498, self).tearDown()

    def _install_package(self):
        """
        Description:
            Install the packages that will be used for the test using litp
        """

        source_paths = list()
        for url in self.find(self.management_node, '/software',
                                    'software-item', rtn_type_children=False):
            source_paths.append('{0}/story_2498'.format(url))
            self.execute_cli_create_cmd(self.management_node,
                                        '{0}/story_2498'.format(url),
                                        'package',
                                        'name=\'{0}\''.format(self.package))

        nodes = self.find(self.management_node, '/', 'ms')
        self.assertNotEqual([], nodes)

        nodes.extend(self.find(self.management_node, '/', 'node'))
        self.assertNotEqual([], nodes)

        for node in nodes:
            for url in self.find(self.management_node, node, 'software-item',
                                                    rtn_type_children=False):
                for url_ in source_paths:
                    self.execute_cli_inherit_cmd(
                        self.management_node,
                        '{0}/story_2498'.format(url),
                        url_
                    )

        self.execute_cli_createplan_cmd(self.management_node)

        self.execute_cli_runplan_cmd(self.management_node)

        self.assertTrue(self.wait_for_plan_state(self.management_node,
                                                const.PLAN_COMPLETE))

    def obsolete_01_p_remove_a_link_to_a_profile_from_a_node(self):
        """
        Obsolete - inherit (link) tested by AT:
            ERIClitpcore/ats/model/inherited/inherit_states.at
        Description:
            Executing the remove command on a node's linked profile, in the
            model, and executing  the create_plan command, will force puppet to
            remove the specific configuration manifest entry for that node,
            while leaving the rest untouched.

        Pre-Requisites:
            1. A running litpd service
            2. An installed and configured cluster

        Steps:
            1. Execute the remove command on a profile linked to a node
            2. Check item state is set to ForRemoval
            3. Execute the create_plan command
            4. Execute the run_plan command
            5. Wait for the plan to complete
            6. Item must be deleted from the model tree and all manifest
               entries related to the item must be removed

        Restore:
            1. If item existed before the test started, restore the link to
               that item
            2. Execute the create_plan command
            3. Wait for the plan to complete and puppet to restore the item

        Results:
            Manifest entries for the specific configuration must be removed
            from the puppet manifests for the specified node
        """

        # try to install the packages

        self._install_package()

        # get all node urls from the model

        nodes = self.find(self.management_node, '/', 'node')
        self.assertNotEqual([], nodes)

        ms_ = self.find(self.management_node, '/', 'ms')
        self.assertNotEqual([], ms_)

        nodes.extend(ms_)

        hostnames = dict()
        for node in nodes:
            stdout, _, _ = self.execute_cli_show_cmd(self.management_node,
                                                node, '-j', load_json=False)
            # get the node hostnames

            hostname = self.cli.get_properties(stdout)['hostname']
            hostnames[node] = hostname

        # filter out the test node to be used

        test_node = nodes[0]

        # for each node and each package check that they exist in the puppet
        # manifests

        for node in nodes:
            stdout, stderr, rcode = self.run_command(self.management_node,
                                        self.rhc.get_grep_file_cmd(
                                        const.PUPPET_MANIFESTS_DIR + \
                                        '{0}.pp'.format(hostnames[node]),
                                        [self.package]))
            self.assertEqual(0, rcode)
            self.assertEqual([], stderr)
            self.assertNotEqual([], stdout)

            self.assertTrue(self.is_text_in_list(self.package, stdout),
            'Package {0} not found in puppet manifests'.format(self.package))

        # get any package linked to a node

        package_url = ''
        for package in self.find(self.management_node, test_node, 'package'):
            stdout, _, _ = self.execute_cli_show_cmd(self.management_node,
                                                    package, '-j',
                                                    load_json=False)

            package_name = self.cli.get_properties(stdout)['name']

            # if the found linked package's name value is equal to the package
            # being used for the test the execute the remove command

            if package_name == self.package:
                package_url = package
                self.execute_cli_remove_cmd(self.management_node, package)

        # for each removed path, chech the state is set to ForRemoval

        stdout, stderr, rcode = self.run_command(self.management_node,
                                    self.cli.get_show_data_value_cmd(
                                        package_url, 'state'))
        self.assertEqual(0, rcode)
        self.assertEqual([], stderr)
        self.assertNotEqual([], stdout)

        self.assertTrue(self.is_text_in_list('ForRemoval', stdout),
        'Expected state not found - stdout: {0}'.format(stdout))

        # execute the create_plan command

        self.execute_cli_createplan_cmd(self.management_node)

        # execute the run_plan command

        self.execute_cli_runplan_cmd(self.management_node)

        # wait for plan to complete

        self.assertTrue(self.wait_for_plan_state(self.management_node,
                                                        const.PLAN_COMPLETE))

        # for each node and package, if the node is the test node, check the
        # packages are removed from its manifest or if not, then that the
        # manifests have been left untouched

        for node in nodes:
            stdout, stderr, rcode = self.run_command(self.management_node,
                                    self.rhc.get_grep_file_cmd(
                                        const.PUPPET_MANIFESTS_DIR + \
                                        '{0}.pp'.format(hostnames[node]),
                                        [self.package]))

            if node == test_node:
                self.assertEqual(1, rcode)
                self.assertEqual([], stderr)
                self.assertEqual([], stdout)

            else:
                self.assertEqual(0, rcode)
                self.assertEqual([], stderr)
                self.assertNotEqual([], stdout)

    def obsolete_02_p_remove_a_profile_linked_to_multiple_nodes(self):
        """
        Obsolete - inherit (link) tested by AT:
            ERIClitpcore/ats/model/inherited/inherit.at
            ERIClitpcore/ats/model/inherited/inherit_states.at
        Description:
            Executing the remove command on a profile linked to multiple nodes,
            in the model, and executing  the create_plan command, will force
            puppet to remove the specific configuration manifest entry for that
            node, while leaving the rest untouched.

        Pre-Requisites:
            1. A running litpd service
            2. An installed and configured cluster

        Steps:
            1. Execute the remove command on a profile linked to multiple nodes
            2. Check item state is set to ForRemoval
            3. Execute the create_plan command
            4. Execute the run_plan command
            5. Wait for the plan to complete
            6. Item must be deleted from the model tree and all manifest
               entries related to the item must be removed

        Restore:
            1. If item existed before the test started, restore the link to
               that item
            2. Execute the create_plan command
            3. Wait for the plan to complete and puppet to restore the item

        Results:
            Manifest entries for the specific configuration must be removed
            from the puppet manifests for the specified node
        """

        # try to install the packages

        self._install_package()

        # get all node urls from the model

        nodes = self.find(self.management_node, '/', 'node')
        self.assertNotEqual([], nodes)

        # filter out the test node to be used

        test_nodes = nodes

        # get all node urls from the model

        ms_ = self.find(self.management_node, '/', 'ms')
        self.assertNotEqual([], ms_)

        nodes.extend(ms_)

        hostnames = dict()
        for node in nodes:
            stdout, _, _ = self.execute_cli_show_cmd(self.management_node,
                                                node, '-j', load_json=False)
            # get the node hostnames

            hostname = self.cli.get_properties(stdout)['hostname']
            hostnames[node] = hostname

        # for each node and each package check that they exist in the puppet
        # manifests

        for node in nodes:
            stdout, stderr, rcode = self.run_command(self.management_node,
                                        self.rhc.get_grep_file_cmd(
                                        const.PUPPET_MANIFESTS_DIR + \
                                        '{0}.pp'.format(hostnames[node]),
                                        [self.package]))
            self.assertEqual(0, rcode)
            self.assertEqual([], stderr)
            self.assertNotEqual([], stdout)

            self.assertTrue(self.is_text_in_list(self.package, stdout),
            'Package {0} not found in puppet manifests'.format(self.package))

        # get any package linked to a node

        package_urls = list()
        for node in test_nodes:
            for package in self.find(self.management_node, node, 'package'):
                stdout, _, _ = self.execute_cli_show_cmd(self.management_node,
                                                        package, '-j',
                                                        load_json=False)

                package_name = self.cli.get_properties(stdout)['name']

                # if the found linked package's name value is equal to the
                # package being used for the test the execute the remove
                # command

                if package_name == self.package:
                    package_urls.append(package)
                    self.execute_cli_remove_cmd(self.management_node, package)

        for package_url in package_urls:

            # for each removed path, chech the state is set to ForRemoval

            stdout, stderr, rcode = self.run_command(self.management_node,
                                        self.cli.get_show_data_value_cmd(
                                            package_url, 'state'))
            self.assertEqual(0, rcode)
            self.assertEqual([], stderr)
            self.assertNotEqual([], stdout)

            self.assertTrue(self.is_text_in_list('ForRemoval', stdout),
            'Expected state not found - stdout: {0}'.format(stdout))

        # execute the create_plan command

        self.execute_cli_createplan_cmd(self.management_node)

        # execute the run_plan command

        self.execute_cli_runplan_cmd(self.management_node)

        # wait for plan to complete

        self.assertTrue(self.wait_for_plan_state(self.management_node,
                                                        const.PLAN_COMPLETE))

        # for each node and package, if the node is the test node, check the
        # packages are removed from its manifest or if not, then that the
        # manifests have been left untouched

        for node in nodes:
            stdout, stderr, rcode = self.run_command(self.management_node,
                                    self.rhc.get_grep_file_cmd(
                                        const.PUPPET_MANIFESTS_DIR + \
                                        '{0}.pp'.format(hostnames[node]),
                                        [self.package]))

            if node in test_nodes:
                self.assertEqual(1, rcode)
                self.assertEqual([], stderr)
                self.assertEqual([], stdout)

            else:
                self.assertEqual(0, rcode)
                self.assertEqual([], stderr)
                self.assertNotEqual([], stdout)

    def obsolete_03_p_remove_a_link_from_ms(self):
        """
        Obsolete - redundant; inherit (link) tested by AT:
            ERIClitpcore/ats/model/inherited/inherit.at
            ERIClitpcore/ats/model/inherited/inherit_states.at
        Description:
        Description:
            Executing the remove command on a profile linked to /ms, in the
            model, and executing  the create_plan command, will force puppet to
            remove the specific configuration manifest entry for that node,
            while leaving the rest untouched.

        Pre-Requisites:
            1. A running litpd service
            2. An installed and configured cluster

        Steps:
            1. Execute the remove command on a profile linked to /ms
            2. Check item state is set to ForRemoval
            3. Execute the create_plan command
            4. Execute the run_plan command
            5. Wait for the plan to complete
            6. Item must be deleted from the model tree and all manifest
               entries related to the item must be removed

        Restore:
            1. If item existed before the test started, restore the link to
               that item
            2. Execute the create_plan command
            3. Wait for the plan to complete and puppet to restore the item

        Results:
            Manifest entries for the specific configuration must be removed
            from the puppet manifests for the specified node
        """

        # try to install the packages

        self._install_package()

        # get all node urls from the model

        nodes = self.find(self.management_node, '/', 'node')
        self.assertNotEqual([], nodes)

        ms_ = self.find(self.management_node, '/', 'ms')
        self.assertNotEqual([], ms_)

        # filter out the test node to be used

        test_node = ms_[0]

        nodes.extend(ms_)

        hostnames = dict()
        for node in nodes:
            stdout, _, _ = self.execute_cli_show_cmd(self.management_node,
                                                node, '-j', load_json=False)
            # get the node hostnames

            hostname = self.cli.get_properties(stdout)['hostname']
            hostnames[node] = hostname

        # for each node and each package check that they exist in the puppet
        # manifests

        for node in nodes:
            stdout, stderr, rcode = self.run_command(self.management_node,
                                        self.rhc.get_grep_file_cmd(
                                        const.PUPPET_MANIFESTS_DIR + \
                                        '{0}.pp'.format(hostnames[node]),
                                        [self.package]))
            self.assertEqual(0, rcode)
            self.assertEqual([], stderr)
            self.assertNotEqual([], stdout)

            self.assertTrue(self.is_text_in_list(self.package, stdout),
            'Package {0} not found in puppet manifests'.format(self.package))

        # get any package linked to a node

        package_url = ''
        for package in self.find(self.management_node, test_node, 'package'):
            stdout, _, _ = self.execute_cli_show_cmd(self.management_node,
                                                    package, '-j',
                                                    load_json=False)

            package_name = self.cli.get_properties(stdout)['name']

            # if the found linked package's name value is equal to the
            # package being used for the test the execute the remove
            # command

            if package_name == self.package:
                package_url = package
                self.execute_cli_remove_cmd(self.management_node, package)

        # for each removed path, chech the state is set to ForRemoval

        stdout, stderr, rcode = self.run_command(self.management_node,
                                    self.cli.get_show_data_value_cmd(
                                        package_url, 'state'))
        self.assertEqual(0, rcode)
        self.assertEqual([], stderr)
        self.assertNotEqual([], stdout)

        self.assertTrue(self.is_text_in_list('ForRemoval', stdout),
        'Expected state not found - stdout: {0}'.format(stdout))

        # execute the create_plan command

        self.execute_cli_createplan_cmd(self.management_node)

        # execute the run_plan command

        self.execute_cli_runplan_cmd(self.management_node)

        # wait for plan to complete

        self.assertTrue(self.wait_for_plan_state(self.management_node,
                                                        const.PLAN_COMPLETE))

        # for each node and package, if the node is the test node, check the
        # packages are removed from its manifest or if not, then that the
        # manifests have been left untouched

        for node in nodes:
            stdout, stderr, rcode = self.run_command(self.management_node,
                                    self.rhc.get_grep_file_cmd(
                                        const.PUPPET_MANIFESTS_DIR + \
                                        '{0}.pp'.format(hostnames[node]),
                                        [self.package]))

            if node == test_node:
                self.assertEqual(1, rcode)
                self.assertEqual([], stderr)
                self.assertEqual([], stdout)

            else:
                self.assertEqual(0, rcode)
                self.assertEqual([], stderr)
                self.assertNotEqual([], stdout)

    def obsolete_04_p_remove_a_child_item_of_a_profile(self):
        """
        Obsolete - redundant; inherit (link) tested by AT:
            ERIClitpcore/ats/model/inherited/inherit.at
            ERIClitpcore/ats/model/inherited/inherit_states.at
        Description:
            Executing the remove command on a child item of a profile linked to
            a node, in the model, and executing  the create_plan command, will
            force puppet to remove the specific configuration manifest entry
            for that node, while leaving the rest untouched.

        Pre-Requisites:
            1. A running litpd service
            2. An installed and configured cluster

        Steps:
            1. Execute the remove command on a child item of a linked profile
            2. Check item state is set to ForRemoval
            3. Execute the create_plan command
            4. Execute the run_plan command
            5. Wait for the plan to complete
            6. Item must be deleted from the model tree and all manifest
               entries related to the item must be removed

        Restore:
            1. If item existed before the test started, restore the link to
               that item
            2. Execute the create_plan command
            3. Wait for the plan to complete and puppet to restore the item

        Results:
            Manifest entries for the specific configuration must be removed
            from the puppet manifests for the specified node
        """

        # Commented Obsolete test case and replace with pass statement
        pass

#        # try to install the packages
#
#        self._install_package()
#
#        # get all node urls from the model
#
#        nodes = self.find(self.management_node, '/', 'node')
#        self.assertNotEqual([], nodes)
#
#        ms_ = self.find(self.management_node, '/', 'ms')
#        self.assertNotEqual([], ms_)
#
#        hostnames = dict()
#        for node in nodes:
#            stdout, _, _ = self.execute_cli_show_cmd(self.management_node,
#                                                node, '-j', load_json=False)
#            # get the node hostnames
#
#            hostname = self.cli.get_properties(stdout)['hostname']
#            hostnames[node] = hostname
#
#        # for each node and each package check that they exist in the puppet
#        # manifests
#
#        for node in nodes:
#            stdout, stderr, rcode = self.run_command(self.management_node,
#                                        self.rhc.get_grep_file_cmd(
#                                        const.PUPPET_MANIFESTS_DIR + \
#                                        '{0}.pp'.format(hostnames[node]),
#                                        [self.package]))
#            self.assertEqual(0, rcode)
#            self.assertEqual([], stderr)
#            self.assertNotEqual([], stdout)
#
#            self.assertTrue(self.is_text_in_list(self.package, stdout),
#            'Package {0} not found in puppet manifests'.format(self.package))
#
#        # get all node urls from the model
#
#        nodes = self.find(self.management_node, '/', 'node')
#        self.assertNotEqual([], nodes)
#
#        ms_ = self.find(self.management_node, '/', 'ms')
#        self.assertNotEqual([], ms_)
#
#        # for each path ,remove was executed on, check the state is now set to
#        # ForRemoval on its links under nodes also
#
#        for node in nodes:
#            for package in self.find(self.management_node, node, 'package'):
#                stdout, _, _ = self.execute_cli_show_cmd(self.management_node,
#                                                         package, '-j',
#                                                         load_json=False)
#                self.assertEqual(0, rcode)
#                self.assertEqual([], stderr)
#                self.assertNotEqual([], stdout)
#
#                package_name = self.cli.get_properties(stdout)['name']
#
#                if package_name == self.package:
#
#                    self.execute_cli_remove_cmd(self.management_node, package)
#
#                    # if the found linked package's name value is equal to the
#                    # package being used for the test the execute the remove
#                    # command
#
#                    stdout, stderr, rcode = \
#                        self.run_command(self.management_node,
#                                         self.cli.get_show_data_value_cmd(
#                                        package, 'state'))
#                    self.assertEqual(0, rcode)
#                    self.assertEqual([], stderr)
#                    self.assertNotEqual([], stdout)
#
#                    self.assertTrue(self.is_text_in_list('ForRemoval', \
#                    stdout), 'Expected state not found - stdout: {0}' \
#                    .format(stdout))
#
#        # execute the create_plan command
#
#        self.execute_cli_createplan_cmd(self.management_node)
#
#        # execute the run_plan command
#
#        self.execute_cli_runplan_cmd(self.management_node)
#
#        # wait for the plan to complete
#
#        self.assertTrue(self.wait_for_plan_state(self.management_node,
#                                                 const.PLAN_COMPLETE))
#
#        # for each node in the model, execute show command, get hostname and
#        # check that the packages are no longer in the puppet manifests for
#        # specified node
#
#        for node in nodes:
#            stdout, stderr, rcode = self.run_command(self.management_node,
#                                    self.rhc.get_grep_file_cmd(
#                                    const.PUPPET_MANIFESTS_DIR + \
#                                        '{0}.pp'.format(hostnames[node]),
#                                    [package]))
#            self.assertEqual(1, rcode)
#            self.assertEqual([], stderr)
#            self.assertEqual([], stdout)
