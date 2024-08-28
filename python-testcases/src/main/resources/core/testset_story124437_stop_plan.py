"""
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     September 2016
@author:    Kieran Duggan, Terry Farrell, Maurizio Senno
@summary:   TORF-124437
            As a LITP Architect I want LITP Core Execution Manger to execute
            Run Plan, Callbacks and Config phases as Celery Jobs in parallel
            based off phases from a phase order tree.

"""
from litp_generic_test import GenericTest, attr
import test_constants as const
import os
import time
from paramiko import AuthenticationException
import re


class Story124437StopPlan(GenericTest):
    """
        As a LITP Architect I want LITP Core Execution Manger to execute
        Run Plan, Callbacks and Config phases as Celery Jobs in parallel
        based off phases from a phase order tree.
    """

    def setUp(self):
        """ Runs before every single test """
        super(Story124437StopPlan, self).setUp()
        self.ms1 = self.get_management_node_filename()

        self.cluster2 = {'id': 'c2',
                         'cluster_id': '1043',
                         'script': 'expand_cloud_c2_mn2.sh',
                         'node': 'node2'}

        self.cluster3 = {'id': 'c3',
                         'cluster_id': '1044',
                         'script': 'expand_cloud_c3_mn3.sh',
                         'node': 'node3'}

        self.cluster4 = {'id': 'c4',
                         'cluster_id': '1045',
                         'script': 'expand_cloud_c4_mn4.sh',
                         'node': 'node4'}

        self.restore_sysctl_backup = False
        self.nodes_to_expand = []
        self.clusters_to_expand = []
        self.test_items = []

    def tearDown(self):
        """ Runs after every single test """
        if self.restore_sysctl_backup:
            self.log('info',
            '################# CUSTOM CLEANUP #################')
            mv_cmd = '/bin/mv  /tmp{0} /etc{0}' \
                      .format(const.SYSCTL_CONFIG_FILE)
            sysctl_cmd = '/sbin/sysctl -p {0}'.format(const.SYSCTL_CONFIG_FILE)
            for node in sorted(self.get_managed_node_filenames()):
                self.run_command(node, mv_cmd, su_root=True)
                self.run_command(node, sysctl_cmd, su_root=True)

        super(Story124437StopPlan, self).tearDown()

    def _expand_model(self, cluster_coll_url):
        """
        Description:
            Execute the expand scripts to add clusters and nodes to the model.
            This method does not include the running of the deployment plan
        Args:
            cluster_coll_url (str): URL of the collection-of-cluster item
        """
        for cluster in self.clusters_to_expand:
            self.nodes_to_expand.append(cluster['node'])

            cluster['url'] = '{0}/{1}'.format(cluster_coll_url, cluster['id'])

            props = ('cluster_type=sfha '
                     'low_prio_net=mgmt '
                     'llt_nets=hb1,hb2 '
                     'cluster_id={0}'.format(cluster['cluster_id']))

            self.execute_cli_create_cmd(self.ms1,
                                        cluster['url'],
                                        'vcs-cluster',
                                        props=props)

        for cluster in self.clusters_to_expand:
            self.execute_expand_script(self.ms1, cluster['script'])

    def _ensure_correct_multi_cluster_env_is_available(self):
        """
        Check if the deployment is multi cluster. Expand if not.
        """
        self.log('info', 'Testset requires multi cluster environment')
        clusters = self.find(self.ms1, '/deployments', 'vcs-cluster')
        if len(clusters) == 1:
            self.log('info', 'Expanding to multi cluster environment')
            cluster_collect_url = self.find(self.ms1,
                                        '/deployments',
                                        'cluster',
                                        False)[0]

            self._expand_model(cluster_collect_url)

            self.run_and_check_plan(self.ms1,
                                    const.PLAN_COMPLETE,
                                    plan_timeout_mins=60,
                                    add_to_cleanup=False)
        elif all(
            [self.get_item_state(self.ms1, c) == 'Applied' for c in clusters]):
            self.log('info',
                'Found {0} Applied cluster environment'.format(len(clusters)))
        else:
            self.fail('Found incompatible cluster  environment')

    def _create_firewall_test_items(self, number_of_items):
        """
        Description:
            plan to create some firewall rules on each node in each cluster
            which should result in some parallel phase execution during
            deployment
        Args:
            number_of_items (int): the number of items to create
        """
        self.test_items = []
        clusters = self.find(self.ms1, '/deployments', 'vcs-cluster')
        for cluster_uri in sorted(clusters):
            node_uri = self.find(self.ms1, cluster_uri, 'node')[0]
            fw_coll_uri = self.find(self.ms1,
                                    node_uri,
                                    'collection-of-firewall-rule')[0]

            for i in range(1, number_of_items + 1):
                item = {}
                item['id'] = 'story124437_{0}'.format(i)
                item['url'] = os.path.join(fw_coll_uri, item['id'])
                item['type'] = 'firewall-rule'
                item['props'] = 'name="77{0} story124437"'.format(i)

                self.execute_cli_create_cmd(self.ms1,
                                            item['url'],
                                            item['type'],
                                            item['props'])

                self.test_items.append(item)

    @staticmethod
    def _is_parallel_plan_state_reached(
            phases_with_running_tasks, skip_vcs_task=True):
        """
        Description:
            Count the phases with running task to determine if parallel
            execution is happening
        Args:
            phases_with_running_tasks (dict): Data of the phases of the plan
                                              with currently running tasks
            skip_vcs_task (bool): Allow to ignore VCS lock/unlock tasks
        Return:
            bool, True if more than one phase is found
        """
        phases = []
        for phase, clusters in phases_with_running_tasks.iteritems():
            for tasks in clusters.values():
                for task in tasks:
                    if skip_vcs_task and 'VCS' in task.get('desc'):
                        continue
                    phases.append(phase)
        if len(set(phases)) > 1:
            return True
        return False

    def _wait_for_conditions(self, conditions, timeout, poll_interval):
        """
        Description:
            Wait for specified condition to be met
        Args:
            conditions (func): The logic to apply to verify the condition
            timeout (int): Timeout in seconds1
            poll_interval (int): The interval between polls in seconds
        Return:
            Data that describe how the condition has been met as returned by
            the call to conditions() function
        """
        start_time = time.time()
        while True:
            iteration_start_time = time.time()
            elapsed_time = int(iteration_start_time - start_time)
            self.assertTrue(elapsed_time < timeout,
                'Timeout reached while waiting for "{0}"'
                .format(conditions.__name__))

            self.log('info',
            'Waiting for condition "{0}" to be met. Remaining time: {1}s'
            .format(conditions.__name__, int(timeout - elapsed_time)))

            result = conditions()

            if result:
                return result

            sleep_time = poll_interval - (time.time() - iteration_start_time)
            if sleep_time > 0:
                time.sleep(sleep_time)

    def _multiple_phases_running(self):
        """
            Determine if there are multiple phase running at same time
        """
        plan = self.get_plan_data(self.ms1)
        phases_with_running_tasks = \
                        self.get_tasks_by_state(self.ms1, 'Running', plan)
        if self._is_parallel_plan_state_reached(phases_with_running_tasks):
            return plan
        return {}

    def _log_plan_state_details(self, plan_section):
        """
        Description:
            Pretty print details of the given plan section
        Args:
            plan_section (dict): Any subset of plan phases data obtained by
                                 filtering the plan data retuned by
                                 get_plan_data(). This could by all the phases
                                 with "Running" tasks for example.

        Example of expected plan_section structure:
            {'state': 'running',
             'phases':
                 '2':
                    {'c1':
                        [
                           {'desc':'Install package "finger" on node "node1"',
                            'url':'http://......',
                            'state': 'Initial'},
                           {'desc':'Install package "firefox" on node "node2"',
                            'url':'http://......',
                            'state': 'Initial'}
                        ]
                    }
             }
        """
        log_data = []

        if plan_section.get('phases'):
            phase_data = plan_section['phases']
            log_data.append('Plan state: {0}'
                            .format(plan_section.get('state')))
        else:
            phase_data = plan_section

        for phase, clusters in sorted(phase_data.iteritems()):
            log_data.append('{0}'.format(phase))
            for cluster, tasks in sorted(clusters.iteritems()):
                log_data.append('  {0}'.format(cluster))
                for task in tasks:
                    log_data.append(
                        '    {0:<8}{1}'
                        .format(task.get('state'), task.get('url')))
                    log_data.append(
                        '    {0:<8}{1}'.format(' ', task.get('desc')))

        if log_data:
            self.log('info', '-' * 80)
            for line in log_data:
                self.log('info', line)
            self.log('info', '-' * 80)

    def _set_credentials_on_peer_nodes(self):
        """
            Set litp-admin and root passwords on peer nodes
        """
        node_names = self.get_managed_node_filenames()
        node_names.sort()

        for node in node_names:
            # Check if credential are already set
            rc = None
            try:
                _, _, rc = self.run_command(node, 'date', su_root=True)
            except AuthenticationException:
                pass
            if rc != 0:
                self.assertTrue(self.set_pws_new_node(self.ms1, node),
                                'Failed to set password on node "{0}"'
                                .format(node))
        return node_names

    def _running_phases_completed(self, phases, expected_states):
        """
        Description:
            Closure function generator for running_phases_completed()
        Args:
            phases (list): Phases we want to check
            expected_states (list): List of task state that defines a completed
                                    phase
        """
        def running_phases_completed():
            """
                Check if all tasks in the given phases are in the expected
                state
            """
            plan = self.get_plan_data(self.ms1)
            for phase in phases:
                for tasks in plan['phases'][phase].values():
                    for task in tasks:
                        if task.get('state') not in expected_states:
                            return {}
            return plan
        return running_phases_completed

    def _multiple_phases_running_and_task_failed(self):
        """
            Check if there are phases running in parallel and at least one
            task failed
        """
        plan = self.get_plan_data(self.ms1)

        failed_tasks = self.get_tasks_by_state(self.ms1, 'Failed', plan)
        if failed_tasks == {}:
            return {}

        phases_with_running_tasks = \
                        self.get_tasks_by_state(self.ms1, 'Running', plan)
        if self._is_parallel_plan_state_reached(phases_with_running_tasks):
            return plan
        return {}

    @attr('manual-test', 'non-revert', 'expansion', 'story124437',
          'story124437_stop_plan', 'story124437_stop_plan_tc01')
    def test_01_p_stop_plan_recreate_plan(self):
        """
        @tms_id: torf_124437_stop_plan_tc_01
        @tms_requirements_id: TORF-124437
        @tms_title:
            Verify that a parallel plan execution can be stopped
        @tms_description:
            Verify that while a plan with multiple clusters being deployed
            in parallel is running, if I issue the "litp stop_plan" command,
            currently running tasks in all running phases run to completion
            and then the plan stops.
            If I recreate and rerun the plan, the plan regenerates from the
            point it was stopped and run to completion with any cluster
            specific phases run in parallel.
        @tms_test_steps:
        @step: Check test environment
        @result: Test environment is correct
        @step: Create a plan to deploy new items that will result in parallel
               phase plan execution
        @result: Plan created successfully
        @step: Start the plan and wait for parallel cluster task execution
        @result: Parallel execution of phases reached
        @step: Stop the plan by issuing the "litp stop_plan" command
        @result: Plan stopped successfully
        @result: Each task that was running when plan was stopped completed
                 successfully
        @step: Re-create and run the plan
        @result: Plan completed successfully

        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """

        #This test is not run in the KGB as it leaves the system in a state
        #that is different to what was found in ('non-revert')

        self.log('info',
        '1. Ensure multi cluster environment is deployed')
        self.clusters_to_expand = [self.cluster2, self.cluster3, self.cluster4]
        self._ensure_correct_multi_cluster_env_is_available()

        self.log('info',
        '2. Create and new items whose deployment will result in parallel '
            'phase plan execution')
        self._create_firewall_test_items(5)

        self.log('info',
        '3. Start the plan and wait for parallel cluster task execution')
        self.execute_cli_createplan_cmd(self.ms1)
        self.execute_cli_runplan_cmd(self.ms1)

        plan_at_stop = self._wait_for_conditions(
                                            self._multiple_phases_running,
                                            timeout=120,
                                            poll_interval=1)

        self.log('info',
        '4. Stop the plan')
        self.execute_cli_stopplan_cmd(self.ms1)

        self.log('info',
        '5. Wait for all tasks in the running phases to complete')
        tasks_running_at_stop = self.get_tasks_by_state(
                                                    self.ms1,
                                                    'Running',
                                                    plan_data=plan_at_stop)
        running_phases_at_stop = tasks_running_at_stop.keys()
        phase_complete_plan = self._wait_for_conditions(
            self._running_phases_completed(running_phases_at_stop,
                                           ['Success']),
            timeout=240,
            poll_interval=1)

        self.log('info',
        '6. Wait for plan to transition to "Stopped"')
        self.wait_for_plan_state(self.ms1, const.PLAN_STOPPED, 5)

        self.log('info',
        '7. Check that plan state is correct')
        plan_at_stopped = self.get_plan_data(self.ms1)

        tasks_initial_at_stopped = self.get_tasks_by_state(
                                                    self.ms1,
                                                    'Initial',
                                                    plan_data=plan_at_stopped)

        self.log('info',
        'Plan state when the "stop_plan" command was issued')
        self._log_plan_state_details(plan_at_stop)

        self.log('info',
        'Plan state when the "Stopped" state was reached')
        self._log_plan_state_details(plan_at_stopped)

        self.log('info',
        'Check that all tasks that were running when the "stop_plan" was '
        'issued have are in "Success" state')
        for phase in tasks_running_at_stop.keys():
            for tasks in plan_at_stopped['phases'][phase].values():
                for task in tasks:
                    self.assertEqual('Success', task.get('state'))

        self.log('info',
        'Check that no new phases were started after the phases that had '
        'running task when the "stop_plan" was issued completed')
        tasks_initial_at_complete = \
            self.get_tasks_by_state(self.ms1, 'Initial', phase_complete_plan)

        self.assertEqual(sorted(tasks_initial_at_stopped.keys()),
                         sorted(tasks_initial_at_complete.keys()))

        self.log('info',
        '8. (Re)Create and Run plan')
        self.execute_cli_createplan_cmd(self.ms1)
        self.execute_cli_runplan_cmd(self.ms1)
        self.wait_for_plan_state(self.ms1, const.PLAN_COMPLETE, 5)

    @attr('manual-test', 'non-revert', 'story124437',
          'story124437Fail_one_config_task',
          'story124437Fail_one_config_task_tc03', 'expansion')
    def test_03_p_config_task_failure_handling(self):
        """
        @tms_id: torf_124437_stop_plan_tc_03
        @tms_requirements_id: TORF-124437
        @tms_title: Task failure handling
        @tms_description: Verify that when multiple phases are running in
            parallel and at least one task in one phase fails all the running
            tasks run to completion and no new phases are started
        @tms_test_steps:
        @step: Create multi cluster environment if required
        @result: multi cluster environment created
        @step: Create some valid test items
        @result: Items created successfully
        @step: Create multiple invalid test items which will cause the plan
               to fail
        @result: Item created successfully
        @step: Create and run plan
        @result: Plan is in "Running" state
        @step: Wait for multiple phase running in parallel and one task to fail
        @result: Required preconditions met
        @result: Plan still in "Running" state
        @step: Wait for phases that were running at failure time to complete
        @result: All tasks completed
        @result: Plan is in "Failed" state
        @result: All tasks that were in "Running" state at time of failure are
                 in "Success" state
        @result: All tasks that were in "Initial" state when all running phases
                 completed are still at "Initial" state

        @tms_test_precondition: parallel running phases
            with simultaneous failed and running tasks in independent clusters
        @tms_execution_type: Automated
        """

        #This test is not run in the KGB as it leaves the system in a state
        #that is different to what was found in ('non-revert')

        self.clusters_to_expand = [self.cluster2, self.cluster3, self.cluster4]
        self.log('info',
        '1. Create multi cluster environment if required')
        self._ensure_correct_multi_cluster_env_is_available()

        self.log('info',
        '2. Set up credential on peer nodes')
        node_names = self._set_credentials_on_peer_nodes()

        self.log('info',
        '3. Create backup of sysctl file of each peer node')
        self.restore_sysctl_backup = True
        for node in node_names:
            self.assertTrue(self.backup_file(node, const.SYSCTL_CONFIG_FILE))

        self.log('info',
        '4. Create new firewall rules on cluster "c2" and "c3" and "c4"')
        self._create_firewall_test_items(1)
        # self._create_logrotate_test_items(5)

        self.log('info',
        '5. Create valid and invalid sysparam items on each peer node')
        sysparam_config_urls = self.find(self.ms1,
                                         '/deployments',
                                         'sysparam-node-config')
        sysparam_config_urls.sort()
        valid_keys = ['key="net.ipv4.ip_forward" value="11"',
                      'key="kernel.msgmnb" value="65534"']
        invalid_key = \
                'key="net.ipv4.conf.default.mc_forwarding" value="01 new"'

        for i, node in enumerate(sysparam_config_urls):
            item = {}
            item['id'] = 'story124437_sysparam_Valid_{0}'.format(i)
            item['url'] = '{0}/params/{1}'.format(node, item['id'])
            item['type'] = 'sysparam'
            item['props'] = valid_keys[0]
            self.execute_cli_create_cmd(self.ms1,
                                        item['url'],
                                        item['type'],
                                        props=item['props'])
            self.test_items.append(item)

            invalid_item = {}
            invalid_item['id'] = 'story124437_sysparam_Invalid_0'
            invalid_item['url'] = '{0}/params/{1}' \
                                  .format(node, invalid_item['id'])
            invalid_item['type'] = 'sysparam'
            invalid_item['props'] = invalid_key
            self.execute_cli_create_cmd(self.ms1,
                                        invalid_item['url'],
                                        invalid_item['type'],
                                        props=invalid_item['props'])
            self.test_items.append(invalid_item)

        self.log('info',
        '7. Create and run plan and wait for parallel phase with failed task '
           'plan state')
        self.execute_cli_createplan_cmd(self.ms1)
        self.execute_cli_showplan_cmd(self.ms1)
        self.execute_cli_runplan_cmd(self.ms1)

        plan_at_fail = self._wait_for_conditions(
                            self._multiple_phases_running_and_task_failed,
                            timeout=240,
                            poll_interval=1)

        failed_tasks = self.get_tasks_by_state(self.ms1,
                                               'Failed',
                                               plan_at_fail)

        running_tasks_at_fail = self.get_tasks_by_state(self.ms1,
                                                       'Running',
                                                        plan_at_fail)

        self.log('info', 'Failed tasks')
        self._log_plan_state_details(failed_tasks)

        self.log('info', 'Running tasks at fail')
        self._log_plan_state_details(running_tasks_at_fail)

        self.log('info',
        '8. Wait for phases that were running at fail complete')
        running_phases_at_fail = running_tasks_at_fail.keys()
        statuses = ['Success', 'Failed']
        plan_at_phase_complete = self._wait_for_conditions(
            self._running_phases_completed(running_phases_at_fail, statuses),
            timeout=240,
            poll_interval=1)
        tasks_that_should_stay_initial = self.get_tasks_by_state(
                                                    self.ms1,
                                                    'Initial',
                                                    plan_at_phase_complete)

        self.log('info',
        '8. Wait for plan to fail and check task statuses')
        self.wait_for_plan_state(self.ms1, const.PLAN_FAILED, 5)
        failed_plan = self.get_plan_data(self.ms1)
        self._log_plan_state_details(failed_plan)

        self.log('info',
        'Check that all tasks that were running when the task failed are in '
        '"Success" state')
        invalid_item_regex = re.compile('Invalid')
        for phase in running_phases_at_fail:
            for tasks in plan_at_phase_complete['phases'][phase].values():
                for task in tasks:
                    self.log('info',
                    '{0} - {1}'.format(task.get('state'), task.get('url')))

                    if invalid_item_regex.search(task.get('url')):
                        self.assertEqual('Failed', task.get('state'))
                    else:
                        self.assertEqual('Success', task.get('state'))

        self.log('info',
        'Check that all tasks that were "Initial" when all running phases '
        'completed are still at "Initial" state')
        for phase in tasks_that_should_stay_initial.keys():
            for tasks in failed_plan['phases'][phase].values():
                for task in tasks:
                    self.log('info',
                    '{0} - {1}'.format(task.get('state'), task.get('url')))
                    self.assertEqual('Initial', task.get('state'))

    @attr('manual-test', 'non-revert', 'story124437',
          'story124437Fail_one_config_task',
          'story124437Fail_one_config_task_tc04', 'expansion')
    def test_04_p_stop_plan_while_failing(self):
        """
        @tms_id: torf_124437_stop_plan_tc_04
        @tms_requirements_id: TORF-124437
        @tms_title: Stop plan that is failing
        @tms_description: Verify that when multiple phases are running in
            parallel and multiple tasks in different phases fail all the
            running tasks run to completion and no new phases are started.
            Also verify that if "litp stop_plan" command is issued right after
            the failures and before the plan transitions to "Failed" then the
            plan eventually transitions to "Stopped"
        @tms_test_steps:
        @step: Create multi cluster environment if required
        @result: multi cluster environment created
        @step: Create some valid test items
        @result: Items created successfully
        @step: Create multiple invalid test items which will cause the plan
               to fail
        @result: Item created successfully
        @step: Create and run plan
        @result: Plan is in "Running" state
        @step: Wait for multiple phase running in parallel and at least one
               task to fail
        @result: Required preconditions met
        @result: Plan still in "Running" state
        @step: Issue the "litp stop_plan" command
        @result: Command executed successfully
        @result: Plan is in "Stopping" state
        @step: Wait for phases that were running at failure time to complete
        @result: All tasks completed
        @result: Plan is in "Stopped" state
        @result: All tasks that were in "Running" state at time of failure are
                 in "Success" state
        @result: All tasks that were in "Initial" state when all running phases
                 completed are still at "Initial" state

        @tms_test_precondition: parallel running phases
            with simultaneous failed and running tasks in independent clusters
        @tms_execution_type: Automated
        """

        #This test is not run in the KGB as it leaves the system in a state
        #that is different to what was found in ('non-revert')

        self.clusters_to_expand = [self.cluster2, self.cluster3, self.cluster4]
        self.log('info',
        '1. Create multi cluster environment if required')
        self._ensure_correct_multi_cluster_env_is_available()

        self.log('info',
        '2. Set up credential on peer nodes')
        node_names = self._set_credentials_on_peer_nodes()

        self.log('info',
        '3. Create backup of sysctl file of each peer node')
        self.restore_sysctl_backup = True
        for node in node_names:
            self.assertTrue(self.backup_file(node, const.SYSCTL_CONFIG_FILE))

        self.log('info',
        '4. Create new firewall rules on cluster "c2" and "c3" and "c4"')
        self._create_firewall_test_items(4)

        self.log('info',
        '5. Create valid and invalid sysparam items on each peer node')
        sysparam_config_urls = self.find(self.ms1,
                                         '/deployments',
                                         'sysparam-node-config')
        sysparam_config_urls.sort()
        valid_keys = ['key="net.ipv4.ip_forward" value="11"',
                      'key="kernel.msgmnb" value="65534"']
        invalid_key = \
                'key="net.ipv4.conf.default.mc_forwarding" value="01 new"'

        for i, node in enumerate(sysparam_config_urls):
            item = {}
            item['id'] = 'story124437_sysparam_Valid_{0}'.format(i)
            item['url'] = '{0}/params/{1}'.format(node, item['id'])
            item['type'] = 'sysparam'
            item['props'] = valid_keys[0]
            self.execute_cli_create_cmd(self.ms1,
                                        item['url'],
                                        item['type'],
                                        props=item['props'])
            self.test_items.append(item)

            invalid_item = {}
            invalid_item['id'] = 'story124437_sysparam_Invalid_0'
            invalid_item['url'] = '{0}/params/{1}' \
                                  .format(node, invalid_item['id'])
            invalid_item['type'] = 'sysparam'
            invalid_item['props'] = invalid_key
            self.execute_cli_create_cmd(self.ms1,
                                        invalid_item['url'],
                                        invalid_item['type'],
                                        props=invalid_item['props'])
            self.test_items.append(invalid_item)

        self.log('info',
        '6. Create and run plan and wait for parallel phase with failed task '
           'plan state')
        self.execute_cli_createplan_cmd(self.ms1)
        self.execute_cli_showplan_cmd(self.ms1)
        self.execute_cli_runplan_cmd(self.ms1)

        plan_at_fail = self._wait_for_conditions(
                            self._multiple_phases_running_and_task_failed,
                            timeout=240,
                            poll_interval=1)

        failed_tasks = self.get_tasks_by_state(self.ms1,
                                               'Failed',
                                               plan_at_fail)

        running_tasks_at_fail = self.get_tasks_by_state(self.ms1,
                                                       'Running',
                                                        plan_at_fail)

        self.log('info', 'Failed tasks')
        self._log_plan_state_details(failed_tasks)

        self.log('info', 'Running tasks at fail')
        self._log_plan_state_details(running_tasks_at_fail)

        self.log('info',
        '7. Issue the "litp stop_plan" command')
        self.execute_cli_stopplan_cmd(self.ms1)

        self.log('info',
        '8. Wait for phases that were running at fail complete')
        running_phases_at_fail = running_tasks_at_fail.keys()
        statuses = ['Success', 'Failed']
        plan_at_phase_complete = self._wait_for_conditions(
            self._running_phases_completed(running_phases_at_fail, statuses),
            timeout=240,
            poll_interval=1)
        tasks_that_should_stay_initial = self.get_tasks_by_state(
                                                    self.ms1,
                                                    'Initial',
                                                    plan_at_phase_complete)

        self.log('info',
        '9. Wait for plan to fail and check task statuses')
        self.wait_for_plan_state(self.ms1, const.PLAN_STOPPED, 5)
        failed_plan = self.get_plan_data(self.ms1)
        self._log_plan_state_details(failed_plan)

        self.log('info',
        'Check that all tasks that were running when the task failed are in '
        'the correct state')
        invalid_item_regex = re.compile('Invalid')
        for phase in running_phases_at_fail:
            for tasks in plan_at_phase_complete['phases'][phase].values():
                for task in tasks:
                    self.log('info',
                    '{0} - {1}'.format(task.get('state'), task.get('url')))

                    if invalid_item_regex.search(task.get('url')):
                        self.assertEqual('Failed', task.get('state'))
                    else:
                        self.assertEqual('Success', task.get('state'))

        self.log('info',
        'Check that all tasks that were "Initial" when all running phases '
        'completed are still at "Initial" state')
        for phase in tasks_that_should_stay_initial.keys():
            for tasks in failed_plan['phases'][phase].values():
                for task in tasks:
                    self.log('info',
                    '{0} - {1}'.format(task.get('state'), task.get('url')))
                    self.assertEqual('Initial', task.get('state'))
