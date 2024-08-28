"""
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     February 2016
@author:    Maria Varley
@summary:   Integration test for separating callback
            and config tasks into their own phases
            Agile: STORY LITPCDS-11955
"""

from litp_generic_test import GenericTest, attr
from litp_cli_utils import CLIUtils
import os


class Story11955(GenericTest):
    '''
    As a LITP Architect I do not want callback and config
    tasks scheduled in the same LITP plan phase
    '''
    def setUp(self):
        """
        Description:
            Runs before every single test
        Actions:
            1. Call the super class setup method
            2. Set up variables used in the tests
        Results:
            The super class prints out diagnostics and variables
            common to all tests are available.
        """
        super(Story11955, self).setUp()
        self.ms1 = self.get_management_node_filenames()[0]
        self.cli = CLIUtils()

    def tearDown(self):
        """
        Description:
            Runs after every single test
        Actions:
            1. Perform Test Cleanup
            2. Call superclass teardown
        Results:
            Items used in the test are cleaned up and the
        """
        super(Story11955, self).tearDown()

    @attr('all', 'revert', 'story11955', 'story11955_tc08')
    def test_08_p_reboot_task_and_config_task_segregation(self):
        """
        @tms_id:
            litpcds_11955_tc08
        @tms_requirements_id:
            LITPCDS-11955
        @tms_title:
            Verify that "Reboot" tasks (Callback task) are not mixed in a
            phase with any "Config" task
        @tms_description:
            Verify that "Reboot" task (Callback task) are not mixed in a
            phase with any "Config" task
        @tms_test_steps:
        @step: Create a number of items in the model so that a "Reboot node"
               task and a number of "Config" tasks are generated when plan
               is created
        @result: items created
        @step: Enter the create_plan command
        @result: Plan is created successfully
        @result: The plan contains a "Reboot node" task
        @result: The plan a contains number of "Config" tasks
        @result: The phase with the "Reboot node" task does not contain
                 any callback task
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        self.log('info',
        "1. Find the bridge device on a node configured with the node's "
           "IP address")
        node_paths = self.find(self.ms1, "/deployments", "node")
        fname = self.get_node_filename_from_url(self.ms1, node_paths[0])
        node_ip = self.get_node_att(fname, 'ipv4')
        bridge_paths = self.find(self.ms1, node_paths[0], "bridge")
        bridge_path = ''
        for bridge in bridge_paths:
            bridge_ip = self.get_props_from_url(self.ms1, bridge, "ipaddress")
            if bridge_ip == node_ip:
                bridge_path = bridge
                break
        else:
            self.fail('Suitable bridge device on node "{0}" not found'.
                format(node_paths[0]))

        self.log('info',
        '2. Find the ipaddress that are allowed to access the sfs-export')
        sfs_path = self.find(self.ms1, "/infrastructure", "sfs-export")[1]
        ip_allowed = self.get_props_from_url(self.ms1,
                                             sfs_path,
                                             "ipv4allowed_clients")

        self.log('info',
        '3. Update the network interface of the mounted shares')
        free_ip_addr = self.get_free_ip_by_net_name(self.ms1, "mgmt")

        try:
            props = "ipaddress={0}".format(free_ip_addr)
            self.execute_cli_update_cmd(self.ms1, bridge_path, props=props)
            props = "ipv4allowed_clients={0},{1}". \
                    format(ip_allowed, free_ip_addr)
            self.execute_cli_update_cmd(self.ms1, sfs_path, props=props)

            self.log('info',
            '4. Create a sysctl parameter on each node')
            sysparam_node_config = self.find(self.ms1,
                                             "/deployments",
                                             "sysparam-node-config")

            for sysparam in sysparam_node_config:
                sys_param_path = sysparam + "/params/sysctl11955"
                props = 'key="kernel.threads-max" value="15637"'
                self.execute_cli_create_cmd(self.ms1,
                                            sys_param_path,
                                            "sysparam",
                                            props=props)

            self.log('info',
            '5 Create a package item type on each node')
            item = self.find(self.ms1, "/software", "software-item", False)[0]
            props = "name='telnet'"
            package_path = os.path.join(item, "telnet")
            self.execute_cli_create_cmd(self.ms1,
                                        package_path,
                                        "package",
                                        props=props)

            for node in node_paths:
                node_sw_ref = self.find(self.ms1,
                                        node,
                                        'software-item',
                                        rtn_type_children=False,
                                        find_refs=True,
                                        exclude_services=True)[0]
                self.execute_cli_inherit_cmd(
                                        self.ms1,
                                        os.path.join(node_sw_ref, "telnet"),
                                        package_path)

            self.log('info',
            '6. Execute the create_plan command')
            self.execute_cli_createplan_cmd(self.ms1)

            self.log('info',
            '7 Check that "config" task and "Reboot node" task are not in '
              'the same phase')
            self.execute_cli_showplan_cmd(self.ms1)
            plan_json = self.execute_cli_showplan_cmd(self.ms1,
                                                      args='-j',
                                                      load_json=True)[0]

            phases_json = \
                plan_json['_embedded']['item'][0]['_embedded']['item']

            reboot_node_task = 'Reboot node'
            phases_with_reboot_task = []
            phases_with_config_task = []
            for phase in phases_json:
                tasks = phase['_embedded']['item'][0]['_embedded']['item']
                for task in tasks:
                    if reboot_node_task in task['description']:
                        phases_with_reboot_task.append(str(phase['id']))
                    else:
                        # If a task has property "call_id" it is a config task
                        if task.get('call_id') is not None:
                            phases_with_config_task.append(str(phase['id']))

            self.log('info', '"Reboot" tasks found on phases "{0}"'.
                              format(','.join(set(phases_with_reboot_task))))
            self.log('info', '"Config" tasks found on phases "{0}"'.
                              format(','.join(set(phases_with_config_task))))

            self.assertNotEqual([], phases_with_config_task,
                'No "Config" tasks were found in the plan')

            self.assertNotEqual([], phases_with_config_task,
                'No "Reboot" tasks were found in the plan')

            self.assertEqual(0,
                len(set(phases_with_config_task).intersection(
                                                set(phases_with_reboot_task))),
                'Found "Config" tasks and "Reboot" task in same phase')

        finally:
            self.log("info",
            "FINALLY: Revert ip address on bridge device")
            props = "ipaddress={0}".format(node_ip)
            self.execute_cli_update_cmd(self.ms1, bridge_path, props=props)

            self.log("info",
            "FINALLY: Revert allowed ip addresses on sfs-export")
            props = "ipv4allowed_clients={0}".format(ip_allowed)
            self.execute_cli_update_cmd(self.ms1, sfs_path, props=props)
