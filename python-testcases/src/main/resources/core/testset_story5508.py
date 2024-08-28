'''
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     October 2014
@author:    Ares
@summary:   Integration test for LITPCDS-5508
            Agile:
                Epic: N/A
                Story: N/A
                Sub-Task: N/A
'''

import os
import test_constants
from litp_generic_test import GenericTest
from litp_cli_utils import CLIUtils
from redhat_cmd_utils import RHCmdUtils


class Story5508(GenericTest):
    """
    LITPCDS-5508:
    As a plugin developer I want core functionality to generate puppet
    manifests from config tasks using property values that are updated during
    the running plan.
    """

    def setUp(self):
        """runs before every test to perform required setup"""
        # call super class setup
        super(Story5508, self).setUp()
        self.management_node = self.get_management_node_filename()
        self.ms_ip_address = self.get_node_att(self.management_node, 'ipv4')
        self.cli = CLIUtils()
        self.rhc = RHCmdUtils()
        self.item_type = 'story5508'
        self.manifests_dir = test_constants.PUPPET_MANIFESTS_DIR
        self.log_path = test_constants.GEN_SYSTEM_LOG_PATH
        self.callback = 'CallbackTask{0}()'
        self.config = 'ConfigTask{0}()'

    def tearDown(self):
        """runs after every test to perform required cleanup/teardown"""

        # call super class teardown
        super(Story5508, self).tearDown()

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

    def _check_item_type_registered(self):
        """check model item type extension registered with litp"""

        expected_match = [
            'INFO: Added ModelExtension: \\"{0}'.format(self.item_type),
            'INFO: Added Plugin: \\"{0}'.format(self.item_type)
        ]

        stdout, stderr, rcode = self.run_command(
            self.management_node,
            self.rhc.get_grep_file_cmd(self.log_path, expected_match)
        )
        self.assertEqual(0, rcode)
        self.assertNotEqual([], stdout)
        self.assertEqual([], stderr)

    def _install_rpms(self):
        """
        check if a plugin/extension rpm is installed and if not, install it
        """

        # since the copy_and_install_rpms method in the framework, doesn't
        # check if the package is already installed, we must check if the
        # package does indeed need to be installed - if we don't, and the
        # package is installed, the test will fail
        _, _, rcode = self.run_command(
            self.management_node,
            self.rhc.check_pkg_installed([self.item_type]),
            su_root=True
        )

        if rcode == 1:
            # copy over and install RPMs
            local_rpm_paths = self.get_local_rpm_paths(
                os.path.abspath(
                    os.path.join(os.path.dirname(__file__), 'plugins')
                ),
                self.item_type
            )

            self.assertTrue(
                self.copy_and_install_rpms(
                    self.management_node, local_rpm_paths
                )
            )
            self._check_item_type_registered()

    def _get_nodes_from_model(self, include_ms=False):
        """get all nodes from the litp model"""

        nodes = self.find(self.management_node, '/deployments', 'node')
        if include_ms:
            nodes.append('/ms')
        return nodes

    def _get_hostname_from_node_url(self, node):
        """get the node hostname from the node url"""

        return self.execute_show_data_cmd(
            self.management_node,
            node,
            'hostname'
        )

    def _get_relevant_task_from_plan(self, stdout, lookup, node):
        """get the relevant task from the plan output"""

        r_phase = -1
        r_task = -1
        r_task_desc = ''
        plan_d = self.cli.parse_plan_output(stdout)
        for phase in plan_d.keys():
            for task in plan_d[phase].keys():
                task_desc = self.cli.get_task_desc(stdout, phase, task)
                if self.is_text_in_list(lookup, task_desc) and \
                    self.is_text_in_list(node.split('/')[-1], task_desc):
                    r_phase = phase
                    r_task = task
                    r_task_desc = task_desc
        return r_phase, r_task, r_task_desc

    def _get_task_state_from_plan(self, r_phase, r_task):
        """get the relevant task state"""

        stdout, _, _ = self.execute_cli_showplan_cmd(self.management_node)
        return self.cli.get_task_status(stdout, r_phase, r_task)

    def _create_model_item(self, test_name):
        """create test model items"""

        sw_items_url = self.find(
            self.management_node,
            '/software',
            'software-item',
            False
        )[0]
        mdelitem_url = os.path.join(sw_items_url, self.item_type)
        self.execute_cli_create_cmd(
            self.management_node,
            mdelitem_url,
            self.item_type,
            'name=\'{0}{1}\''.format(self.item_type, test_name)
        )
        return mdelitem_url

    def _reference_model_item(self, mdelitem_url, include_ms=False):
        """create the test model item references"""

        nodes = self._get_nodes_from_model(include_ms)
        for node in nodes:
            node_sw_items_url = self.find(
                self.management_node,
                node,
                'software-item',
                False
            )[0]
            self.execute_cli_inherit_cmd(
                self.management_node,
                os.path.join(node_sw_items_url, self.item_type),
                mdelitem_url
            )
        return nodes

    def _get_relevant_tasks_per_node(self, nodes, stdout, callback, config):
        """
        get each relevant task index and description associated to node in a
        dict
        """

        node_tasks = dict()
        for node in nodes:
            callback_r = self._get_relevant_task_from_plan(
                stdout,
                callback,
                node
            )
            config_r = self._get_relevant_task_from_plan(
                stdout,
                config,
                node
            )
            hostname = self._get_hostname_from_node_url(node)
            node_tasks[node] = dict()
            node_tasks[node][hostname] = list()
            node_tasks[node][hostname].append(callback_r)
            node_tasks[node][hostname].append(config_r)
        return node_tasks

    def _check_property_updated(self, node, expected, proprty):
        """check the expected property was updated by the plugin"""

        mdelitm_url = self.find(self.management_node, node, self.item_type)[0]
        result = self.execute_show_data_cmd(
            self.management_node,
            mdelitm_url,
            proprty
        )
        self.assertEqual(expected, result.split(' ')[0])

    def _check_manifest_contents(self, hostname, test_name):
        """check the generated configuration in the manifests"""

        stdout, stderr, rcode = self.run_command(
            self.management_node,
            self.rhc.get_grep_file_cmd(
                os.path.join(self.manifests_dir, '{0}.pp'.format(hostname)),
                ['{0}{1}'.format(self.item_type, test_name)]
            )
        )
        self.assertEqual(0, rcode)
        self.assertEqual([], stderr)
        self.assertNotEqual([], stdout)

    def _do_checks(self, task, node, hostname, callback, config, test_name,
                    expected):
        """perform the checks required for the test"""

        task_state = self._get_task_state_from_plan(task[0], task[1])
        while task_state == 'Running':
            task_state = self._get_task_state_from_plan(task[0], task[1])
            if self.wait_for_plan_state(self.management_node,
                    test_constants.PLAN_FAILED):
                assert False
            if self.is_text_in_list(callback, task[2]):
                self._check_property_updated(
                    node,
                    expected,
                    'ensure'
                )
            elif self.is_text_in_list(config, task[2]):
                self._check_manifest_contents(hostname, test_name)

    def _do_checks_while_plan_running(self, node_tasks, callback, config,
                                    test_name, expected):
        """perform the checks while the plan is in a Running state"""

        while self.wait_for_plan_state(self.management_node,
                test_constants.PLAN_IN_PROGRESS):
            for node in node_tasks.keys():
                for hostname in node_tasks[node].keys():
                    for task in node_tasks[node][hostname]:
                        self._do_checks(
                            task,
                            node,
                            hostname,
                            callback,
                            config,
                            test_name,
                            expected
                        )

    # @attr('all', 'non-revert', '5508')
    def obsolete_01_p_update_property_check_manifests(self):
        """
        Obsoleted:
        replaced with AT:
        ERIClitpcore/ats/plan/future_property_value/\
            update_property_check_manifests.at

        Test Description
        Given a running plan, if a property value is updated, prior to the
        ConfigTask()'s execution, during the plan execution, then the task's
        properties will reflect the update.

        Pre-Requisites
         A running litpd service
         An installed test item type extension/plugin

        Risks
         Once an item type extension is installed and registered with the litpd
         service, it cannot be removed
         Once a plugin is installed, it cannot be removed

        Pre-Test Steps
        1.  Create a new item type extension as described in the LITP 2 SDK
        2.  Create a new plugin as described in the LITP 2 SDK
        3.  Edit the item type extension to have a plugin updatable property
            with a default value
        4.  Edit the plugin to have a CallbackTask() to update the plugin
            updatable property value
        5.  Edit the plugin to have a ConfigTask() to make use of the property
            value
        6.  Build and install the extension package
        7.  Build and install the plugin package

        Steps
        1.  Execute the create command to create a model item
        2.  Execute the create_plan command
        3.  Check the property's default value
        4.  Execute the run_plan command
        5.  Check that the CallbackTask() updates the property's value
        6.  Wait for plan execution to complete successfully
        7.  Check puppet manifests show the updated property value

        Restore
        1.  Execute the remove command on the created model item
        2.  Execute the create_plan command
        3.  Execute the run_plan command
        4.  Wait for plan execution to complete succesfully
        5.  Check model item is removed from the model

        Expected Result
        The puppet manifests generated from the ConfigTask(), during the plan
        execution, will reflect the property's updated value.
        """

        self._install_rpms()
        callback = self.callback.format('')
        config = self.config.format('')
        mdelitem_url = self._create_model_item('test01')
        nodes = self._reference_model_item(mdelitem_url)
        self.execute_cli_createplan_cmd(self.management_node)
        stdout, _, _ = self.execute_cli_showplan_cmd(self.management_node)
        node_tasks = self._get_relevant_tasks_per_node(
            nodes,
            stdout,
            callback,
            config
        )
        self.execute_cli_runplan_cmd(self.management_node)
        self._do_checks_while_plan_running(
            node_tasks,
            callback,
            config,
            'test01',
            'present'
        )

    # @attr('all', 'non-revert', '5508')
    def obsolete_02_p_update_property_multiple_check_manifests(self):
        """
        Obsoleted:
        replaced with AT:
        ERIClitpcore/ats/plan/future_property_value/\
            update_property_multiple_check_manifests.at

        Test Description
        Given a running plan, if a property value is updated, prior to the
        ConfigTask() execution, during the plan execution, then updated again
        after the ConfigTask()'s execution, the task's properties will reflect
        the first update.

        Pre-Requisites
         A running litpd service
         An installed test item type extension/plugin

        Risks
         Once an item type extension is installed and registered with the litpd
         service, it cannot be removed
         Once a plugin is installed, it cannot be removed

        Pre-Test Steps
        1.  Create a new item type extension as described in the LITP 2 SDK
        2.  Create a new plugin as described in the LITP 2 SDK
        3.  Edit the item type extension to have a plugin updatable property
            with a default value
        4.  Edit the plugin to have a CallbackTask() to update the plugin
            updatable property value
        5.  Edit the plugin to have a ConfigTask() to make use of the property
            value
        6.  Build and install the extension package
        7.  Build and install the plugin package

        Steps
        1.  Execute the create command to create a model item
        2.  Execute the create_plan command
        3.  Check the property's default value
        4.  Execute the run_plan command
        5.  Check that the CallbackTask() updates the property's value
        6.  Wait for Configtask() to complete successfully
        7.  Check the generated manifest configuration uses the property's
            updated value
        8.  Check that another CallbackTask() updates the property's value a
            second time
        9.  Wait for second Configtask() to complete successfully
        10. Check the generated manifest second configuration uses the
            property's updated value
        11. Check the generated manifest first configuration remains unchanged
        12. Wait for plan execution to complete successfully

        Restore
        1.  Execute the remove command on the created model item
        2.  Execute the create_plan command
        3.  Execute the run_plan command
        4.  Wait for plan execution to complete succesfully
        5.  Check model item is removed from the model

        Expected Result
        The puppet manifests generated from the ConfigTask(), during the plan
        execution, will reflect the property's values as updated by the
        previous CallbackTask().
        """

        self._install_rpms()
        callback = self.callback.format('')
        config = self.config.format('')
        callback2 = self.callback.format('2')
        config2 = self.config.format('2')
        mdelitem_url = self._create_model_item('test02')
        nodes = self._reference_model_item(mdelitem_url)
        self.execute_cli_createplan_cmd(self.management_node)
        stdout, _, _ = self.execute_cli_showplan_cmd(self.management_node)
        node_tasks = self._get_relevant_tasks_per_node(
            [nodes[0]],
            stdout,
            callback,
            config
        )
        node_tasks2 = self._get_relevant_tasks_per_node(
            [nodes[0]],
            stdout,
            callback2,
            config2
        )
        self.execute_cli_runplan_cmd(self.management_node)
        self._do_checks_while_plan_running(
            node_tasks,
            callback,
            config,
            'test02',
            'present'
        )
        self._do_checks_while_plan_running(
            node_tasks2,
            callback2,
            config2,
            'test02',
            'absent'
        )

    # @attr('all', 'non-revert', '5508')
    def obsolete_03_p_no_property_update_check_manifests(self):
        """
        Obsoleted:
        replaced with AT:
        ERIClitpcore/ats/plan/future_property_value/\
            no_update_property_check_manifests.at

        Test Description
        Given a running plan, if no property value is updated during the plan
        execution, prior to the ConfigTask(), then the ConfigTask() will use
        the property value from the model.

        Pre-Requisites
         A running litpd service
         An installed test item type extension/plugin

        Risks
         Once an item type extension is installed and registered with the litpd
         service, it cannot be removed
         Once a plugin is installed, it cannot be removed

        Pre-Test Steps
        1.  Create a new item type extension as described in the LITP 2 SDK
        2.  Create a new plugin as described in the LITP 2 SDK
        3.  Edit the item type extension to have a plugin updatable property
            with a default value
        4.  Edit the plugin to have a ConfigTask() to make use of the property
            value
        5.  Build and install the extension package
        6.  Build and install the plugin package

        Steps
        1.  Execute the create command to create a model item
        2.  Execute the create_plan command
        3.  Check the property's default value
        4.  Execute the run_plan command
        5.  Wait for plan execution to complete successfully
        6.  Check puppet manifests show the same default property value defined
            on the model item

        Restore
        1.  Execute the remove command on the created model item
        2.  Execute the create_plan command
        3.  Execute the run_plan command
        4.  Wait for plan execution to complete succesfully
        5.  Check model item is removed from the model

        Expected Result
        The puppet manifests generated from the ConfigTask(), during the plan
        execution, will reflect the property's value in the model, since no
        CallbackTask() updated it beforehand.
        """

        self._install_rpms()
        callback = self.callback.format('')
        config = self.config.format('')
        mdelitem_url = self._create_model_item('test03')
        nodes = self._reference_model_item(mdelitem_url, include_ms=True)
        self.execute_cli_createplan_cmd(self.management_node)
        stdout, _, _ = self.execute_cli_showplan_cmd(self.management_node)
        node_tasks = self._get_relevant_tasks_per_node(
            nodes,
            stdout,
            callback,
            config
        )
        self.execute_cli_runplan_cmd(self.management_node)
        self._do_checks_while_plan_running(
            node_tasks,
            callback,
            config,
            'test03',
            'absent'
        )
