'''
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     October 2018
@author:    Philip Daly
@summary:   As a LITP user I want the ability to create and run a
            litp plan which only performs a rolling over
            node reboot of peer servers
            Agile: TORF-289801
'''

from litp_generic_test import GenericTest, attr
from redhat_cmd_utils import RHCmdUtils
from litp_cli_utils import CLIUtils
import test_constants


class Story289801(GenericTest):
    """
    As a LITP user I want the ability to create
    and run a litp plan which only performs a
    rolling over node reboot of peer servers
    """

    def setUp(self):
        """run before every test"""
        super(Story289801, self).setUp()
        self.ms_node = self.get_management_node_filename()
        self.list_managed_nodes = self.get_managed_node_filenames()
        self.rhcmd = RHCmdUtils()
        self.cli = CLIUtils()
        self.uptime_cmd = "/usr/bin/uptime"
        self.litp_path = "/usr/bin/litp"

    def tearDown(self):
        """run after every test"""
        super(Story289801, self).tearDown()
        # EXTRA CODE ADDED ON ACCOUNT OF TORF-302424
        # WHICH ESSENTIALLY PREVENTS restore_model FROM
        # REMOVING ITEMS IN STATE initial FROM THE MODEL.
        show_cmd = self.cli.get_show_cmd('/', "-r")
        grep_filter = \
            "| {0} / | {0} -v :".format(self.rhcmd.grep_path)
        grep_command = "{0} {1}".format(show_cmd, grep_filter)
        # GET ALL URLS FROM THE LITP MODEL
        stdout, _, _ = \
            self.run_command(self.ms_node, grep_command)
        # REMOVE THE FOLLOWING ITEMS WHICH DO NOT HAVE A STATE
        stateless_urls = ["/plans", "/litp"]
        for url in stateless_urls:
            matches = [x for x in stdout if url in x]
            for match in matches:
                index = stdout.index(match)
                stdout.pop(index)
        # CYCLE THROUGH COLLECTED PATHS AND REMOVE initial ITEMS
        child_of_removed_object = []
        for url in stdout:
            # IF A PARENT IS REMOVED THE CHILDREN ARE REMOVED
            # AUTOMATICALLY SO WE DON'T NEED TO EXECUTE THE
            # COMMAND ON THEM AS THEY WILL NO LONGER EXIST
            if url in child_of_removed_object:
                continue
            state = \
                self.get_item_state(self.ms_node, url)
            if state == "Initial":
                child_of_removed_object.extend(
                    [x for x in stdout if url in x])
                self.execute_cli_remove_cmd(self.ms_node, url,
                                            add_to_cleanup=False)
        self.remove_node_from_connfile("node3")

    def execute_cli_create_reboot_plan_cmd(self, node, url=None,
                                           username=None, password=None,
                                           expect_positive=True):
        """
        Description:
            Build + Run a LITP create reboot plan command.

        Args:
            node            (str): Node you want to run command on.

        Kwargs:
            url             (str): LITP path to a specific node to reboot,
                                   defaults to rebooting all nodes in
                                   the deployment. Default value is None.

            username        (str): User to run command as if not default.
                                   Default value is None.

            password        (str): Password to run command as if not default.
                                   Default value is None.

            expect_positive (bool): Determines error checking. By default\
                                    assumes command will run without failure.
                                    Default valule is True.

        Returns:
            list, list, int. std_out, std_err, rc from create reboot command.
        """
        # build and run create command
        reboot_plan_cmd = self.get_create_reboot_plan_cmd(url)
        stdout, stderr, returnc = \
            self.run_command(node, reboot_plan_cmd,
                             username, password)

        # assert expected values
        if expect_positive:
            self.assertEqual([], stderr)
            self.assertEqual(0, returnc)

        else:
            self.assertEqual([], stdout)
            self.assertNotEqual([], stderr)
            self.assertNotEqual(0, returnc)

        return stdout, stderr, returnc

    def get_create_reboot_plan_cmd(self, url=None):
        """
        Description:
            Generate a LITP create_reboot_plan command.

        Kwargs:
            url (str): Optional node url arg for the command.
                       Default value is None.

        Returns:
            str. Correctly formatted CLI create_reboot_plan command.
        """

        cmd = "{0} create_reboot_plan"\
            .format(self.litp_path)
        if not url:
            return cmd
        if url:
            cmd = "{0} create_plan -p {1}"\
                .format(self.litp_path, url)
            return cmd

    def chk_node_uptime(self, node, node_uptimes):
        """
        Description:
            Function to check the uptime on the supplied node.
        Args:
            node (str): The node on which the uptime is to be checked.

            node_uptimes (list): list to which the nodes
                                 uptime is to be added.
        Returns:
            dict. Uptimes of the nodes with node filename as key
        """
        # ISSUE THE UPTIME COMMAND ON THE SUPPLIED NODE.
        stdout, _, _ = \
            self.run_command(node, self.uptime_cmd)

        # PARSE THE UPTIME COMMAND OUTPUT AND CONVERT
        # DAYS AND HOURS DECLARATIONS TO MINUTES
        # FOR SUBSEQUENT COMPARISON.
        split_lines = stdout[0].split(',')
        # IF THE NODE IS ONLY UP A FEW MINUTES.
        if 'min' in split_lines[0]:
            line_elements = split_lines[0].split(' ')
            node_uptimes[node] = int(line_elements[2])
            return node_uptimes
        # IF THE NODE IS UP A FEW HOURS.
        elif ('min' not in split_lines[0] and
                'days' not in split_lines[0] and 'day' not in split_lines[0]):
            line_elements = split_lines[0].split(' ')
            # REMOVE EMPTY ENTRIES FROM LIST.
            # THIS HAPPENS IN THE CASE OF THE NODE BEING UP
            # FOR JUST A SINGLE HOUR.
            line_elements = [x for x in line_elements if x != '']
            hours = int(line_elements[2].split(':')[0])
            mins = int(line_elements[2].split(':')[1])
            hour_converted_mins = hours * 60
            node_uptimes[node] = hour_converted_mins + mins
            return node_uptimes
        # IF THE NODE IS UP FOR ONE OR MORE DAYS.
        elif 'days' in split_lines[0] or 'day' in split_lines[0]:
            line_elements = split_lines[0].split(' ')
            days = int(line_elements[2])
            day_converted_minutes = days * 1440
            # IF THE NODE IS UP FOR N DAYS & N MINS.
            if 'min' in split_lines[1]:
                line_elements = split_lines[1].split(' ')
                minutes = int(line_elements[1])
                node_uptimes[node] = \
                    day_converted_minutes + minutes
                return node_uptimes
            # IF THE NODE IS UP FOR N DAYS & N HOURS.
            else:
                line_elements = split_lines[1].strip().split(':')
                hour_converted_mins = int(line_elements[0]) * 60
                mins = int(line_elements[1])
                node_uptimes[node] = \
                    day_converted_minutes + \
                    hour_converted_mins + mins
                return node_uptimes

    def compare_uptimes(self, starting_node_uptimes, current_node_uptimes):
        """
        Description:
            Function to compare the collected uptimes
            from the LITP nodes.

        Args:
            starting_node_uptimes (dict): The initial uptimes of the
                                          nodes in the deployment.

            current_node_uptimes (dict): The current uptimes of the
                                     nodes in the deployment.
        """
        for node in current_node_uptimes:
            current_uptime = current_node_uptimes[node]
            original_uptime = starting_node_uptimes[node]
            self.assertTrue(current_uptime < original_uptime,
                            "The current uptime: {0}, is not less that "
                            "the starting uptime: {1}, implying that "
                            "node {2} did not in fact "
                            "reboot.".format(current_uptime, original_uptime,
                                             node))

    def chk_node_wrapped_in_lock_unlock_tasks_in_plan(self, showplan_output):
        """
        Description:
            Function to ensure that all reboot tasks per node are wrapped
            in lock and unlock tasks.
        Args:
            showplan_output (list): output from the show plan command.
        """
        indexes = []
        counter = 0
        for item in showplan_output:
            if "Phase" in item:
                indexes.append(counter)
            counter += 1

        order = {}
        for index in indexes:
            node_url = showplan_output[index + 3]
            if node_url not in order:
                order[node_url] = []
            task = showplan_output[index + 4]
            if 'Lock VCS on node' in task:
                order[node_url].append("Lock")
            elif 'Reboot node' in task:
                order[node_url].append("Reboot")
            elif 'Unlock VCS on node' in task:
                order[node_url].append("Unlock")

        for node_url in order:
            self.assertTrue(order[node_url] ==
                            ["Lock", "Reboot", "Unlock"],
                            "The following declared node: {0}, "
                            "was not wrapped in Lock & Unlock "
                            "tasks.".format(node_url))

    @attr('all', 'revert', 'story289801', 'story289801_tc03')
    def test_03_p_node_reboot_plan(self):
        """
        @tms_id: torf_289801_tc03
        @tms_requirements_id: TORF-289801
        @tms_title: create_reboot_plan test.
        @tms_description:
            Test to verify that when the litp create_reboot_plan
            command is issued that a plan with only tasks to lock,
            reboot, and unlock nodes is created. Ensure the
            execution of the reboot plan is successful, and also
            that the uptimes of the nodes is less than at the
            start of the test proving that the nodes did indeed
            reboot.
        @tms_test_steps:
            @step: Gather the starting uptimes of the nodes.
            @result: Uptimes are gathered.
            @step: Gather the URLs of some LITP items for updating
                   to ensure some items in state Updated exist in
                   the LITP model. A package, and a service
                   object shall be used for the test.
            @result: URL's are gathered
            @step: Update a property on the objects.
                   Service_name on service, and epoch on package
            @result: Property is updated.
            @step: Expand the cluster to include a third node in
                   the LITP model, but do not deploy this updated
                   configuration.
            @result: LITP model is populated with a third node
                     and numerous child objects in state Initial.
            @step: Find all nodes in the deployment, and
                   group them based on item state.
            @result: Nodes are successfully collected and grouped.
            @step: Issue the create_reboot_plan command.
            @result: Reboot plan is successfully generated.
            @step: Issue the show plan command.
            @result: The output of the show plan is collected.
            @step: Ensure all nodes in state Applied
                   are present in the reboot plan.
            @result: All Applied state nodes are present.
            @step: Ensure no collected state Initial nodes are
                   present in the reboot plan.
            @result: No Initial state nodes are present.
            @step: Ensure all node reboot tasks are wrapped in
                   Lock and Unlock tasks.
            @result: All nodes are wrapped in Lock & Unlock tasks.
            @step: Issue the run_plan command.
            @result: The plan completes successfully.
            @step: Wait for all nodes to reboot.
            @result: All nodes reboot successfully.
            @step: Gather the current uptimes of the nodes.
            @result: Uptimes are gathered.
            @step: Compare the starting and current uptimes, and
                   ensure the current uptime is less than starting.
            @result: Current uptimes are less than starting.
            @step: Ensure updated model items are still in
                   state updated.
            @result: Updated items have remained in updated state.

        @tms_test_precondition:NA
        @tms_execution_type: Automated
        """
        self.log('info', "Gather the starting uptimes of the nodes.")
        starting_node_uptimes = {}
        for node in self.list_managed_nodes:
            starting_node_uptimes = \
                self.chk_node_uptime(node, starting_node_uptimes)

        self.log('info', "Gather the URLs for some LITP items.")
        package_url = \
            self.find(self.ms_node, "/software",
                      "package", rtn_type_children=True)[0]

        service_url = \
            self.find(self.ms_node, "/software", "service",
                      rtn_type_children=True)[0]
        self.backup_path_props(self.ms_node, package_url)
        self.backup_path_props(self.ms_node, service_url)

        self.log('info', "Update a property on the objects. "
                 "Service_name on the service, and epoch on the package.")
        epoch_current_value = \
            int(self.get_props_from_url(self.ms_node,
                                        package_url, "epoch"))
        new_int = int(epoch_current_value) + 1
        self.execute_cli_update_cmd(self.ms_node, package_url,
                                    "epoch={0}".format(new_int))
        self.execute_cli_update_cmd(self.ms_node,
                                    service_url,
                                    "service_name=test289801")

        self.log('info', "Expand the LITP model to include a third node.")
        self.execute_expand_script(self.ms_node,
                                   'expand_cloud_c1_mn3.sh')

        self.log('info', "Find all nodes in the deployment.")
        deployment_urls = \
            self.find(self.ms_node, "/deployments", "node")

        self.log('info', "Group nodes based on their state.")
        applied_nodes = []
        initial_nodes = []
        for url in deployment_urls:
            node_state = \
                self.get_item_state(self.ms_node, url)
            if node_state == 'Applied':
                applied_nodes.append(url)
            elif node_state == "Initial":
                initial_nodes.append(url)

        self.log('info', "Issue the litp create_reboot_plan command.")
        self.execute_cli_create_reboot_plan_cmd(self.ms_node)

        self.log('info', "Execute the show_plan command.")
        stdout, _, _ = \
            self.execute_cli_showplan_cmd(self.ms_node)
        self.log('info', "Ensure all nodes in state Applied are present.")
        for node_url in applied_nodes:
            self.assertTrue(self.is_text_in_list(node_url, stdout),
                            "The following node in state Applied was "
                            "not found in the plan: {0}".format(node_url))
        self.log('info', "Ensure no nodes in state Initial are present.")
        for node_url in initial_nodes:
            self.assertFalse(self.is_text_in_list(node_url, stdout),
                             "The following node in state Initial was "
                             "found in the plan: {0}".format(node_url))

        self.log('info',
                 "Ensure all nodes reboot tasks "
                 "are wrapped in lock/unlock tasks.")
        self.chk_node_wrapped_in_lock_unlock_tasks_in_plan(stdout)

        self.log('info', "Execute the reboot plan.")
        self.execute_cli_runplan_cmd(self.ms_node)
        self.assertTrue(self.wait_for_plan_state(self.ms_node,
                                                 test_constants.PLAN_COMPLETE),
                        "Plan did not complete successfully.")

        for node in self.list_managed_nodes:
            self.wait_for_node_up(node)

        self.log('info', "Cycle through the nodes and "
                         "ensure the uptime shows the node to have rebooted.")
        new_node_uptimes = {}
        for node in self.list_managed_nodes:
            new_node_uptimes = self.chk_node_uptime(node, new_node_uptimes)

        self.compare_uptimes(starting_node_uptimes, new_node_uptimes)

        self.log('info', "Ensure that the LITP model "
                         "items are still in state Updated.")
        self.assertEqual('Updated',
                         self.get_item_state(self.ms_node, package_url),
                         "Item {0} was not in expected "
                         "state of Updated.".format(package_url))
        self.assertEqual('Updated',
                         self.get_item_state(self.ms_node, service_url),
                         "Item {0} was not in expected "
                         "state of Updated.".format(service_url))
