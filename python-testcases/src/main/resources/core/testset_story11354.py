"""
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     August  2015
@author:    Maurizio
@summary:   Integration test for LITPCDS-11354
            This story is based on LITPCDS-10593 and LITPCDS-6067
            As a LITP user, in a disaster recovery situation
            I want prepare_restore to ensure the last applied plan is restored
            so that I can ensure the integrity of my restore.

            With this story "prepare_restore" will first call reload_model
            to reset any updated model items to their applied state and remove
            any newly created ones before being set back to "Initial" state.

            Bug TORF-109265
            We are now expecting to be able to successfully issue
            "create_snapshot" command immediately after getting the  prompt
            back from "prepare_restore"

            Bug TORF-113860
            MS replacement scenario not contemplated when developing
            prepare_restore.
            prepare_restore must leave puppet service untouched

            Bug TORF-114663
            Task order incorrect in plan created after prepare_restore and
            update to an MS network interface
"""

from litp_generic_test import GenericTest, attr
from storage_utils import StorageUtils
from third_pp_utils import ThirdPPUtils
import test_constants as const
import time


class Story11354(GenericTest):
    """
    Implementation of tests for story11354
    """

    def setUp(self):
        """runs before every test to perform required setup"""
        super(Story11354, self).setUp()
        self.ms1 = self.get_management_node_filename()
        self.mn_nodes = self.get_managed_node_filenames()
        self.story_id = '11354'
        self.ms1_pp_file = \
            '{0}{1}.pp'.format(const.PUPPET_MANIFESTS_DIR, self.ms1)
        self.storage = StorageUtils()
        self.third_pp = ThirdPPUtils()
        self.skip_cleanup = False
        self.logging_url = "/litp/logging"

    def tearDown(self):
        """runs after every test to perform required cleanup/teardown"""
        if not self.skip_cleanup:
            super(Story11354, self).tearDown()

    def _check_item_state(self, state, paths):
        """
        Description:
            Check that all items under given paths are in the specified state
        Args:
            state (str): Expected item state
            paths (list): Paths to check
        """
        for path in paths:
            self.assertTrue(
                self.is_expected_state(self.ms1, path=path, state=state),
                'Found at least one item under "{0}" not in {1} state'
                .format(path, state))

    def _check_all_defined_items_state_is_correct(self, litp_items):
        """
        Description:
            Determine which items of a given list are in an unexpected state.
            This verification is done by comparing values specified in the
            items definition at the beginning of the test with values
            obtained by inspecting the LITP model.

        Args:
            litp_items (list): List of items to inspect
        Return:
            list, Description of items found in an unexpected state

        litp_items structure example:
            [
                {
                    'description': 'test updated item on MS',
                    'props': 'name=655 fw_rule01',
                    'item_id': '11354_fw_rule01',
                    ...
                    'transition_to': 'ForRemoval' # This is the expected state
                },
            ]
        """
        unexpected_state_items = []
        for each_item in litp_items:
            state = self.get_item_state(self.ms1, each_item['url'])
            if each_item['transition_to'] == 'Update_and_Remove':
                expected_state = 'ForRemoval'
            else:
                expected_state = each_item['transition_to']

            if expected_state == state:
                self.log('info', '[OK]    Item: "{0}" - State: "{1}"'
                                 .format(each_item['url'], state))
            else:
                msg = ('[ERROR] Item: "{0}" - State: "{1}"'
                        .format(each_item['url'], state))
                self.log('info', msg)
                unexpected_state_items.append(msg)
        return unexpected_state_items

    def _resize_snapshot(self, size, file_system_name='root'):
        """
        Description
            Change "snap_size" property value of a given file system.

        args:
            size (int): The size of the snapshot volume (in % of max size)
            file_system_name (str): The name of the file system to change
                                    "snap_size" property value on
        """
        file_systems = self.find(self.ms1, '/infrastructure', 'file-system')
        root_file_system_url = ''
        for file_system in file_systems:
            if file_system.endswith(file_system_name):
                root_file_system_url = file_system
                break

        self.assertNotEqual(root_file_system_url, '',
            'No "root" file system found on LITP model')

        self.backup_path_props(self.ms1, root_file_system_url)

        self.execute_cli_update_cmd(self.ms1, root_file_system_url,
            'snap_size={0}'.format(size))

    def _create_snapshot(self, snapshot_names):
        """
        Description:
            Create snapshots and wait for plan to complete
        Args:
            snapshot_name (list): The list of snapshots to create
        """
        for snapshot in snapshot_names:
            self.execute_cli_createsnapshot_cmd(
                self.ms1, '-n {0}'.format(snapshot))
            self.assertTrue(
                self.wait_for_plan_state(
                    self.ms1, const.PLAN_COMPLETE),
                    'Plan to create snapshot "{0}" failed'.format(snapshot))

    def _check_snapshot_item_is_present(self, snapshot_names):
        """
        Description:
            Check that given snapshots are on litp model
        Args:
            snapshot_names (list): The list of snapshot items to check
        """
        snapshot_paths = self.find(self.ms1, '/snapshots', 'snapshot-base',
                                   assert_not_empty=True, find_refs=True)
        for snapshot in snapshot_names:
            snapshot_items = [x.split('/')[-1] for x in snapshot_paths]
            self.assertTrue(snapshot in snapshot_items,
                'Snapshot "{0}"" not found on litp model.'.format(snapshot))

    def _check_puppet_files_have_been_cleaned(self):
        """
        Description:
            - Check that puppet cert folder contains only the "ms1.pp" file
            - Check that puppet certificate for all peer nodes were removed
        """
        dir_contents = self.list_dir_contents(self.ms1,
                                        const.PUPPET_MANIFESTS_DIR)

        self.log('info',
            'Check that {0} contains only the "ms1.pp" file'
            .format(const.PUPPET_MANIFESTS_DIR))
        self.assertEqual(1, len(dir_contents),
            '\nExtra files found on {0}\n{1}'
            .format(const.PUPPET_MANIFESTS_DIR, dir_contents))

        self.assertTrue(self.remote_path_exists(self.ms1, self.ms1_pp_file),
            'File "{0}" not found on MS after running "prepare_restore"'
            .format(self.ms1_pp_file))

        self.log('info',
            'Check that puppet certificate for all peer nodes were removed')
        cmd = self.third_pp.get_puppet_cert_list_cmd(args='--all')
        puppet_certs = self.run_command(self.ms1, cmd,
                                        default_asserts=True, su_root=True)[0]
        error = False
        for line in puppet_certs:
            if line.startswith('+ "{0}"'.format(self.ms1)):
                continue
            else:
                error = True
                break

        self.assertFalse(error,
            '\nFound node puppet certs still on system after "prepare_restore"'
            '\n{0}'.format('\n'.join(puppet_certs)))

    def _get_node_url(self, node_type, node_index):
        """
        Description
            Determine node url of node to be used during test
        Args:
            node_index (int): node to look for
            node_type  (str): specify whether it is a peer node or MS
        Return:
            str, The url of the required "node" item
        """
        node_urls = self.find(self.ms1, '/', node_type)
        self.assertTrue(len(node_urls) >= node_index,
            'Invalid node index "{0}" was requested. Valid index range is '
            '"0" to "{1}"'
            .format(node_index, len(node_urls) - 1))
        return node_urls[node_index]

    def _create_node_firewall_rule_item(self, node_url, item_id, props):
        """
        Description:
            Create new item of type firwall-rule on a specified node
        Args:
            node_url (str): vpath to node
            item_id  (str): The id of the new item
            props    (str): Item properties
        Return:
            str, The url of the item just created
        """
        firewall_node_config_url = self.find(self.ms1,
                                        node_url, 'firewall-node-config')[0]
        rule_url = '{0}/rules/{1}'.format(firewall_node_config_url, item_id)

        self.execute_cli_create_cmd(self.ms1,
                    rule_url, 'firewall-rule', props, load_json=False)

        # Show configuration of the newly created item
        self.get_props_from_url(self.ms1, rule_url)

        return rule_url

    def _create_logrotate_rule_item(self, node_url, item_id, props):
        """
        Description:
            Create new item of type logrotate-rule on a specified node
        Args:
            node_url      (str): vpath to node
            item_id       (str): The id of the new item
            props         (str): Item properties
        Return:
            str, The url of the item just created
        """
        logrotate_rule_config_urls = self.find(self.ms1,
            node_url, 'logrotate-rule-config', assert_not_empty=False)

        if len(logrotate_rule_config_urls) == 0:
            coll_of_node_config_urls = self.find(
                self.ms1, node_url, 'collection-of-node-config')
            logrotate_rule_config_url = ('{0}/logrotate'.
                                         format(coll_of_node_config_urls[0]))
            self.execute_cli_create_cmd(self.ms1,
                                        logrotate_rule_config_url,
                                        'logrotate-rule-config')
        else:
            logrotate_rule_config_url = logrotate_rule_config_urls[0]

        rule_url = '{0}/rules/{1}'.format(logrotate_rule_config_url, item_id)

        self.execute_cli_create_cmd(self.ms1,
                        rule_url, 'logrotate-rule', props, load_json=False)

        # Show configuration of the newly created item
        self.get_props_from_url(self.ms1, rule_url)

        return rule_url

    def _power_down_peer_nodes(self, nodes):
        """
        Description:
            Issue a shutdown command on peer nodes and wait until they are
            all offline
        Args:
            nodes (list) : list of nodes to power down
        Return:
            bool, True is power down was successful, otherwise false
        """
        self.log('info', "Powering down nodes {0}".format(nodes))
        cmd = "(sleep 1; {0} -h now) &".format(const.SHUTDOWN_PATH)
        for node in nodes:
            self.run_command(node, cmd, su_root=True)

        running_nodes = nodes[:]
        timeout = 120
        self.log('info', "Waiting for peer nodes to power down")
        while running_nodes != []:
            for node in running_nodes[:]:
                if self.is_ip_pingable(self.ms1, node) is False:
                    running_nodes.remove(node)

            time.sleep(1)
            timeout -= 1

            if len(running_nodes) > 0:
                self.log('info',
                         'Nodes "{0}" still running. Time left {1}s'
                         .format(running_nodes, timeout))
            if timeout == 0:
                return False
        self.log('info', 'Nodes "{0}" are now powered down'.
                          format(', '.join(nodes)))
        return True

    def _get_changed_properties(self, items):
        """
        Description:
            Compare initial value of properties of each item of a given list
            with their current values to determine if changed have occurred.
            If the item is marked as "transition_to" Initial, then we expect
            it to have been removed from the model.
        Args:
            items (list): Items to check property values on
        Return:
            list, list, List of items with changed property values,
                        List of items with new properties

        items structure example:
            [
                {
                    'description': 'test updated item on MS',
                    'props': 'name=655 fw_rule01',
                    'item_id': '11354_fw_rule01',
                    ...
                    'transition_to': 'ForRemoval' # This is the expected state
                },
            ]
        """
        for each_item in items:
            if each_item['transition_to'] == 'Initial':
                self.execute_cli_show_cmd(
                    self.ms1,
                    each_item['url'],
                    expect_positive=False)
            else:
                props = self.get_props_from_url(self.ms1,
                                                each_item['url'])

                changed_props, new_props = self.get_changed_props(
                    props, each_item['props_before'])

        return changed_props, new_props

    def _soft_poweroff_node(self, node):
        """
        Will perform a soft poweroff of a peer node.
        First check if the node is reachable

        Args:
           node (str): The peer node(filename) you wish to soft poweroff.

        Raises:
          AssertionError. If poweroff command returns an error or if
          node is still pingable after hard power off.
        """
        cmd = "(sleep 1; {0} -h now) &".format(const.SHUTDOWN_PATH)
        node_ip = self.get_node_att(node, 'ipv4')

        self.stop_service(node, 'puppet')

        self.run_command(node, cmd, su_root=True, default_asserts=True)
        self.log('info', 'Checking node is down')

        self.assertTrue(self.wait_for_ping(node_ip, False, timeout_mins=2),
                        "Node '{0} has not gone down".format(node_ip))

    def _create_package_inheritance(self, node_url, package_name, package_url):
        """
        Description:
            Create package inheritance on the test node.
        Args:
            node_url (str): node url
            package_name (str): package name
            package_url (str): package software url
        Actions:
            1. Create package inheritance using CLI.
        Results:
            Path in litp tree to the created package inheritance.
        """

        # 1. Inherit package with cli
        node_package_url = node_url + "/items/{0}".format(package_name)
        self.execute_cli_inherit_cmd(self.ms1,
                                     node_package_url,
                                     package_url)
        return node_package_url

    def _create_package(self, package_name, expected_state):
        """
        Description:
            Create test package
        Args:
            package_name (str): package name
            expected_state (bool): If True expect positive is True
                                   if False expect positive is False
        Actions:
            1. Get software items collection path
            2. Create test package
        Results:
            stdmsg, stderr
        """

        # 1. Get items path
        items = self.find(self.ms1, "/software", "software-item", False)
        items_path = items[0]

        # 2. Create a package with cli
        package_url = items_path + "/package"
        props = "name='{0}'".format(package_name)

        self.execute_cli_create_cmd(
            self.ms1,
            package_url,
            "package",
            props,
            expect_positive=expected_state)

        return package_url

    @attr('all', 'revert', 'story11354',
            'story11354_tc01', 'bur_only_test')
    def test_01_n_prepare_restore_not_allowed_if_plan_failed(self):
        """
        @tms_id:
            litpcds_11354_tc01
        @tms_requirements_id:
            LITPCDS-11354
        @tms_title:
            prepare_restore throws an error if ran after a failed deployment
            plan
        @tms_description:
            Test that executing prepare_restore after running a deployment
            plan that failed results on an error being thrown

        @tms_test_steps:
        @step: Create an item of type "eth" with invalid macaddress
        @result: Command executed successfully
        @step: Create and run the plan
        @result: The plan fails
        @step: Run "prepare_restore"
        @result: A ValidationError is thrown
        @step: Remove the item created for this test
        @result: Command completed successfully
        @step: Create and run the plan
        @result: Plan completed successfully
        @result: All items under "/deployments" are in "Applied" state

        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        tc_id = '{0}_tc01'.format(self.story_id)

        self.log('info',
        '1. Make change to the model that will cause the plan to fail')
        node_url = self.find(self.ms1, '/deployments', 'node')[0]
        coll_network_interface_url = self.find(
                    self.ms1, node_url, 'collection-of-network-interface')[0]

        new_item = {}
        new_item['type'] = 'eth'
        new_item['macaddress'] = '00:50:56:00:00:81'
        new_item['device_name'] = 'if7'
        new_item['url'] = ('{0}/{1}_{2}'
                                    .format(coll_network_interface_url,
                                            new_item['device_name'],
                                            tc_id))

        props = ('macaddress={0} device_name={1}'
                 .format(new_item['macaddress'], new_item['device_name']))

        self.execute_cli_create_cmd(self.ms1,
                                    new_item['url'],
                                    class_type=new_item['type'],
                                    props=props)

        self.run_and_check_plan(self.ms1, const.PLAN_FAILED,
                                plan_timeout_mins=10)

        self.log('info',
        '2. Verify that "prepare_restore" cannot be run under failed '
           'deployment plan condition')
        _, err, _ = self.execute_cli_prepare_restore_cmd(
                                                self.ms1,
                                                expect_positive=False)
        expected_error = {
            'url': '/litp/prepare-restore',
            'error_type': 'ValidationError',
            'msg': '    Not possible to restore the deployment to a known '
                   'good state because the last deployment plan was not '
                   'successfully executed.'
        }
        missing_err, extra_err = self.check_cli_errors([expected_error], err)
        self.assertTrue([] == missing_err and [] == extra_err)

        self.log('info',
        '3. Remove the item created for this test')
        self.execute_cli_remove_cmd(self.ms1, new_item['url'])
        self.run_and_check_plan(self.ms1, const.PLAN_COMPLETE,
                                plan_timeout_mins=10)

        self.log('info',
        '4. Check that all items under "/deployments" are in "Applied" state')
        self._check_item_state(state='Applied',
                               paths=['/deployments'])

    @attr('all', 'non-revert', 'story11354',
            'story11354_tc02', 'bur_only_test')
    def test_02_p_prepare_restore_with_snapshots(self):
        """
        @tms_id:
            litpcds_11354_tc02
        @tms_requirements_id:
            LITPCDS-11354
        @tms_title:
            Test that "prepare_restore" allows for a successful cluster
            re-deployment

        @tms_description:
            This test procedure verifies the following cases:
            1. LITPCDS-11354
            given a LITP MS with a model with items in
            Applied/Updated/ForRemoval/Initial states and with
            Deployment/Backup snapshots when a user run litp "prepare_restore"
            then MS and LITP model become ready for re-deployment,
            changes can be made to the model, a snapshot can be created and
            deployment plan can be created and run successfully.

            NOTE:
            also verifies the following bugs:
            Bug TORF-109265
            "create_snapshot" command can be successfully issued right after
            "prepare_restore" command completed

            Bug TORF-113860
            Test that "prepare_restore" leaves puppet service in the state it
            was before the command was issued.

            Bug TORF-114663
            Test that changes to MS configuration involving update
            to peer nodes made after running "prepare_restore" are deployed
            successfully.

        @tms_test_steps:
        @step: Create item on node to be marked "ForRemoval"
        @result: Command executed successfully
        @step: Create item on node to be updated and then marked "ForRemoval"
        @result: Command executed successfully
        @step: Create item on node to be in "Updated" state
        @result: Command executed successfully
        @step: Create item on MS to be marked "ForRemoval"
        @result: Command executed successfully
        @step: Create item on MS to be updated and marked "ForRemoval"
        @result: Command executed successfully
        @step: Create item on MS to be in "Updated" state
        @result: Command executed successfully
        @step: Create and run the plan
        @result: Plan completed successfully
        @step: Save property values of all "Updated" and "ForRemoval" items
        @result: Command executed successfully
        @step: Create item on node to be in "Initial" state
        @result: Command executed successfully
        @step: Create item on the MS to be in "Initial" state
        @result: Command executed successfully
        @step: Update some of the existing items
        @result: Command executed successfully
        @step: Mark ForRemoval some of the existing items
        @result: Command executed successfully
        @step: Update and mark ForRemoval some of existing items
        @result: Command executed successfully
        @step: Check that all items in the model are in the expected state
        @result: All items in the model are in expected state
        @step: Remove all existing snapshots
        @result: Command executed successfully
        @step: Set "snap_size" on "root" file system on nodes to "50"
        @result: Command executed successfully
        @step: Create "deployment" snapshot
        @result: Snapshot created successfully
        @step: Create "backup" snapshot
        @result: Snapshot created successfully
        @step: Power down one peer node
        @result: Peer node powered down successfully
        @step: Check status of "puppet" service
        @result: "puppet" service is running
        @step: Run "prepare_restore" command
        @result: Command executed successfully
        @step: Create "Deployment" and "Backup Named" snapshots
        @result: Snapshots created successfully
        @step: Check the state of the system after "prepare_restore"
        @result: All item under "/ms" are in "Applied" state
        @result: All items under "/infrastructure", "/deployments", "/software"
                 are in "Initial" state
        @result: All items that were in "Initial" state are no longer in the
                 model
        @result: All items that were in "Updated" or "ForRemoval" are still in
                 the model and their property have been set back to their
                 initial value
        @result: Folder "/opt/ericsson/nms/litp/etc/puppet/manifests/plugins/"
                 contains only the "ms1.pp" file
        @result: "puppet" certificate for all peer nodes are removed
        @result: "puppet" service is running
        @step: Stop "puppet" service
        @result: "puppet" service stopped successfully
        @step: Run "prepare_restore"
        @result: Command executed successfully
        @step: Create "Deployment" and "Backup Named" snapshots
        @result: Snapshots created successfully
        @step: Check the state of the system after "prepare_restore"
        @result: All item under "/ms" are in "Applied" state
        @result: All items under "/infrastructure", "/deployments", "/software"
                 are in "Initial" state
        @result: All items that were in "Initial" state are no longer in the
                 model
        @result: All items that were in "Updated" or "ForRemoval" are still in
                 the model and their property have been set back to their
                 initial value
        @result: Folder "/opt/ericsson/nms/litp/etc/puppet/manifests/plugins/"
                 contains only the "ms1.pp" file
        @result: "puppet" certificate for all peer nodes are removed
        @result: "puppet" service is stopped
        @step: Update value of property "hostname" on one node
        @result: Command executed successfully
        @step: Update "macaddress" property of one "eth" interface on MS
        @result: Command executed successfully
        @step: Create and run the deployment plan
        @result: Plan completed successfully
        @step: Remove "deployment" snapshot
        @result: Command executed successfully
        @step: Remove "backup" snapshot
        @result: Command executed successfully
        @step: Create "deployment" snapshot
        @result: Snapshot created successfully
        @step: Create a new LITP item
        @result: Command executed successfully
        @step: Create and run the plan
        @result: Plan completed successfully
        @step: Assert that changes to MS have been applied
        @result: Updated "eth" item is in Applied" state
        @result: The "macaddress" property of "eth" item is set correctly.

        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        test_id = 'story{0}tc02'.format(self.story_id)
        # snapshot_name_1 = '{0}a'.format(self.story_id)

        # Temporarily switching off named snapshots
        # To be reverted as soon as the feature that allows to change
        # snap_size on MS become available
        # snapshots = ['snapshot', snapshot_name_1]
        snapshots = ['snapshot']

        self.skip_cleanup = True
        items = []

        self.log('info',
        '1. Define new LITP items to use during tests')

        self.log('info',
        '1.1 Create item on node to be marked "ForRemoval"')
        items.append({})
        items[0]['description'] = 'test removal item on node'
        items[0]['node'] = self._get_node_url('node', 0)
        items[0]['props'] = ('name="{0}_00" path="/var/log"'
                                         .format(test_id))
        items[0]['update_props'] = 'path="/tmp"'
        items[0]['item_id'] = '{0}_lr_rule00'.format(test_id)
        items[0]['url'] = self._create_logrotate_rule_item(
                                    items[0]['node'],
                                    items[0]['item_id'],
                                    items[0]['props'])
        items[0]['transition_to'] = 'ForRemoval'

        self.log('info',
        '1.2 Create item on node to be updated and then marked "ForRemoval"')
        items.append({})
        items[1]['description'] = 'test update and removal item on node'
        items[1]['node'] = self._get_node_url('node', 0)
        items[1]['props'] = ('name="{0}_01" path="/var/log"'
                                         .format(test_id))
        items[1]['update_props'] = 'path="/tmp"'
        items[1]['item_id'] = '{0}_lr_rule01'.format(test_id)
        items[1]['url'] = self._create_logrotate_rule_item(
                                    items[1]['node'],
                                    items[1]['item_id'],
                                    items[1]['props'])
        items[1]['transition_to'] = 'Update_and_Remove'

        self.log('info',
        '1.3 Create item on node to be in "Updated" state')
        items.append({})
        items[2]['description'] = 'test updated item on node'
        items[2]['node'] = self._get_node_url('node', 0)
        items[2]['props'] = ('name="455 {0}" proto="tcp"'
                                      .format(test_id))
        items[2]['update_props'] = 'proto="udp"'
        items[2]['item_id'] = '{0}_fw_rule02'.format(test_id)
        items[2]['url'] = self._create_node_firewall_rule_item(
                                    items[2]['node'],
                                    items[2]['item_id'],
                                    items[2]['props'])
        items[2]['transition_to'] = 'Updated'

        self.log('info',
        '1.4 Create item on MS to be marked "ForRemoval"')
        items.append({})
        items[3]['description'] = 'test removal item on MS'
        items[3]['node'] = self._get_node_url('ms', 0)
        items[3]['props'] = ('name="{0}_03" path="/var/log"'
                                         .format(test_id))
        items[3]['update_props'] = 'path="/tmp"'
        items[3]['item_id'] = '{0}_lr_rule03'.format(test_id)
        items[3]['url'] = self._create_logrotate_rule_item(
                                    items[3]['node'],
                                    items[3]['item_id'],
                                    items[3]['props'])
        items[3]['transition_to'] = 'ForRemoval'

        self.log('info',
        '1.5 Create item on MS to be updated and marked "ForRemoval"')
        items.append({})
        items[4]['description'] = 'test update and removal item on MS'
        items[4]['node'] = self._get_node_url('ms', 0)
        items[4]['props'] = ('name="{0}_04" path="/var/log"'
                                         .format(test_id))
        items[4]['update_props'] = 'path="/tmp"'
        items[4]['item_id'] = '{0}_lr_rule04'.format(test_id)
        items[4]['url'] = self._create_logrotate_rule_item(
                                    items[4]['node'],
                                    items[4]['item_id'],
                                    items[4]['props'])
        items[4]['transition_to'] = 'Update_and_Remove'

        self.log('info',
        '1.6 Create item on MS to be in "Updated" state')
        items.append({})
        items[5]['description'] = 'test updated item on MS'
        items[5]['node'] = self._get_node_url('ms', 0)
        items[5]['props'] = ('name="655 {0}" proto="tcp"'
                                      .format(test_id))
        items[5]['update_props'] = 'proto="udp"'
        items[5]['item_id'] = '{0}_fw_rule05'.format(test_id)

        items[5]['url'] = self._create_node_firewall_rule_item(
                                    items[5]['node'],
                                    items[5]['item_id'],
                                    items[5]['props'])
        items[5]['transition_to'] = 'Updated'

        # Making sure the force_debug is enabled due to
        # TORF-207142
        self.execute_cli_update_cmd(self.ms1,
                                    self.logging_url,
                                    props='force_debug=true')
        self.run_and_check_plan(self.ms1, const.PLAN_COMPLETE,
                                plan_timeout_mins=10)

        self.log('info',
        '2. Log current model state')
        self.execute_cli_show_cmd(self.ms1, '/', '-r')

        self.log('info',
        '3. Save property values of all "Updated" and "ForREmoval" items')
        for item in items:
            item['props_before'] = self.get_props_from_url(self.ms1,
                                                           item['url'])

        self.log('info',
        '4. Create item on node to be in "Initial" state')
        items.append({})
        items[6]['description'] = 'test new item on node'
        items[6]['node'] = self._get_node_url('node', 0)
        items[6]['props'] = ('name="{0}_06" path="/var/log"'
                                         .format(test_id))
        items[6]['item_id'] = '{0}_lr_rule06'.format(test_id)
        items[6]['url'] = self._create_logrotate_rule_item(
                                    items[6]['node'],
                                    items[6]['item_id'],
                                    items[6]['props'])
        items[6]['transition_to'] = 'Initial'

        self.log('info',
        '5. Create item on the MS to be in "Initial" state')
        items.append({})
        items[7]['description'] = 'test new item on node'
        items[7]['node'] = self._get_node_url('ms', 0)
        items[7]['props'] = ('name="{0}_07" path="/var/log"'
                                         .format(test_id))
        items[7]['item_id'] = '{0}_lr_rule07'.format(test_id)
        items[7]['url'] = self._create_logrotate_rule_item(
                                    items[7]['node'],
                                    items[7]['item_id'],
                                    items[7]['props'])
        items[7]['transition_to'] = 'Initial'

        self.log('info',
        '6. Update existing items')
        item_list = [item for item in items
                            if item.get("transition_to") == "Updated"]
        for each_item in item_list:
            self.execute_cli_update_cmd(
                self.ms1, each_item['url'], each_item['update_props'])
            self.get_props_from_url(self.ms1, each_item['url'])  # Log props

        self.log('info',
        '7. Mark ForRemoval existing items')
        item_list = [item for item in items
                            if item.get("transition_to") == "ForRemoval"]
        for each_item in item_list:
            self.execute_cli_remove_cmd(self.ms1, each_item['url'])
            self.get_props_from_url(self.ms1, each_item['url'])  # Log props

        self.log('info',
        '8. Update and mark ForRemoval existing items')
        item_list = [item for item in items
                        if item.get("transition_to") == "Update_and_Remove"]
        for each_item in item_list:
            self.execute_cli_update_cmd(self.ms1,
                                        each_item['url'],
                                        each_item['update_props'])
            self.execute_cli_remove_cmd(self.ms1, each_item['url'])
            self.get_props_from_url(self.ms1, each_item['url'])  # Log props

        self.log('info',
        '9. Check that all relevant items are in correct state')
        errors = self._check_all_defined_items_state_is_correct(items)
        self.assertEqual([], errors,
                '\nFollowing items were found in unexpected state:\n{0}'
                .format('\n'.join(errors)))

        self.log('info',
        '10. Create deployment and backup snapshots')
        self.remove_all_snapshots(self.ms1)
        self._resize_snapshot(50, 'root')
        self._create_snapshot(snapshot_names=snapshots)
        self._check_snapshot_item_is_present(snapshot_names=snapshots)

        self.log('info',
        '12. Log current model state')
        self.execute_cli_show_cmd(self.ms1, '/', '-r')

        self.log('info',
        '13. Power down peer node1')
        nodes = self.get_managed_node_filenames()
        self.assertTrue(self._power_down_peer_nodes(nodes[:1]),
                        'Failed to power down "{0}"'.format(nodes[0]))

        self.log('info',
        '14. Assert that puppet service is running (Bug TORF-113860)')
        self.get_service_status(self.ms1, 'puppet', assert_running=True)

        self.log('info',
        '15. Run "prepare_restore" command')
        self.execute_cli_prepare_restore_cmd(self.ms1)

        self.log('info',
        '16. Verify that deployment and backup snapshots can be created '
             'Bug TORF-109265')
        # NOTE: this step MUST follow the "prepare_restore"
        # command issued during this test. No actions or delay are allowed
        # between prepare_restore and the snapshot creation in order to verify
        # the bug correctly
        self._create_snapshot(snapshot_names=snapshots)

        self.log('info',
        '17. Check system state after "prepare_restore"')
        self.log('info',
        '17.1. Check that everything under "/ms" is in "Applied" state')
        self._check_item_state(state='Applied', paths=['/ms'])

        self.log('info',
        '17.2. Check other model items are in "Initial" state')
        self._check_item_state(state='Initial',
                    paths=['/infrastructure', '/deployments', '/software'])

        self.log('info',
        '17.3. Check that all items that were in "Initial" state are gone '
            'and all items that were in "Updated" or "ForRemoval" are '
            'still present and their properties have original values')
        changed_props, new_props = self._get_changed_properties(items)
        self.assertTrue(([] == changed_props) and ([] == new_props))

        self.log('info',
        '17.4. Check that puppet files have been cleaned up')
        self._check_puppet_files_have_been_cleaned()

        self.log('info',
        '17.5. Assert that puppet service is running (Bug TORF-113860)')
        self.get_service_status(self.ms1, 'puppet', assert_running=True)

        self.log('info',
        '18. Stop puppet service (Bug TORF-113860)')
        self.stop_service(self.ms1, 'puppet')
        out, _, rc = self.get_service_status(self.ms1, 'puppet',
                                             assert_running=False)
        self.assertEqual('inactive', out[0])
        self.assertEqual(3, rc)

        self.log('info',
        '19. Run "prepare_restore" command')
        self.execute_cli_prepare_restore_cmd(self.ms1)

        self.log('info',
        '20. Verify that deployment and backup snapshots can be created '
             'Bug TORF-109265')
        self._create_snapshot(snapshot_names=snapshots)

        self.log('info',
        '21. Check system state after "prepare_restore"')
        self.log('info',
        '21.1. Check that everything under "/ms" is in "Applied" state')
        self._check_item_state(state='Applied', paths=['/ms'])

        self.log('info',
        '21.2. Check other model items are in "Initial" state')
        self._check_item_state(state='Initial',
                    paths=['/infrastructure', '/deployments', '/software'])

        self.log('info',
        '21.3. Check that all items that were in "Initial" state are gone '
              'and all items that were in "Updated" or "ForRemoval" are '
              'still present and their properties have original values')
        changed_props, new_props = self._get_changed_properties(items)
        self.assertTrue(([] == changed_props) and ([] == new_props))

        self.log('info',
        '21.4. Check that puppet files have been cleaned up')
        self._check_puppet_files_have_been_cleaned()

        self.log('info',
        '21.5. Assert puppet service is stopped (Bug TORF-113860)')
        out, _, rc = self.get_service_status(self.ms1, 'puppet',
                                             assert_running=False)
        self.assertEqual('inactive', out[0])
        self.assertEqual(3, rc)

        self.log('info',
        '22. Make changes to MS that will cause changes on peer nodes '
             'TORF-114663')
        ms_ntwk_if_coll_url = self.find(self.ms1,
                                        '/ms',
                                        'collection-of-network-interface')[0]
        ms_eth_if_url = self.find(self.ms1, ms_ntwk_if_coll_url, 'eth')[0]
        free_nics = self.get_free_nics_on_node(self.ms1, '/ms')
        self.assertNotEqual([], free_nics)

        props = 'macaddress={0}'.format(free_nics[0]['MAC'])
        self.execute_cli_update_cmd(self.ms1, ms_eth_if_url, props=props)
        ms_eth_if_props = self.get_props_from_url(self.ms1, ms_eth_if_url)

        self.log('info',
        '23. Change value of property "hostname" on one node')
        node = self.find(self.ms1, '/deployments', 'node')[0]
        props = 'hostname=nodeA'
        self.execute_cli_update_cmd(self.ms1, node, props)

        # Making sure the force_debug is enabled due to
        # TORF-207142
        self.execute_cli_update_cmd(self.ms1,
                                    self.logging_url,
                                    props='force_debug=true')
        self.log('info',
        '24. Create and run deployment plan')
        self.run_and_check_plan(self.ms1, const.PLAN_COMPLETE,
                                plan_timeout_mins=60)

        self.log('info',
        '25. Perform sanity check on system after re-deployment')
        self.log('info',
        '25.1 Verify that snapshots can be removed and created')
        self._check_snapshot_item_is_present(snapshot_names=snapshots)
        self.remove_all_snapshots(self.ms1)
        self._create_snapshot(snapshot_names=['snapshot'])

        self.log('info',
        '25.2.Verify that an new LITP item can be created')
        items.append({})
        items[-1]['description'] = ('test create new item after '
                                    'prepare_restore')
        items[-1]['node'] = self._get_node_url('node', 0)
        items[-1]['props'] = ('name="{0}_09" path="/var/log"'
                               .format(test_id))
        items[-1]['item_id'] = '{0}_lr_rule09'.format(test_id)
        items[-1]['url'] = self._create_logrotate_rule_item(
                                    items[-1]['node'],
                                    items[-1]['item_id'],
                                    items[-1]['props'])

        # Making sure the force_debug is enabled due to
        # TORF-207142
        self.execute_cli_update_cmd(self.ms1,
                                    self.logging_url,
                                    props='force_debug=true')
        self.run_and_check_plan(self.ms1, const.PLAN_COMPLETE,
                                plan_timeout_mins=15)

        self.log('info',
        '25.3 Assert that changes to MS have been applied')
        self.assertEqual("Applied", self.get_item_state(self.ms1,
                                                        ms_eth_if_url))
        ms_eth_if_props_cur = self.get_props_from_url(self.ms1, ms_eth_if_url)
        changed_props, new_props = self.get_changed_props(ms_eth_if_props_cur,
                                                          ms_eth_if_props)
        self.assertTrue([] == changed_props and [] == new_props)

    @attr('all', 'non-revert', 'story11354',
                    'story11354_tc03', 'bur_only_test')
    def test_03_n_prepare_restore_error_handling_end_rest_syntax(self):
        """
        @tms_id:
            litpcds_11354_tc_03
        @tms_requirements_id:
            LITPCDS-11354
        @tms_title:
            Test "prepare_restore" idempotency and error handling mechanism
        @tms_description:
        Verify following cases:
        - if a user attempt to run "litp prepare_restore" while
          a deployment plan is running then an error is thrown
        - when a user run "litp prepare_restore"
          and the remove snapshot procedure fails an error is thrown
        - when a user run "prepare_restore" using the "update" rest object
            "litp update -p /litp/prepare-restore -o path='/'"
          then MS and LITP model become ready for re-deployment
        - Re-run the command
             "litp update -p /litp/prepare-restore -o path='/'"
          to verify that it is idempotent

        @tms_test_steps:
        @step: Make changes to the model, create and run the plan
        @result: The plan is running
        @step: Issue the "litp prepare_restore" command
        @result: An "InvalidRequestError" is thrown
        @step: Wait for the deployment plan to complete
        @result: The deployment plan completed successfully
        @result: All items under '/deployments', '/infrastructure',
                 '/software' branches are in state "Applied"
        @step: Create deployment and backup snapshots
        @result: Snapshots are created
        @step: Replace the "lvremove" binary file on the MS with a dummy
               file to cause restore snapshot to fail
        @result: Dummy file is created
        @step: Issue the "prepare_restore" command
        @result: An "InternalServerError" is thrown
        @step: Restore original version of "lvremove" binary file
        @result: "lvremove" file restored
        @step: Issue the "prepare_restore" command using the "update" rest
               object
        @result: The command execute successfully
        @step: Check state of puppet files
        @result: Folder "/opt/ericsson/nms/litp/etc/puppet/manifests/plugins/"
                 contains only the "ms1.pp" files
        @step: Check state of items under "/infrastructure", "/deployments",
                "/software"
        @result: All items under "/infrastructure", "/deployments", "/software"
        are in "Initial" state
        @step: Re-issue the previous command
        @result: Command executed successfully
        @step: Check state of puppet files
        @result: Folder "/opt/ericsson/nms/litp/etc/puppet/manifests/plugins/"
                 contains only the "ms1.pp" file
        @step: Check state of items under "/infrastructure", "/deployments",
                "/software"
        @result: All items under "/infrastructure", "/deployments", "/software"
        are in "Initial" state

        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        # Temporarily switching off named snapshots
        # To be reverted as soon as the feature that allows to change
        # snap_size on MS become available
        # snapshot_name = self.story_id
        self.skip_cleanup = True

        self.log('info',
        '1. Verify prepare_restore cannot run while a deployment '
            'plan is running')

        self.log('info',
        '1.1. Create new package LITP item')
        items_path = self.find(self.ms1,
                            '/software/', 'collection-of-software-item')[0]
        package_path = '{0}/emacs-nox'.format(items_path)

        self.execute_cli_show_cmd(self.ms1,
                                  package_path, expect_positive=False)
        self.execute_cli_create_cmd(self.ms1,
                                    package_path, 'package', 'name=emacs-nox')
        self.execute_cli_inherit_cmd(
            self.ms1,
            '/deployments/d1/clusters/c1/nodes/n1/items/emacs-nox',
            '/software/items/emacs-nox')

        self.log('info',
        '1.2. Create, run plan and assert it is running')
        self.run_and_check_plan(self.ms1, const.PLAN_IN_PROGRESS,
                                plan_timeout_mins=1)

        self.log('info',
        '1.3. Attempt to run "prepare_restore" while deployment '
            'plan is running')
        _, err, _ = self.execute_cli_prepare_restore_cmd(
                                            self.ms1, expect_positive=False)

        self.log('info',
        '1.4. Check that correct error is thrown')
        expected_error = {
            'url': '/litp/prepare-restore',
            'error_type': 'InvalidRequestError',
            'msg': '    Operation not allowed while plan is running/stopping'
        }
        missing_err, extra_err = self.check_cli_errors([expected_error], err)
        self.assertTrue([] == missing_err and [] == extra_err)

        self.log('info',
        '1.5. Check that deployment plan completes successfully')
        self.wait_for_plan_state(self.ms1, const.PLAN_COMPLETE)

        self._check_item_state(state='Applied',
                    paths=['/deployments', '/infrastructure', '/software'])

        self.log('info',
        '2. Verify that prepare_restore can detect deployment plan fail '
            'and collect the error message')

        self.log('info',
        '2.1. Create deployment and backup snapshots')
        self.remove_all_snapshots(self.ms1)
        self._resize_snapshot(25, 'root')

        # Temporarily switching off named snapshots
        # To be reverted as soon as the feature that allows to change
        # snap_size on MS become available
        # self._create_snapshot(snapshot_names=['snapshot', snapshot_name])
        self._create_snapshot(snapshot_names=['snapshot'])

        self.log('info',
        '2.2. Corrupt "lvremove" binary file on MS')
        self.backup_file(self.ms1,
                         self.storage.lvremove_path,
                         backup_mode_cp=False)

        file_contents = ['#!/bin/sh',
                         'echo "lvremove hit a problem 5" >&2',
                         "exit 5"]

        create_success = self.create_file_on_node(self.ms1,
                                                  self.storage.lvremove_path,
                                                  file_contents,
                                                  su_root=True)
        self.assertTrue(create_success,
            'File "{0}" could not be created'.
             format(self.storage.lvremove_path))

        self.log('info',
        '2.3. Attempt to run "prepare_restore" and expect that if fail')
        _, err, _ = self.execute_cli_prepare_restore_cmd(
                                            self.ms1, expect_positive=False)

        self.log('info',
        '2.4. Assert that correct error is thrown')
        # Temporarily switching off named snapshots
        # To be reverted as soon as the feature that allows to change
        # snap_size on MS become available
        # expected_error = {
        #     'url': '/snapshots/{0}'.format(snapshot_name),
        #     'error_type': 'InternalServerError',
        #     'msg': '    Remove snapshot plan failed'
        # }

        expected_error = {
            'url': '/snapshots/{0}'.format('snapshot'),
            'error_type': 'InternalServerError',
            'msg': '    Remove snapshot plan failed'
        }

        missing_err, extra_err = self.check_cli_errors([expected_error], err)
        self.assertTrue([] == missing_err and [] == extra_err)

        self.log('info',
        '2.5. Restore original version of "lvremove"')
        restored = self.restore_backup_files(self.ms1,
                                             self.storage.lvremove_path)
        self.assertTrue(restored)

        self.log('info',
        '3. Verify that prepare_restore can be run using the "update" rest '
            'object')
        self.execute_cli_update_cmd(self.ms1,
                                    '/litp/prepare-restore', 'path="/"')

        self.log('info',
        '4. Check that puppet files have been cleaned up')
        self._check_puppet_files_have_been_cleaned()

        self.log('info',
        '5. Check that items under "/infrastructure", "/deployments", '
            '"/software" are in "Initial" state')
        self._check_item_state(state='Initial',
                    paths=['/infrastructure', '/deployments', '/software'])

        self.log('info',
        '6. Verify that prepare_restore command can be run multiple times')
        self.execute_cli_prepare_restore_cmd(self.ms1)

        self.log('info',
        '7. Check that puppet files have been cleaned up')
        self._check_puppet_files_have_been_cleaned()

        self.log('info',
        '8. Check that items under "/infrastructure", "/deployments", '
            '"/software" are in "Initial" state')
        self._check_item_state(state='Initial',
                    paths=['/infrastructure', '/deployments', '/software'])

    @attr('all', 'revert', 'story2115', 'story2115_tc23')
    def test_23_p_run_successful_snapshot_plan(self):
        """
        Description:
            A create snapshot plan will not execute when the prompt is returned
            to the

            A plan will not execute when the prompt is returned to the user
            once a remove snapshot plan is running

            A deployment plan will not execute when the prompt is returned
            to the user once a create snapshot plan is running

            NOTE: Verifies TORF-109265

        Actions:

            Scenario 1: create snapshot then run creates_snapshot in a loop
            1.  Delete any old snapshot
            2.  Run create_snapshot
            3.  Issue remove plan cmd & assert error messages
            4.  Reissue create_snapshot while previous plan is running &
                assert error messages
            5.  Verify the DoNothingPlanError for the second create_snapshot
                cmd
            6.  Verify that the snapshot plan succeeds
            7.  Verify that the snapshot exists in the model

            Scenario 2: remove snapshot & execute run_plan in a loop
            8.  Create a package (finger) on node 1
            9.  Inherit the package to a node.
            10. Soft power off Node2 and wait until powered off
            11. Execute Remove_snapshot -f
            12. Execute run_plan cmd once when the remove snapshot plan is
                running & assert error messages
            13. Execute create_plan cmd in a loop while the remove snapshot
                plan is running assert error messages
            14. Power Node2 back on
            15. Remove volume group snapshot on Node2
            16. Verify no snapshot item exists in the model

            Scenario 3: Run Deployment plan & execute create_snapshot in a loop
            17. Run Deployment Plan
            18. Run create_snapshot plan in a loop while deployment plan is
                running & assert error messages
            19. Verify that the snapshot plan succeeds
            20. Verify that the snapshot exists in the model.
            21. Verify package (finger) item is in the model


        Result:
            A create snapshot plan cannot be run while a create snapshot plan
            is running and finishes successfully

            A plan cannot be run while a remove snapshot plan  is running and
            finishes successfully

            A create snapshot plan cannot be run while a deployment plan
            is running and finishes successfully
        """
        self.log('info', '1. Delete any old snapshot')
        if self.is_snapshot_item_present(self.ms1):
            self.execute_and_wait_removesnapshot(self.ms1)

        self.log('info', '2. Create a snapshot')
        self.execute_cli_createsnapshot_cmd(self.ms1)

        inv_req_err = 'InvalidRequestErrorPlanalreadyrunning'
        failed_snap = 'DoNothingPlanErrornotasksweregenerated.Nosnapshott' \
                      'asksaddedbecausefailedDeploymentSnapshotexists'
        inv_req_err_stop = '/plans/planInvalidRequestErrorRemovingarunning/' \
                           'stoppingplanisnotallowed'

        self.log('info', '3. Issue remove plan cmd & assert error messages')
        _, stderr, _ = self.execute_cli_removeplan_cmd(self.ms1,
                                                       expect_positive=False)
        self.assertEqual(inv_req_err_stop, ''.join(stderr).replace(' ', ''))

        self.log('info', '4. Reissue create_snapshot while previous plan '
                         'is running & assert error messages')
        # Once a plan has finished and returns successful there are mco
        # commands being issued to each node. This can take up to 30
        # seconds if a node is down and not responding. During this time
        # the test verifies that when executing a create/run command no
        # create/run succeeds even though the user has the prompt back and
        # thinks everything is OK. The only way to verify this is to continue
        # to issue create/run commands until LITP allows it once the user
        # gets the prompt back.
        timeout = 300
        time_start = time.time()
        create_snapplan_cmd = self.cli.get_create_snapshot_cmd()
        while True:
            _, stderr, _ = self.run_command(self.ms1, create_snapplan_cmd)
            self.assertNotEqual(failed_snap, stderr)
            if ''.join(stderr).replace(' ', '') != inv_req_err:
                break
            time.sleep(1)
            self.assertTrue((time.time() - time_start) < timeout,
                            'Time out waiting for second'
                            'create snapshot plan to run')

        self.log('info', '5. Verify the DoNothingPlanError for the '
                         'second create_snapshot cmd')
        _, stderr, _ = self.run_command(self.ms1, create_snapplan_cmd)
        self.assertTrue(self.is_text_in_list('DoNothingPlanError', stderr))

        self.log('info', '6. Verify that the snapshot plan succeeds')
        self.assertTrue(self.wait_for_plan_state(self.ms1,
                       const.PLAN_COMPLETE))

        self.log('info', '7. Verify that the snapshot exists in the model')
        self.assertTrue(self.is_snapshot_item_present(self.ms1))

        self.log('info', '8. Create a package (finger) on node 1')
        node = self.mn_nodes[0]
        self._create_package("finger", True)
        node_url = self.get_node_url_from_filename(self.ms1, node)

        self.log('info', '9. Inherit the package to a node.')
        self.execute_cli_inherit_cmd(
            self.ms1,
            '/deployments/d1/clusters/c1/nodes/n1/items/finger',
            '/software/items/package')

        self.log('info', '10. Soft power off Node2 and wait until powered off')
        self._soft_poweroff_node(self.mn_nodes[1])

        self.log('info', '11. Execute remove_snapshot -f')
        self.execute_cli_removesnapshot_cmd(self.ms1, args='-f')
        inv_req_err_stp = '/plans/planInvalidRequestErrorPlaniscurrentlyrun' \
                          'ningorstopping'
        inv_req_err_creat = '/plans/planInvalidRequestErrorCreateplanfailed:' \
                            'Planalreadyrunning'

        self.log('info', '12. Execute run_plan cmd once when the remove '
                         'snapshot plan is running & assert error messages')
        _, stderr, _ = self.execute_cli_runplan_cmd(self.ms1,
                                                    expect_positive=False)
        self.assertEqual(inv_req_err_stp, ''.join(stderr).replace(' ', ''))

        self.log('info', '13. Execute create_plan cmd in a loop while the'
                         ' remove snapshot plan is running assert error '
                         'messages')
        timeout = 300
        time_start = time.time()
        create_plan_cmd = self.cli.get_create_plan_cmd()
        while True:
            _, stderr, _ = self.run_command(self.ms1, create_plan_cmd)
            if ''.join(stderr).replace(' ', '') != inv_req_err_creat:
                break
            time.sleep(1)
            self.assertTrue((time.time() - time_start) < timeout,
                            'Time out waiting for second'
                            'create snapshot plan to run')

        self.log('info', '14. Power Node2 back on')
        self.poweron_peer_node(self.ms1, self.mn_nodes[1])

        self.log('info', '15. Remove volume group snapshot on Node2')
        lvdis = self.get_lv_info_on_node(self.mn_nodes[1])
        vg_path = lvdis['L_vg1_root_']['LV_PATH']
        cmd = self.storage.get_lvremove_cmd(vg_path, "-f")
        out, _, _ = self.run_command(self.mn_nodes[1], cmd, su_root=True,
                                     default_asserts=True)
        self.assertTrue(self.is_text_in_list("successfully removed", out))

        self.log('info', '16. Verify no snapshot item exists in the model')
        self.assertFalse(self.is_snapshot_item_present(self.ms1))

        self.log('info', '17. Run Deployment Plan')
        self.run_and_check_plan(self.ms1, const.PLAN_COMPLETE, 20)

        self.log('info', '18. Run create_snapshot plan in a loop while '
                         'deployment plan is running & assert error messages')
        inv_req_err = 'InvalidRequestErrorPlanalreadyrunning'

        timeout = 300
        time_start = time.time()
        while True:
            _, stderr, _ = self.run_command(self.ms1, create_snapplan_cmd)
            self.assertNotEqual(failed_snap, stderr)
            if ''.join(stderr).replace(' ', '') != inv_req_err:
                break
            time.sleep(1)
            self.assertTrue((time.time() - time_start) < timeout,
                            'Time out waiting for second'
                            'create snapshot plan to run')

        self.log('info', '19. Verify that the snapshot plan succeeds')
        self.assertTrue(self.wait_for_plan_state(self.ms1,
                        const.PLAN_COMPLETE))

        self.log('info', '20. Verify that the snapshot exists in the model.')
        self.assertTrue(self.is_snapshot_item_present(self.ms1))

        self.log('info', '21. Verify package (finger) item is in the model')
        self.execute_cli_show_cmd(self.ms1, '{0}/items/finger'.
                                  format(node_url))
