"""
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     September 2016
@author:    Maurizio Senno
@summary:   TORF-124437
            As a LITP Architect I want LITP Core Execution Manger to execute
            Run Plan, Callbacks and Config phases as Celery Jobs in parallel
            based off phases from a phase order tree.
"""
from redhat_cmd_utils import RHCmdUtils
from litp_generic_test import GenericTest, attr
import test_constants as const
import os
import re
import time


class Story124437KillServices(GenericTest):
    """
        As a LITP Architect I want LITP Core Execution Manger to execute
        Run Plan, Callbacks and Config phases as Celery Jobs in parallel
        based off phases from a phase order tree.
    """

    def setUp(self):
        """ Runs before every single test """
        super(Story124437KillServices, self).setUp()
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

        self.skip_cleanup = False
        self.terminate = False
        self.rhel = RHCmdUtils()
        self.test_items = []
        self.nodes_to_expand = []
        self.clusters_to_expand = []
        self.celery_default_reg = \
            re.compile(r'celeryd \(node litpDefault\) \(pid [0-9]+\) is up...')
        self.celery_plan_reg = \
            re.compile(r'celeryd \(node litpPlan\) \(pid [0-9]+\) is up...')
        self.celery_task_reg = \
            re.compile(r'celeryd \(node litpTask\) \(pid [0-9]+\) is up...')
        self.celery_workers = [self.celery_default_reg,
                               self.celery_plan_reg,
                               self.celery_task_reg]
        self.plan_mode = ''

    def tearDown(self):
        """ Runs after every single test """
        if not self.skip_cleanup:
            super(Story124437KillServices, self).tearDown()
        else:
            self.log('info',
            'CLEAN UP procedure has been disabled for this test')

    def _update_litpd_conf_file(self, params):
        """
        Description:
        Update the value of the specified parameters in the litpd.conf

        Args:
        params (dict): Dict of param/value pairs

        Returns:
        dict, original value of the specified parameters
        """
        initial_conf = {}
        for param, value in params.iteritems():
            grep_string = '^{0}'.format(param)
            cmd = self.rhel.get_grep_file_cmd(const.LITPD_CONF_FILE,
                                              grep_string)
            matching_lines = self.run_command(self.ms1,
                                              cmd,
                                              default_asserts=True)[0]
            if len(matching_lines) == 1:
                line_to_update = matching_lines[0]
            else:
                self.fail('Found more than one line matching the parameter '
                          '"{0}" in "{1}"'.
                           format(param, const.LITPD_CONF_FILE))

            initial_val = re.match(r'\w+ = (\d+)', line_to_update).group(1)
            initial_conf[param] = initial_val

            new_line = '{0} = {1}'.format(param, value)
            cmd = "/bin/sed -i 's/^{0}/{1}/g' {2}". \
                  format(line_to_update, new_line, const.LITPD_CONF_FILE)
            self.run_command(self.ms1, cmd, su_root=True, default_asserts=True)

        # Restart celeryd service so changes take effect
        self.stop_service(self.ms1, 'celeryd')
        self.start_service(self.ms1, 'celeryd')

        return initial_conf

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

    def _create_parallel_capable_plan(self):
        """
        plan to create some firewall rules on each node in each cluster
        which should result in some parallel phase execution during
        deployment
        """
        self.test_items = []
        clusters = self.find(self.ms1, '/deployments', 'vcs-cluster')
        for cluster_uri in clusters:
            node_uri = self.find(self.ms1, cluster_uri, 'node')[0]
            fw_coll_uri = self.find(self.ms1,
                                    node_uri,
                                    'collection-of-firewall-rule')[0]

            for i in range(1, 5):
                item = {}
                item['id'] = 'story124437_{0}'.format(i)
                item['url'] = os.path.join(fw_coll_uri, item['id'])
                item['type'] = 'firewall-rule'
                item['props'] = 'name="77{0} story124437"'.format(i)
                item['cleanup'] = True
                self.test_items.append(item)

        self._change_the_model()
        self.execute_cli_createplan_cmd(self.ms1)

    def _change_the_model(self):
        """
            Check the model to determine whether to create new test items or
            remove existing test items
        """
        found = self.find(self.ms1,
                          self.test_items[0]['url'],
                          self.test_items[0]['type'],
                          assert_not_empty=False)
        if found:
            self.plan_mode = 'remove'
        else:
            self.plan_mode = 'create'

        # To ensure that the test environment state is under control
        # we accept two scenarios only:
        # All test_items are to be created
        # All test_items are to be removed
        #
        # Mixed cases will cause the test to fail
        for item in self.test_items:
            if self.plan_mode == 'create':
                self.execute_cli_create_cmd(self.ms1,
                                            item['url'],
                                            item['type'],
                                            item['props'])
            elif self.plan_mode == 'remove':
                self.execute_cli_remove_cmd(self.ms1,
                                            item['url'])

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

    def _kill_celery_queue(self, node, queue, kill_args='', su_root=False):
        """
        Description:
            Kill all celery worker processes
        Args:
            node (str): The node where to kill the processes
            queue (str): The name of the celery process
            kill_args (str): Allow to specify additional kill parameters
            su_root (bool): Specify if su to root is required
        """
        kill_cmd = "/usr/bin/pkill {0} -f {1}".format(kill_args, queue)
        return self.run_command(node, kill_cmd, su_root=su_root)

    def _wait_for_conditions(self, conditions, timeout, poll_interval):
        """
        Description:
            Wait for specified condition to be met
        Args:
            conditions (func): The logic to apply to verify the condition
            timeout (int): Timeout in seconds
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
        Description:
            Determine if there are multiple phase running at same time
        Return:
            Dict, Data that describe the plan at the time multiple phases are
                  found to be running in parallel. If no phases running in
                  parallel are found return an empty dict.
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

        if plan_section.get('state'):
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
        self.log('info', '-' * 80)
        for line in log_data:
            self.log('info', line)
        self.log('info', '-' * 80)

    def _celery_service_running(self):
        """
        Description:
            Check for the three celery workers (Default, Plan and Task) status
        Return:
            bool, True if all celery workers are up and running
        """
        stdout, _, rc = self.get_service_status(self.ms1,
                                               'celeryd',
                                                assert_running=False)
        if rc != 0:
            return False
        stdout_str = ' '.join(stdout)
        for worker in self.celery_workers:
            if not worker.search(stdout_str):
                return False
        return True

    def _rabbitmq_service_running(self):
        """
        Description:
            Check for the rabbitmq-server status
        Return:
            bool, True if rabbitmq-server is up and running
        """
        stdout, _, rc = self.get_service_status(self.ms1,
                                               'rabbitmq-server',
                                                assert_running=False)
        if rc != 0:
            return False
        if self.is_text_in_list('uptime', stdout):
            return True
        return False

    def _check_service_status(self, service, statuses):
        """
        Description:
            Parses the output of service status
        Args:
            service (str): The name of the service
            statuses (list): List of valid statuses
        Reurn:
            bool, True if service status matches any of the given statuses
        """
        stdout, _, _ = self.get_service_status(self.ms1,
                                               service,
                                               assert_running=False)
        for status in statuses:
            if self.is_text_in_list(status, stdout):
                return True
        return False

    def _service_running(self, service, statuses):
        """ Closure function generator for service_running() """
        def service_running():
            """ Proxy for _check_service_status() function """
            return self._check_service_status(service, statuses)
        return service_running

    def _service_dead(self, service, statuses):
        """ Closure function generator for service_dead() """
        def service_dead():
            """ Proxy for _check_service_status() function """
            return self._check_service_status(service, statuses)
        return service_dead

    def _assert_model_is_in_correct_state(self):
        """
            Check that all items processed by this test are in correct state.
            If the test created new items all of them are expected to be
            in "Applied" state.
            If the test removed existing items all of them should no longer
            be found in the model.
        """
        if self.plan_mode == 'create':
            for item in self.test_items:
                self.assertEqual('Applied',
                                 self.get_item_state(self.ms1, item['url']))
        else:
            for item in self.test_items:
                self.assertEqual([],
                                 self.find(self.ms1,
                                           item['url'],
                                           item['type'],
                                           assert_not_empty=False))

    @attr('manual-test', 'non-revert', 'story124437',
          'story124437KillServices', 'story124437KillServices_tc01',
          'expansion')
    def test_01_celeryd_restarted_automatically(self):
        """
        @tms_id: torf_124437_kill_services_tc_01
        @tms_requirements_id: TORF-124437
        @tms_title:
            Verify that all celery processes are restarted automatically
            if stopped
        @tms_description:
            Verify that all celery processes are restarted automatically
            if stopped
        @tms_test_steps:
        @step: Check "celeryd" status
        @result: "celeryd" is running
        @step: Stop "celeryd" by issuing "service celeryd stop" command
        @result: "celeryd" is stopped
        @step: Wait for "celeryd" to get restarted
        @result: "celeryd" is up and running

        @tms_test_precondition: An MS system with "celeryd" running
        @tms_execution_type: Automated
        """

        #This test is not run in the KGB as it leaves the system in a state
        #that is different to what was found in ('non-revert')

        self.log('info',
        '1. Assert celeryd is running')
        self.get_service_status(self.ms1, 'celeryd', assert_running=True)

        self.log('info',
        '2. Stop celeryd')
        self.stop_service(self.ms1, 'celeryd', assert_success=True)

        self.log('info',
        '3. Assert that celery worker processes are restarted automatically')
        puppet_interval = self.get_puppet_interval(self.ms1)
        self.start_new_puppet_run(self.ms1)
        self.assertTrue(self._wait_for_conditions(
                                            self._celery_service_running,
                                            timeout=puppet_interval,
                                            poll_interval=3),
            'Celery failed to restart within a puppet run cycle of {0}s'
            .format(puppet_interval))

    @attr('manual-test', 'non-revert', 'expansion', 'story124437',
          'story124437KillServices', 'story124437KillServices_tc02')
    def test_02_p_stop_plan_with_stop_litpd_service(self):
        """
        @tms_id: torf_124437_kill_services_tc_02
        @tms_requirements_id: TORF-124437
        @tms_title:
            Stopping "litpd" while multiple phases are running
        @tms_description:
            Verify that while a multi cluster parallel plan is running
            if I issue the "service litpd stop" command the plan is stopped
        @tms_test_steps:
        @step: Create new LITP items on model
        @result: Items created successfully
        @step: Create a plan
        @result: Plan created successfully
        @step: Wait for multiple phases running in parallel
        @result: Parallel phase execution reached
        @step: Issue the "service litpd stop" command
        @result: "litpd" service stopped successfully
        @step: Start "litpd"
        @result: "litpd" started successfully
        @step: Check the plan status
        @result: The plan stopped
        @result: All tasks that were running when "litpd" was stopped
                 completed successfully
        @step: Re-create and run the plan
        @result: The plan completed successfully
        @result: All new items are in "Applied" state
        @tms_test_precondition: LITP deployment with at least 3 clusters
        @tms_execution_type: Automated
        """

        #This test is not run in the KGB as it leaves the system in a state
        #that is different to what was found in ('non-revert')

        self.skip_cleanup = True
        self.clusters_to_expand = [self.cluster2, self.cluster3, self.cluster4]

        self.log('info',
        '1. Create multi cluster environment if required')
        self._ensure_correct_multi_cluster_env_is_available()

        self.log('info',
        '2. Make changes to the model which should result in a parallel phase '
           'execution')
        self._create_parallel_capable_plan()
        self.execute_cli_runplan_cmd(self.ms1)

        self.log('info',
        '3. wait for parallelism in plan')
        plan_parallel = self._wait_for_conditions(
                                        self._multiple_phases_running,
                                        timeout=180,
                                        poll_interval=1)

        running_phases_at_litpd_stop = self.get_tasks_by_state(
                                                self.ms1,
                                                'Running',
                                                plan_data=plan_parallel)

        self.log('info', 'Running phases at "litpd stop" time')
        self._log_plan_state_details(running_phases_at_litpd_stop)

        self.log('info',
        '4. Stop the litpd service')
        self.stop_service(self.ms1, 'litpd')

        # This is required in order to query the plan status
        self.start_service(self.ms1, 'litpd')
        self.turn_on_litp_debug(self.ms1)

        self.log('info',
        '5. Check that plan state transitioned to "stopped"')
        stopped_plan = self.get_plan_data(self.ms1)
        self.log('info', 'Phases state at "stopped plan" time')
        self._log_plan_state_details(stopped_plan)
        self.assertEqual('stopped', stopped_plan.get('state'))

        # Celery is configured to work based on "phase boundaries".
        # It means that the smallest plan element that can be acted upon
        # while a plan is running is the "phase".
        # A "stop" plan request will actually take effect only when all
        # the tasks of each phase that had "running" tasks at the moment
        # the stop request was issued have either completed
        # successfully of failed
        self.log('info',
        '6. Check that phases running at "litpd stop" time completed '
           'successfully')
        for phase in running_phases_at_litpd_stop.keys():
            for tasks in stopped_plan['phases'][phase].values():
                for task in tasks:
                    self.assertEqual('Success', task.get('state'))

        self.log('info',
        '7. Re-create and run the plan')
        self.execute_cli_createplan_cmd(self.ms1)
        self.execute_cli_showplan_cmd(self.ms1)
        self.execute_cli_runplan_cmd(self.ms1)
        self.assertTrue(self.wait_for_plan_state(self.ms1,
                                                 const.PLAN_COMPLETE,
                                                 5))

        self.log('info',
        '8. Check that all test items are in the correct state')
        self._assert_model_is_in_correct_state()

    @attr('manual-test', 'non-revert', 'expansion', 'story124437',
          'story124437KillServices', 'story124437KillServices_tc03')
    def test_03_p_stop_plan_with_kill_litpd_service(self):
        """
        @tms_id: torf_124437_kill_services_tc_03
        @tms_requirements_id: TORF-124437
        @tms_title:
            Sending SIGTERM to "litpd" while multiple phases are running
        @tms_description:
            Verify that while a multi cluster parallel plan is running
            if I issue the SIGTERM to litpd PID the plan is stopped
        @tms_test_steps:
        @step: Create new LITP items on model
        @result: Items created successfully
        @step: Create a plan
        @result: Plan created successfully
        @step: Wait for multiple phases running in parallel
        @result: Parallel phase execution reached
        @step: Issue the "kill <litpd PID>" command
        @result: "litpd" service is stopped
        @step: Start "litpd" service
        @result: "litpd" started successfully
        @result: The plan stopped
        @result: All tasks that were running when "litpd" was terminated
                 completed successfully
        @step: Create and run the plan
        @result: The plan completed successfully
        @result: All the new items are no longer in the model

        @tms_test_precondition: LITP deployment with at least 3 clusters
        @tms_execution_type: Automated
        """

        #This test is not run in the KGB as it leaves the system in a state
        #that is different to what was found in ('non-revert')

        self.skip_cleanup = True
        self.clusters_to_expand = [self.cluster2, self.cluster3, self.cluster4]

        self.log('info',
        '1. Create multi cluster environment if required')
        self._ensure_correct_multi_cluster_env_is_available()

        self.log('info',
        '2. Make changes to the model which should result in a parallel phase '
           'execution')
        self._create_parallel_capable_plan()
        self.execute_cli_runplan_cmd(self.ms1)

        self.log('info',
        '3. wait for parallelism in plan')
        plan_parallel = self._wait_for_conditions(
                                        self._multiple_phases_running,
                                        timeout=180,
                                        poll_interval=1)

        running_phases_at_litpd_kill = self.get_tasks_by_state(
                                                self.ms1,
                                                'Running',
                                                plan_data=plan_parallel)

        self.log('info', 'Running phases at "litpd kill" time')
        self._log_plan_state_details(running_phases_at_litpd_kill)

        self.log('info',
        '4. Send SIGTERM to "litpd" to stop the plan')
        self.stop_service(self.ms1, 'litpd', kill_service=True)

        self.log('info',
        '5. Wait for "litpd" service to die')
        self._wait_for_conditions(
                            self._service_dead('litpd', ['dead', 'stopped']),
                            timeout=180,
                            poll_interval=3)

        self.log('info',
        '6. Start "litpd" service')
        # This is required in order to query the plan status
        self.start_service(self.ms1, 'litpd')
        self.turn_on_litp_debug(self.ms1)

        self.log('info',
        '7. Check that plan state transitioned to "stopped"')
        stopped_plan = self.get_plan_data(self.ms1)
        self.log('info', 'Phases state at "stopped plan" time')
        self._log_plan_state_details(stopped_plan)
        self.assertEqual('stopped', stopped_plan.get('state'))

        self.log('info',
        '8. Check that phases running at "litpd kill" time completed '
           'successfully')
        for phase in running_phases_at_litpd_kill.keys():
            for tasks in stopped_plan['phases'][phase].values():
                for task in tasks:
                    self.assertEqual('Success', task.get('state'))

        self.log('info',
        '9. Re-create and run the plan to completion')
        self.execute_cli_createplan_cmd(self.ms1)
        self.execute_cli_showplan_cmd(self.ms1)
        self.execute_cli_runplan_cmd(self.ms1)
        self.assertTrue(self.wait_for_plan_state(self.ms1,
                                                 const.PLAN_COMPLETE,
                                                 5))

        self.log('info',
        '10. Check that all test items are in the correct state')
        self._assert_model_is_in_correct_state()

    @attr('manual-test', 'non-revert', 'expansion', 'story124437',
          'story124437KillServices', 'story124437KillServices_tc05')
    def test_05_p_parallel_plan_restart_litpd_service(self):
        """
        @tms_id: torf_124437_kill_services_tc_05
        @tms_requirements_id: TORF-124437
        @tms_title:
            Restarting "litpd" while multiple phases are running
        @tms_description:
            Verify that while a multi cluster parallel plan is running
            if I issue the "service litpd restart" command the plan is stopped
        @tms_test_steps:
        @step: Create new LITP items on model
        @result: Items created successfully
        @step: Create a plan
        @result: Plan created successfully
        @step: Wait for multiple phases running in parallel
        @result: Parallel phase execution reached
        @step: Issue the "service litpd restart" command
        @result: "litpd" service restarted successfully
        @result: The plan stopped
        @result: All tasks that were running when "litpd" was stopped
                 completed successfully
        @step: Re-create and run the plan
        @result: The plan completed successfully
        @result: All new items are in "Applied" state
        @tms_test_precondition: LITP deployment with at least 3 clusters
        @tms_execution_type: Automated
        """

        #This test is not run in the KGB as it leaves the system in a state
        #that is different to what was found in ('non-revert')

        self.skip_cleanup = True
        self.clusters_to_expand = [self.cluster2, self.cluster3, self.cluster4]

        self.log('info',
        '1. Create multi cluster environment if required')
        self._ensure_correct_multi_cluster_env_is_available()

        self.log('info',
        '2. Make changes to the model which should result in a parallel phase '
           'execution')
        self._create_parallel_capable_plan()
        self.execute_cli_runplan_cmd(self.ms1)

        self.log('info',
        '3. wait for parallelism in plan')
        plan_parallel = self._wait_for_conditions(
                                        self._multiple_phases_running,
                                        timeout=180,
                                        poll_interval=1)

        running_phases_at_restart = self.get_tasks_by_state(
                                                self.ms1,
                                                'Running',
                                                plan_data=plan_parallel)

        self.log('info', 'Running phases at "litpd restart" time')
        self._log_plan_state_details(running_phases_at_restart)

        self.log('info',
        '4. Restart the "litpd" service')
        self.restart_litpd_service(self.ms1)

        self.log('info',
        '5. Check that plan state transitioned to "stopped"')
        stopped_plan = self.get_plan_data(self.ms1)
        self.log('info', 'Phases state at "stopped plan" time')
        self._log_plan_state_details(stopped_plan)
        self.assertEqual('stopped', stopped_plan.get('state'))

        self.log('info',
        '6. Check that phases running at "litpd stop" time completed '
           'successfully')
        for phase in running_phases_at_restart.keys():
            for tasks in stopped_plan['phases'][phase].values():
                for task in tasks:
                    self.assertEqual('Success', task.get('state'))

        self.log('info',
        '7. Re-create and run the plan')
        self.execute_cli_createplan_cmd(self.ms1)
        self.execute_cli_showplan_cmd(self.ms1)
        self.execute_cli_runplan_cmd(self.ms1)
        self.assertTrue(self.wait_for_plan_state(self.ms1,
                                                 const.PLAN_COMPLETE,
                                                 5))

        self.log('info',
        '8. Check that all test items are in the correct state')
        self._assert_model_is_in_correct_state()

    @attr('manual-test', 'non-revert', 'story124437',
          'story124437KillServices', 'story124437KillServices_tc10',
          'expansion')
    def test_10_p_fail_plan_with_stop_celery_service(self):
        """
        @tms_id: torf_124437_kill_services_tc_10
        @tms_requirements_id: TORF-124437
        @tms_title:
            Stopping "celeryd" service does not stop a running plan
        @tms_description:
            Verify that while a multi cluster parallel plan is running
            if I issue the "service celeryd stop" command
            the plan completes successfully
        @tms_test_steps:
        @step: Make changes to the model
        @result: Changes made successfully
        @step: Create and run the plan
        @result: Plan is running
        @step: Wait for parallelism
        @result: Multiple phases are running in parallel
        @step: Stop the "celeryd" service
        @result: "celeryd" service stopped successfully
        @step: Wait for puppet to restart "celeryd"
        @result: "celeryd" restarted successfully
        @step: Wait for plan to complete
        @result: Plan completed successfully
        @result: All items processed by the test are in the correct state

        @tms_test_precondition: Multi cluster environment deployed
        @tms_execution_type: Automated
        """

        #This test is not run in the KGB as it leaves the system in a state
        #that is different to what was found in ('non-revert')

        self.skip_cleanup = True
        self.clusters_to_expand = [self.cluster2, self.cluster3, self.cluster4]

        self.log('info',
        '1. Create multi cluster environment if required')
        self._ensure_correct_multi_cluster_env_is_available()

        self.log('info',
        '2. Make changes to the model which should result in a parallel phase '
           'execution')
        self._create_parallel_capable_plan()
        self.execute_cli_runplan_cmd(self.ms1)

        self.log('info',
        '3. Wait for parallelism in plan')
        plan_parallel = self._wait_for_conditions(
                                        self._multiple_phases_running,
                                        timeout=180,
                                        poll_interval=1)

        running_phases_at_celeryd_stop = self.get_tasks_by_state(
                                                    self.ms1,
                                                    'Running',
                                                    plan_data=plan_parallel)

        self.log('info', 'Running phases at "celeryd stop" time')
        self._log_plan_state_details(running_phases_at_celeryd_stop)

        self.log('info',
        '4. Stop the "celeryd" service')
        self.stop_service(self.ms1, 'celeryd', assert_success=False)
        self._wait_for_conditions(
                            self._service_dead('celeryd', ['down', 'stopped']),
                            timeout=180,
                            poll_interval=3)

        self.log('info',
        '5. Wait for "puppet" to restart "celeryd"')
        puppet_interval = self.get_puppet_interval(self.ms1)
        self._wait_for_conditions(self._celery_service_running,
                                  timeout=puppet_interval,
                                  poll_interval=3)

        self.log('info',
        '6. Wait for the plan to complete')
        self.assertTrue(self.wait_for_plan_state(self.ms1,
                                                 const.PLAN_COMPLETE,
                                                 5))

        self.log('info',
        '7. Check that all test items are in the correct state')
        self._assert_model_is_in_correct_state()

    @attr('manual-test', 'non-revert', 'story124437',
          'story124437KillServices', 'story124437KillServices_tc11',
          'expansion')
    def test_11_p_fail_plan_with_kill_celery_default_queue(self):
        """
        @tms_id: torf_124437_kill_services_tc_11
        @tms_requirements_id: TORF-124437
        @tms_title:
            Sending SIGTERM to "litpDefault" service does not stop a
            running plan
        @tms_description:
            Verify that while a multi cluster parallel plan is running
            if I issue the "pkill -f litpDefault" command
            the plan completes successfully
        @tms_test_steps:
        @step: Make changes to the model
        @result: Changes made successfully
        @step: Create and run the plan
        @result: Plan is running
        @step: Wait for parallelism
        @result: Multiple phases are running in parallel
        @step: Send SIGTERM to the "litpDefault" service
        @result: "litpDefault" service stopped successfully
        @step: Wait for puppet to restart "litpDefault"
        @result: "litpDefault" restarted successfully
        @step: Wait for plan to complete
        @result: Plan completed successfully
        @result: All items processed by the test are in the correct state

        @tms_test_precondition: Multi cluster environment deployed
        @tms_execution_type: Automated
        """

        #This test is not run in the KGB as it leaves the system in a state
        #that is different to what was found in ('non-revert')

        self.skip_cleanup = True
        self.clusters_to_expand = [self.cluster2, self.cluster3, self.cluster4]

        self.log('info',
        '1. Create multi cluster environment if required')
        self._ensure_correct_multi_cluster_env_is_available()

        self.log('info',
        '2. Make changes to the model which should result in a parallel phase '
           'execution')
        self._create_parallel_capable_plan()
        self.execute_cli_runplan_cmd(self.ms1)

        self.log('info',
        '3. wait for parallelism in plan')
        plan_parallel = self._wait_for_conditions(
                                        self._multiple_phases_running,
                                        timeout=180,
                                        poll_interval=1)

        running_phases_at_celeryd_stop = self.get_tasks_by_state(
                                                    self.ms1,
                                                    'Running',
                                                    plan_data=plan_parallel)

        self.log('info', 'Running phases at "celeryd stop" time')
        self._log_plan_state_details(running_phases_at_celeryd_stop)

        self.log('info',
        '4. Send SIGTERM the "litpDefault" service')
        self._kill_celery_queue(self.ms1, 'litpDefault', su_root=True)
        self._wait_for_conditions(
                            self._service_dead('celeryd', ['down', 'stopped']),
                            timeout=60,
                            poll_interval=3)

        self.log('info',
        '5. Wait for "puppet" to restart "celeryd"')
        puppet_interval = self.get_puppet_interval(self.ms1)
        self._wait_for_conditions(self._celery_service_running,
                                  timeout=puppet_interval,
                                  poll_interval=3)

        self.log('info',
        '6. Wait for the plan to complete')
        self.assertTrue(self.wait_for_plan_state(self.ms1,
                                                 const.PLAN_COMPLETE,
                                                 5))

        self.log('info',
        '7. Check that all test items are in the correct state')
        self._assert_model_is_in_correct_state()

    @attr('manual-test', 'non-revert', 'story124437',
          'story124437KillServices', 'story124437KillServices_tc13',
          'expansion')
    def test_13_p_fail_plan_with_kill_celery_plan_queue(self):
        """
        @tms_id: torf_124437_kill_services_tc_13
        @tms_requirements_id: TORF-124437
        @tms_title:
            Sending SIGTERM to "litpPlan" service will cause a running
            plan to fail
        @tms_description:
            Verify that while a multi cluster parallel plan is running
            if I issue the "pkill -f litpPlan" command
            the plan fails
        @tms_test_steps:
        @step: Make changes to the model
        @result: Changes made successfully
        @step: Create and run the plan
        @result: Plan is running
        @step: Wait for parallelism
        @result: Multiple phases are running in parallel
        @step: Stop the "litpPlan" service
        @result: "litpPlan" service stopped successfully
        @step: Wait for puppet to restart "litpPlan" service
        @result: "litpPlan" service restarted successfully
        @step: Wait for plan to fail
        @result: Plan failed
        @step: Create and run the plan and wait for it to complete successfully
        @result: Plan completed successfully
        @result: All items processed by the test are in the correct state

        @tms_test_precondition: Multi cluster environment deployed
        @tms_execution_type: Automated
        """

        #This test is not run in the KGB as it leaves the system in a state
        #that is different to what was found in ('non-revert')

        self.skip_cleanup = True
        self.clusters_to_expand = [self.cluster2, self.cluster3, self.cluster4]

        self.log('info',
        '1. Create multi cluster environment if required')
        self._ensure_correct_multi_cluster_env_is_available()

        self.log('info',
        '2. Make changes to the model which should result in a parallel phase '
           'execution')
        self._create_parallel_capable_plan()
        self.execute_cli_runplan_cmd(self.ms1)

        self.log('info',
        '3. wait for parallelism in plan')
        plan_parallel = self._wait_for_conditions(
                                        self._multiple_phases_running,
                                        timeout=180,
                                        poll_interval=1)

        running_phases_at_celeryd_stop = self.get_tasks_by_state(
                                                    self.ms1,
                                                    'Running',
                                                    plan_data=plan_parallel)

        self.log('info', 'Running phases at "celeryd stop" time')
        self._log_plan_state_details(running_phases_at_celeryd_stop)

        self.log('info',
        '4. Send SIGTERM the "litpPlan" service')
        self._kill_celery_queue(self.ms1,
                                'litpPlan',
                                su_root=True)
        self._wait_for_conditions(
                            self._service_dead('celeryd', ['down', 'stopped']),
                            timeout=60,
                            poll_interval=3)

        self.log('info',
        '5. Wait for "puppet" to restart "celeryd"')
        puppet_interval = self.get_puppet_interval(self.ms1)
        self._wait_for_conditions(self._celery_service_running,
                                  timeout=puppet_interval,
                                  poll_interval=3)

        self.log('info',
        '6. Wait for the plan to fail')
        self.assertTrue(self.wait_for_plan_state(self.ms1,
                                                 const.PLAN_FAILED,
                                                 5))

        self.log('info',
        '7. Re-create and run the plan')
        self.execute_cli_createplan_cmd(self.ms1)
        self.execute_cli_showplan_cmd(self.ms1)
        self.execute_cli_runplan_cmd(self.ms1)
        self.assertTrue(self.wait_for_plan_state(self.ms1,
                                                 const.PLAN_COMPLETE,
                                                 5))

        self.log('info',
        '8. Check that all test items are in the correct state')
        self._assert_model_is_in_correct_state()

    @attr('manual-test', 'non-revert', 'story124437',
          'story124437KillServices', 'story124437KillServices_tc15',
          'expansion')
    def test_15_p_fail_plan_with_kill_celery_task_queue(self):
        """
        @tms_id: torf_124437_kill_services_tc_15
        @tms_requirements_id: TORF-124437
        @tms_title:
            Sending SIGTERM to "litpTask" service will cause a running
            plan to fail
        @tms_description:
            Verify that while a multi cluster parallel plan is running
            if I issue the "pkill -f litpTask" command
            the plan fails
        @tms_test_steps:
        @step: Make changes to the model
        @result: Changes made successfully
        @step: Create and run the plan
        @result: Plan is running
        @step: Wait for parallelism
        @result: Multiple phases are running in parallel
        @step: Stop the "litpTask" service
        @result: "litpTask" service stopped successfully
        @step: Wait for puppet to restart "litpTask"
        @result: "litpTask" restarted successfully
        @step: Wait for plan to fail
        @result: Plan failed
        @step: Create and run the plan and wait for it to complete successfully
        @result: Plan completed successfully
        @result: All items processed by the test are in the correct state

        @tms_test_precondition: Multi cluster environment deployed
        @tms_execution_type: Automated
        """

        #This test is not run in the KGB as it leaves the system in a state
        #that is different to what was found in ('non-revert')

        self.skip_cleanup = False
        self.clusters_to_expand = [self.cluster2, self.cluster3, self.cluster4]

        self.log('info',
        '1. Create multi cluster environment if required')
        self._ensure_correct_multi_cluster_env_is_available()

        self.log('info',
        '2. Make changes to the model which should result in a parallel phase '
           'execution')
        self._create_parallel_capable_plan()
        self.execute_cli_runplan_cmd(self.ms1)

        self.log('info',
        '3. wait for parallelism in plan')
        plan_parallel = self._wait_for_conditions(
                                        self._multiple_phases_running,
                                        timeout=180,
                                        poll_interval=1)

        running_phases_at_celeryd_stop = self.get_tasks_by_state(
                                                    self.ms1,
                                                    'Running',
                                                    plan_data=plan_parallel)

        self.log('info', 'Running phases at "celeryd stop" time')
        self._log_plan_state_details(running_phases_at_celeryd_stop)

        self.log('info',
        '4. Send SIGTERM the "litpTask" service')
        self._kill_celery_queue(self.ms1,
                                'litpTask',
                                su_root=True)
        self._wait_for_conditions(
                            self._service_dead('celeryd', ['down', 'stopped']),
                            timeout=60,
                            poll_interval=3)

        self.log('info',
        '5. Wait for "puppet" to restart "celeryd"')
        puppet_interval = self.get_puppet_interval(self.ms1)
        self._wait_for_conditions(self._celery_service_running,
                                  timeout=puppet_interval,
                                  poll_interval=3)

        self.log('info',
        '6. Wait for the plan to fail')
        self.assertTrue(self.wait_for_plan_state(self.ms1,
                                                 const.PLAN_FAILED,
                                                 5))

        self.log('info',
        '7. Re-create and run the plan')
        self.execute_cli_createplan_cmd(self.ms1)
        self.execute_cli_showplan_cmd(self.ms1)
        self.execute_cli_runplan_cmd(self.ms1)
        self.assertTrue(self.wait_for_plan_state(self.ms1,
                                                 const.PLAN_COMPLETE,
                                                 5))

        self.log('info',
        '8. Check that all test items are in the correct state')
        self._assert_model_is_in_correct_state()
