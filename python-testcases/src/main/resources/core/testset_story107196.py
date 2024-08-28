"""
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     Jul 2016; Refactored Feb 2019
@author:    Roman Jarzebiak; Aisling Stafford
@summary:   TORF-107196
            As a LITP Architect I want LITP Core's Puppet Manager to access
            PuppetDb feedback during a Run Plan Operation
"""
from litp_generic_test import GenericTest, attr
import test_constants as const
from rest_utils import RestUtils


class Story107196(GenericTest):
    """
    As a LITP Architect I want LITP Core's Puppet Manager to access PuppetDb
    feedback during a Run Plan Operation
    """

    def setUp(self):
        """ Runs before every single test """
        super(Story107196, self).setUp()
        self.ms_node = self.get_management_node_filename()
        self.ms_ip = self.get_node_att(self.ms_node,
                                            const.NODE_ATT_IPV4)
        self.peer_nodes = self.get_managed_node_filenames()
        self.puppet_conf = const.PUPPET_CONFIG_FILE
        self.rest = RestUtils(self.ms_ip)

        self.ms_firewall_rules = self.find(self.ms_node,
                            '/ms',
                            'collection-of-firewall-rule')[0]

        self.n1_firewall_rules = self.find(self.ms_node,
                            '/deployments',
                            'collection-of-firewall-rule')[1]

        self.fw_rule_path_name = 'fw_story_107196'
        self.fw_rule_name = '550 story107196'

    def tearDown(self):
        """ Runs after every single test """
        super(Story107196, self).tearDown()

    def create_fw_rule(self, node_fw_path):
        """
        Description:
        Creates a firewall rule on the selected node.

        Args:
        node_fw_path (str): Path to node firewall rules

        returns:
        fw_path (str): full path to the created fw rule
        """

        fw_path = '{0}/{1}'.format(node_fw_path, self.fw_rule_path_name)

        self.execute_cli_create_cmd(self.ms_node,
                                        fw_path,
                                       'firewall-rule',
                                       'name="{0}"'.format(self.fw_rule_name))
        return fw_path

    def assert_task_state(self, task, expected_state):
        """
        Description: Waits for task to reach it's expected state and
                     asserts it is as expected
        Args:
            task (str): task to wait for
            expected_state (int): id of expected task state
        """

        self.assertTrue(self.wait_for_task_state(self.ms_node, task,
                        expected_state,
                        ignore_variables=False, timeout_mins=30),
                        'Task "{0}" not in expected '
                        'state "{1}"'.format(task, expected_state))

    @attr('all', 'revert', 'story107196', 'story107196_tc04')
    def test_04_n_no_puppet_feedback_uri(self):
        """
        @tms_id: litpcds_107196_tc04
        @tms_requirements_id: TORF-107196
        @tms_title: No puppet feedback uri
        @tms_description: Verify that the obsoleted
            "/execution/puppet_feedback" uri is removed and sending a request
            to it results with a 404 response code.
        @tms_test_steps:
         @step: on the ms do POST request to
            https://127.0.0.1:9999/execution/puppet_feedback"
         @result: 404 returned
        @tms_test_precondition: DB litp installed.
        @tms_execution_type: Automated
        """

        http_status = self.rest.get('/execution/puppet_feedback')[2]

        self.assertEqual(http_status, 404, '/execution/puppet_feedback path '
                                           'shouldn\'t exist')

    @attr('all', 'revert', 'story107196', 'story107196_tc06')
    def test_06_p_no_landscape_reference_in_puppet_conf(self):
        """
        @tms_id: litpcds_107196_tc06
        @tms_requirements_id: TORF-107196
        @tms_title: no landscape reference in puppet config
        @tms_description: Verify that the obsoleted landscape.rb file is not
            referenced in reports section of the /etc/puppet/puppet.conf file
            on a freshly installed LITP system or system was upgraded to db.
        @tms_test_steps:
         @step: look for reports section in the /etc/puppets/puppet.conf file
         @result: no landscape reference
        @tms_test_precondition: DB litp installed.
        @tms_execution_type: Automated
        """

        reports = self.g_util.get_prop_from_file(
            self.get_file_contents(self.ms_node, self.puppet_conf),
            'reports')

        self.assertFalse('landscape' in reports, "Unexpected reference to "
                         "landscape in reports section of puppet config"
        )

    @attr('all', 'revert', 'story107196', 'story107196_tc08')
    def test_08_n_kill_puppedb_while_plan_is_running_ms(self):
        """
        @tms_id: litpcds_107196_tc08
        @tms_requirements_id: TORF-107196
        @tms_title: puppetdb disabled while plan is running with MS and peer
                    node tasks
        @tms_description: Verify that if puppetdb will be disabled while a plan
            is running then puppet will restart puppetdb on MS and plan will
            run to completion. This test covers litpcds_107196_tc09.
        @tms_test_steps:
         @step: Create a dummy firewall rule on the MS and create a plan
         @result: MS firewall rule and plan are created
         @step: Wait until puppet idle and run previously created plan
         @result: puppet run completes and plan is running
         @step: Wait until the MS task is running, kill puppetdb on the MS and
                wait for task to be successful
         @result: puppetdb is killed, and is restarted by puppet. MS task
                  is successful
         @step: Wait until plan is successful
         @result: plan completes successfully
         @step: Create a dummy firewall rule on a peer node and create a plan
         @result: node firewall rule and plan are created
         @step: Wait until puppet idle and run previously created plan
         @result: puppet run completes and plan is running
         @step: Wait until the peer node task is running, kill puppetdb on
                the MS and wait for task to be successful
         @result: puppetdb is killed, and is restarted by puppet. peer node
                  task is successful
         @step: Wait until plan is successful
         @result: plan completes successfully
         @step: Check puppetdb is back up, all rules applied and the new
                firewall rule exists on the MS and peer node
         @result: puppetdb up and running
         @result: new rules are in applied state
         @result: new firewall rule exists on the ms
        @tms_test_precondition: N/A
        @tms_execution_type: Automated
        """

        try:
            orig_runinterval_value = self.set_puppet_runinterval(self.ms_node,
                                                                 "720")

            fw_rules = {self.ms_firewall_rules: self.ms_node,
                        self.n1_firewall_rules: self.peer_nodes[0]}

            rule_paths = []
            log_pos = 1
            for rule, node in fw_rules.iteritems():

                self.log('info', '{0}. Create a dummy firewall rule on {1} '
                         'then create a plan.'.format(log_pos, node))

                rule_path = self.create_fw_rule(rule)
                rule_paths.append(rule_path)

                self.execute_cli_createplan_cmd(self.ms_node)

                self.log('info', '{0}. Wait until puppet idle and run '
                         'previously created plan'.format(log_pos + 1))

                self.wait_for_puppet_idle(self.ms_node)
                self.execute_cli_runplan_cmd(self.ms_node)

                plan_task = 'Add firewall rule "550 story107196" on node'\
                                ' "{0}"'.format(node)

                self.log('info', '{0}. Wait until task "{1}" is running, '
                             'kill puppetdb on the MS and wait for task to be '
                     'successful'.format(log_pos + 2, plan_task))

                self.assert_task_state(plan_task, const.PLAN_TASKS_RUNNING)
                self.stop_service(self.ms_node, 'puppetdb',
                                      kill_service=True)
                self.assert_task_state(plan_task, const.PLAN_TASKS_SUCCESS)

                self.log('info', '{0}. Wait until the plan is '
                         'successful'.format(log_pos + 3))
                self.assertTrue(
                self.wait_for_plan_state(self.ms_node, const.PLAN_COMPLETE,
                                         timeout_mins=30),
                                        "Plan did not complete successfully")
                log_pos = 5

            self.log('info', '8. Check puppetdb is back up, all rules applied '
                         'and the new firewall rule exists on the MS and '
                         'peer node')

            self.get_service_status(self.ms_node, 'puppetdb',
                                    assert_running=True)

            for rule in rule_paths:
                self.assertTrue(self.is_expected_state(self.ms_node, rule,
                                'Applied'),
                                'Rule not in "Applied" state as expected')

            for node in [self.ms_node, self.peer_nodes[0]]:
                self.check_iptables(node, self.fw_rule_name)
        finally:
            self.set_puppet_runinterval(self.ms_node, orig_runinterval_value)

    #attr('all', 'revert', 'story107196', 'story107196_tc09')
    def obsolete_09_n_kill_puppedb_while_plan_is_running_mn(self):
        """
        #tms_id: litpcds_107196_tc09
        #tms_requirements_id: TORF-107196
        #tms_title: puppetdb disabled while plan is running with node tasks
        #tms_description: Verify that if puppetdb will be disabled while a plan
            is running then the plan runs untill puppetdb comes back up and
            plan runs till completion.
        #tms_test_steps:
         #step: wait for puppet run to complete
         #result: puppet run completes
         #step: run previously created plan
         #result: plan is running
         #step: kill -9 puppetdb on the ms
         #result: puppetdb is not running
         #step: wait till plan is successfull
         #result: plan successful
         #result: all items in applied state
         #result: new firewall rule exists on the node
        #tms_test_precondition: DB litp installed, valid deployment plan
            created that has tasks on managed nodes
        #tms_execution_type: Automated

         Reason for obsoletion: Merged logic with
            story107196.test_08_n_kill_puppedb_while_plan_is_running_ms
        """
        pass
