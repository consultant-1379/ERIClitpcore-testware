"""
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     September 2016
@author:    Maurizio Senno, Laura Forbes
@summary:   TORF-124437
            As a LITP Architect I want LITP Core Execution Manger to execute
            Run Plan, Callbacks and Config phases as Celery Jobs in parallel
            based off phases from a phase order tree.
"""
from litp_generic_test import GenericTest, attr
import test_constants as const
import time


class Story124437Dependencies(GenericTest):
    """
        As a LITP Architect I want LITP Core Execution Manger to execute
        Run Plan, Callbacks and Config phases as Celery Jobs in parallel
        based off phases from a phase order tree.
    """

    def setUp(self):
        """ Runs before every single test """
        super(Story124437Dependencies, self).setUp()

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

        self.cluster_collect_url = self.find(
            self.ms1, '/deployments', 'cluster', False)[0]

        self.clusters_to_expand = [self.cluster2, self.cluster3, self.cluster4]
        self.nodes_to_expand = list()

    def tearDown(self):
        """ Runs after every single test """
        super(Story124437Dependencies, self).tearDown()

    def _expand_model(self):
        """
        Description:
            Expands the model with new clusters and nodes.
        """
        for cluster in self.clusters_to_expand:
            self.nodes_to_expand.append(cluster['node'])

            cluster['url'] = '{0}/{1}'.format(
                self.cluster_collect_url, cluster['id'])

            props = 'cluster_type=sfha low_prio_net=mgmt llt_nets=hb1,hb2 ' \
                    'cluster_id={0}'.format(cluster['cluster_id'])

            self.execute_cli_create_cmd(self.ms1, cluster['url'],
                                        'vcs-cluster', props=props)

            self.execute_expand_script(self.ms1, cluster['script'])

    def _check_deployment_type_and_create_snapshot(self):
        """
        Description:
            Asserts that the test environment has 1 cluster with 1 node.
            Creates a LITP snapshot.
        """
        clusters = self.find(self.ms1, '/deployments', 'vcs-cluster')
        nodes = self.find(self.ms1, '/deployments', 'node')
        self.assertTrue(len(clusters) == 1 and len(nodes) == 1,
                        'This test requires a LITP '
                        '1-cluster 1-node deployment.')

        self.execute_and_wait_createsnapshot(self.ms1, add_to_cleanup=False)

    def _is_plan_running(self):
        """
        Description:
            Checks if the LITP plan is in a "Running" state.
        Return:
            bool. True if plan is in "Running" state. False otherwise.
        """
        plan_state = self.get_current_plan_state(self.ms1)
        return plan_state == const.PLAN_IN_PROGRESS

    @staticmethod
    def _find_last_occurrence(list_to_search, find_string):
        """
        Description:
            Finds the position of the last occurrence of
            the passed string in the passed list.
            Returns -1 if the string has not been found.
        Args:
            list_to_search (list): List to search.
            find_string (str): String to find the
                last occurrence of in the passed list.
        Return:
            int. Position of last occurrence of the string in the list.
        """
        for count, elem in enumerate(reversed(list_to_search)):
            if elem == find_string:
                return len(list_to_search) - count - 1
        return -1

    def _all_nodes_sshable(self, nodes_to_check):
        """
        Description:
            Checks if all nodes in the passed list are be SSH-able.
        Args:
            nodes_to_check (list): List of nodes to check if
                they are all installed and accessible via SSH.
        Return:
            bool. True if all nodes are SSH-able. False otherwise.
        """
        # Assume all node are SSHable
        all_sshable = True

        for node in nodes_to_check:
            node = node['node']
            stdout, stderr, rc = self.run_command(
                self.ms1, "ssh -T litp-admin@{0}".format(node))

            self.assertEqual([], stdout)
            self.assertNotEqual([], stderr)
            self.assertEqual(255, rc)
            # Expected errors while node is offline/starting up:
            accepted_errors = ["Temporary failure in name resolution",
                               "No route to host", "Connection refused",
                               "Connection timed out"]

            # If node is up, the following string is expected to
            # be returned as an error when SSHed via Python
            if not any("Host key verification failed" in s for s in stderr):
                # Expected error not found - node is not SSHable
                all_sshable = False
                # Ensure only expected errors are returned
                accepted_error_returned = False
                if any(substring in stderr[0] for
                           substring in accepted_errors):
                    accepted_error_returned = True

                self.assertTrue(accepted_error_returned,
                                "Unexpected error returned while attempting"
                                " to SSH {0}: {1}".format(node, stderr))

        return all_sshable

    def _wait_for_nodes_installed(self, node_list, max_tries=80):
        """
        Description:
            Waits for all nodes in the passed list to be installed.
            Raises an Exception if nodes are not up after specified
            number of tries or if plan is not in "Running" state.
        Args:
            node_list (list): List of nodes to wait for to be installed.
            max_tries (int): Number of times to check if node is up with
                30 seconds in between each try. Default is 80 times (40 mins).
        """
        all_nodes_installed = False
        while not all_nodes_installed:
            self.assertTrue(self._is_plan_running(),
                            "Plan not in expected Running state.")

            all_nodes_installed = self._all_nodes_sshable(node_list)

            max_tries -= 1
            self.assertTrue(max_tries >= 0,
                            "Node(s) not up within the expected time.")
            time.sleep(30)

        # Ensure no task with description 'Wait for node "X" to install and
        # deregister node "X" from Cobbler' is still in 'Running' state
        deregister_running = True
        max_tries = 30
        while deregister_running:
            running = self.get_tasks_by_state(self.ms1)
            for value in running.values():
                for url_desc in value.values():
                    for task_desc in url_desc:
                        if not any("install and deregister node"
                                   in s for s in task_desc.values()):
                            deregister_running = False

            time.sleep(10)
            max_tries -= 1
            self.assertTrue(max_tries >= 0, "All nodes up but plan still "
                                            "running 'install node' task(s).")

    def _multiple_clusters_running(self, dependee_running, depender_running):
        """
        Description:
            Checks if a task from a dependee cluster and a
            depender cluster are running at the same time.
        Args:
            dependee_running (bool): True if a task from
                the dependee cluster is running. False otherwise.
            depender_running (bool): True if a task from
                the depender cluster is running. False otherwise.
        """
        both_running_msg = "DEPENDEE CLUSTER RUNNING WHILE " \
                           "DEPENDER CLUSTER IS RUNNING."
        self.assertFalse(dependee_running and depender_running,
                         both_running_msg)

    def _dummy_firewall_rules(self, rules):
        """
        Description:
            Create dummy firewall rules on each peer node with the given rules.
        Args:
            rules (dict): Dictionary of dummy rule urls and rule names.
        """
        node_urls = self.find(self.ms1, '/deployments', 'node')

        for url in node_urls:
            n_fw_coll_url = self.find(
                self.ms1, url,
                'collection-of-firewall-rule')[0]

            for rule_url, rule_name in rules.iteritems():
                node_fw_rule = '{0}/{1}'.format(n_fw_coll_url, rule_url)

                self.execute_cli_create_cmd(
                    self.ms1, node_fw_rule, 'firewall-rule',
                    'name={0}'.format(rule_name))

    def _revert_expansion(self):
        """
        Description:
            Reverts an expansion by restoring snapshots.
        """
        self.log('info', 'Reverting expansion.')
        self.execute_and_wait_restore_snapshot(
            self.ms1, poweroff_nodes=self.nodes_to_expand)

    @attr('manual-test', 'revert', 'story124437dependencies',
          'story124437dependencies_tc01', 'expansion')
    def test_01_p_verify_sequential_dependencies(self):
        """
        @tms_id: torf_124437_dependencies_tc01
        @tms_requirements_id: TORF-124437
        @tms_title:
            Verify sequential dependencies in deploying clusters.
        @tms_description:
            Verify that given a LITP model with clusters C2, C3, C4 in
            "Initial" state and C4 depends on C3 and C3 depends on
            C2, when I run the plan, then clusters are deployed
            following the sequence C2, C3, C4.
        @tms_test_steps:
            @step: Assert that the test environment has 1 cluster with 1 node.
            @result: Environment is verified to be correct.
            @step: Create a LITP snapshot.
            @result: LITP snapshot created successfully.
            @step: Create 3 additional clusters with 1 node each.
            @result: 3 new clusters with 1 node each added.
            @step: Make Cluster 3 depend on Cluster 2.
            @result: Cluster 3 depends on Cluster 2.
            @step: Make Cluster 4 depend on Cluster 3.
            @result: Cluster 4 depends on Cluster 3.
            @step: Kick off an expansion plan and
                ensure it is in a running state.
            @result: Expansion plan is running.
            @step: Wait for all nodes to be installed.
            @result: All nodes are installed.
            @step: Assert that a task from a dependee cluster and a task from
                a depender cluster are not running at the same time.
            @result: Tasks from dependee and depender
                clusters run asynchronously.
            @step: Ensure that no dependee cluster tasks ran after
                intermediate cluster tasks began.
            @result: All dependee cluster tasks finished before any
                intermediate cluster tasks started.
            @step: Ensure that no intermediate cluster tasks ran before
                dependee cluster tasks finished or after depender tasks began.
            @result: Intermediate cluster tasks ran after dependee tasks
                completed and finished before depender cluster tasks began.
            @step: Ensure that no depender cluster tasks began before
                any intermediate cluster tasks finished.
            @result: Depender cluster tasks started running after the
                completion of all intermediate cluster tasks.
            @step: Revert expansion.
            @result: Deployment successfully reverted to 1 cluster with 1 node.
        @tms_test_precondition: Test environment has 1 cluster with 1 node.
        @tms_execution_type: Automated
        """
        # This test is not run as part of the KGB due to the execution time
        # taking too long

        self.log('info', '1. Check that test environment is correct. '
                         'Create a LITP snapshot.')
        self._check_deployment_type_and_create_snapshot()

        self.log('info', '2. Create three new clusters with one node each.')
        # Expand the LITP model with the new clusters and nodes
        self._expand_model()

        self.log('info', '2.1. Cluster 3 will have a dependency on Cluster 2.')
        props = 'dependency_list="c2"'
        self.execute_cli_update_cmd(self.ms1, self.cluster3['url'], props)

        self.log('info', '2.2. Cluster 4 will have a dependency on Cluster 3.')
        props = 'dependency_list="c3"'
        self.execute_cli_update_cmd(self.ms1, self.cluster4['url'], props)

        try:
            self.log('info', '3. Run an expansion plan.')
            self.run_and_check_plan(self.ms1, const.PLAN_IN_PROGRESS,
                                    plan_timeout_mins=5,
                                    add_to_cleanup=False)
            # Ensure plan is running
            self.assertTrue(self._is_plan_running(),
                            "Plan not in expected Running state.")

            self.log('info', '4. Wait for all nodes to be up.')
            # Wait for 40 minutes for all added nodes to be installed
            self._wait_for_nodes_installed(self.clusters_to_expand)
            self.log('info', '4.1. All nodes are up and SSHable.')

            # Other cluster(s) depend on the below cluster
            dependee_cluster = ['c2']
            # The below cluster is dependent on another
            # cluster and also has a cluster dependent on it
            intermediate_cluster = ['c3']
            # The below cluster depends on another cluster
            depender_cluster = ['c4']

            cluster_sequence = []  # Store the order of cluster tasks executed

            while self._is_plan_running():
                # Get list of phases with running tasks
                running = self.get_tasks_by_state(self.ms1)

                # To check what clusters are running tasks at a given time
                dependee_running = False
                intermediate_running = False
                depender_running = False

                # Iterate through the running tasks extracting
                # the cluster and task description
                for value in running.values():
                    for cluster, url_desc in value.iteritems():
                        # Ignore any tasks that update host files
                        if "host file" in url_desc[0]['desc']:
                            continue

                        # Get order that tasks are run in
                        cluster_sequence.append(cluster)

                        # Check what cluster(s) has running tasks
                        dependee_running = ((dependee_running == True) or
                                            (cluster in dependee_cluster))
                        intermediate_running = ((intermediate_running == True)
                                        or (cluster in intermediate_cluster))
                        depender_running = ((depender_running == True) or
                                            (cluster in depender_cluster))

                        # Ensure that a task from both a dependee and
                        # depender cluster are not running simultaneously
                        self._multiple_clusters_running(
                            dependee_running, intermediate_running)
                        self._multiple_clusters_running(
                            intermediate_running, depender_running)
                        self._multiple_clusters_running(
                            dependee_running, depender_running)

            # Ensure that the plan has completed successfully
            self.assertEqual(self.get_current_plan_state(self.ms1),
                             const.PLAN_COMPLETE,
                             "Plan not in expected Running/Complete state.")
            self.log("info", "5. Plan completed successfully.")

            self.log("info", "6. Ensuring Phases ran in correct order.")
            # Get last occurrence of dependee cluster running in plan execution
            last_dependee = self._find_last_occurrence(
                cluster_sequence, dependee_cluster[0])
            # Get last occurrence of intermediate cluster in plan execution
            last_intermediate = self._find_last_occurrence(
                cluster_sequence, intermediate_cluster[0])

            # Ensure that no dependee cluster tasks
            # ran after intermediate cluster tasks began
            self.assertFalse(
                dependee_cluster[0] in cluster_sequence[last_dependee + 1:],
                "Dependee task(s) ran after intermediate tasks "
                "began:\n{0}".format(cluster_sequence))

            # Ensure that no intermediate cluster tasks ran before dependee
            # cluster tasks finished or after depender cluster tasks began
            self.assertFalse(
                intermediate_cluster[0] in
                cluster_sequence[:last_dependee + 1],
                "Intermediate task(s) ran before dependee tasks "
                "finished:\n{0}".format(cluster_sequence))
            self.assertFalse(
                intermediate_cluster[0] in
                cluster_sequence[last_intermediate + 1:],
                "Intermediate task(s) ran after depender "
                "tasks began:\n{0}".format(cluster_sequence))

            # Ensure that no depender cluster tasks began
            # before intermediate cluster tasks finished
            self.assertFalse(depender_cluster[0] in
                             cluster_sequence[:last_intermediate + 1],
                             "Depender task(s) ran before "
                             "intermediate tasks finished:\n{0}".format(
                                 cluster_sequence))

        finally:
            self._revert_expansion()

    @attr('manual-test', 'revert', 'story124437dependencies',
          'story124437dependencies_tc02', 'expansion')
    def test_02_p_verify_sequential_dependencies_upgrade(self):
        """
        @tms_id: torf_124437_dependencies_tc02
        @tms_requirements_id: TORF-124437
        @tms_title:
            Verify sequential dependencies in upgrading clusters.
        @tms_description:
            1) Verify that given a LITP model with clusters C2, C3, C4 in
            "Initial" state and C3 depends on C2 and C4 has no dependency,
            when I run the plan, then cluster specific phases for C2 and C4
            are deployed first in parallel and C3 will come after C2.
            2) Verify that given a LITP model with clusters C2, C3, C4 in
            "Applied" state and C3 depends on C2 and C4 has no dependency, when
            I run a plan to upgrade clusters, then cluster specific phases for
            C2 and C4 are deployed first in parallel and C3 will come after C2.
        @tms_test_steps:
            @step: Begin test for sequential deployment.
            Assert that the test environment has 1 cluster with 1 node.
            @result: Environment is verified to be correct.
            @step: Create a LITP snapshot.
            @result: LITP snapshot created successfully.
            @step: Create 3 additional clusters with 1 node each.
            @result: 3 new clusters with 1 node each added.
            @step: Make Cluster 3 depend on Cluster 2.
            @result: Cluster 3 depends on Cluster 2.
            @step: Kick off an expansion plan and
                ensure it is in a running state.
            @result: Expansion plan is running.
            @step: Wait for all nodes to be installed.
            @result: All nodes are installed.
            @step: Assert that a task from a dependee cluster and a task from
                a depender cluster are not running at the same time.
            @result: Tasks from dependee and depender
                clusters run asynchronously.
            @step: Assert that at some stage, two
                phases were running in parallel.
            @result: Two phases were detected to run in parallel at some point.
            @step: Ensure that no dependee cluster tasks
                ran after depender cluster tasks began.
            @result: Depender cluster tasks ran after dependee tasks completed.
            @step: Assert that no depender cluster tasks began
                before dependee cluster tasks finished.
            @result: Dependee cluster tasks completed
                before depender cluster tasks began.
            @step: End test for sequential deployment.
                Begin test for sequential upgrade.
            Create dummy firewall rules on each node.
            @result: Dummy firewall rules created on each node.
            @step: Create and run upgrade plan.
            @result: Plan is created and in a "Running" state.
            @step: Assert that a task from a dependee cluster and a task from
                a depender cluster are not running at the same time.
            @result: Tasks from dependee and depender
                clusters run asynchronously.
            @step: Assert that at some stage, two
                phases were running in parallel.
            @result: Two phases were detected to run in parallel at some point.
            @step: Ensure that no dependee cluster tasks
                ran after depender cluster tasks began.
            @result: Depender cluster tasks ran after dependee tasks completed.
            @step: Assert that no depender cluster tasks began
                before dependee cluster tasks finished.
            @result: Dependee cluster tasks completed
                before depender cluster tasks began.
            @step: Revert expansion.
            @result: Deployment successfully reverted to 1 cluster with 1 node.
        @tms_test_precondition: Test environment has 1 cluster with 1 node.
        @tms_execution_type: Automated
        """

        # This test is not run as part of the KGB due to the execution time
        # taking too long

        self.log('info', '1. Check that test environment is correct. '
                         'Create a LITP snapshot.')
        self._check_deployment_type_and_create_snapshot()

        self.log('info', '2. Create three new clusters with one node each.')
        # Expand the LITP model with the new clusters and nodes
        self._expand_model()

        self.log('info', '2.1. Cluster 3 will have a dependency on Cluster 2.')
        props = 'dependency_list="c2"'
        self.execute_cli_update_cmd(self.ms1, self.cluster3['url'], props)

        try:
            self.log('info', '3. Run an expansion plan.')
            self.run_and_check_plan(self.ms1, const.PLAN_IN_PROGRESS,
                                    plan_timeout_mins=5,
                                    add_to_cleanup=False)
            # Ensure plan is running
            self.assertTrue(self._is_plan_running(),
                            "Plan not in expected Running state.")

            self.log('info', '4. Wait for all nodes to be up.')
            # Wait for 40 minutes for all added nodes to be installed
            self._wait_for_nodes_installed(self.clusters_to_expand)
            self.log('info', '4.1. All nodes are up and SSHable.')

            # Other cluster(s) depend on the below cluster
            dependee_cluster = ['c2']
            # The below cluster depends on another cluster(s)
            depender_cluster = ['c3']

            parallel_running = False  # To check if parallelism is detected
            cluster_sequence = []  # Store the order of cluster tasks executed

            while self._is_plan_running():
                # Get list of phases with running tasks
                running = self.get_tasks_by_state(self.ms1)

                # Check if more than one phase is running
                if len(running) > 1:
                    parallel_running = True

                # To check what clusters are running tasks at a given time
                dependee_running = False
                depender_running = False

                # Iterate through the running tasks extracting
                # the cluster and task description
                for value in running.values():
                    for cluster, url_desc in value.iteritems():
                        # Ignore any tasks that update host files
                        if "host file" in url_desc[0]['desc']:
                            continue

                        # Get order that tasks are run in
                        cluster_sequence.append(cluster)

                        # Check what cluster(s) has running tasks
                        dependee_running = ((dependee_running == True) or
                                            (cluster in dependee_cluster))
                        depender_running = ((depender_running == True) or
                                            (cluster in depender_cluster))

                        # Ensure that a task from both the dependee and
                        # depender clusters are not running simultaneously
                        self._multiple_clusters_running(
                            dependee_running, depender_running)

            # Ensure that the plan has completed successfully
            self.assertEqual(self.get_current_plan_state(self.ms1),
                             const.PLAN_COMPLETE,
                             "Plan not in expected Running/Complete state.")
            self.log("info", "5. Plan completed successfully.")

            # Assert that at some stage, 2 phases were running in parallel
            self.assertTrue(parallel_running,
                            "No phases were detected to run in parallel.")

            self.log("info", "6. Ensuring Phases ran in correct order.")
            # Get last occurrence of dependee cluster running in plan execution
            last_dependee = self._find_last_occurrence(
                cluster_sequence, dependee_cluster[0])
            # Ensure that no dependee cluster tasks
            # ran after depender cluster tasks began
            self.assertFalse(
                dependee_cluster[0] in cluster_sequence[last_dependee + 1:],
                "Dependee task(s) ran after depender tasks "
                "began:\n{0}".format(cluster_sequence))
            # Ensure that no depender cluster tasks began
            # before dependee cluster tasks finished
            self.assertFalse(
                depender_cluster[0] in cluster_sequence[:last_dependee],
                "Depender task(s) ran before dependee tasks "
                "finished:\n{0}".format(cluster_sequence))

            self.log("info", "BEGINNING TEST FOR SEQUENTIAL UPGRADE.")

            self.log(
                'info', '7. Create dummy firewall rules on each node.')
            firewall_rules = {'fw_story_124437': '"550 story124437"',
                              'fw_story124437': '"105 story124437second"'}
            self._dummy_firewall_rules(firewall_rules)

            self.log("info", "8. Create and run upgrade plan.")
            self.execute_cli_createplan_cmd(self.ms1)
            self.execute_cli_runplan_cmd(self.ms1)
            self.assertTrue(self.wait_for_plan_state(
                self.ms1, const.PLAN_IN_PROGRESS))

            parallel_running = False  # To check if parallelism is detected
            cluster_sequence = []  # Store order of cluster tasks executed

            while self._is_plan_running():
                # Get list of phases with running tasks
                running = self.get_tasks_by_state(self.ms1)

                # Check if more than one phase is running
                if len(running) > 1:
                    parallel_running = True

                # To check what clusters are running tasks at a given time
                dependee_running = False
                depender_running = False

                # Iterate through the running tasks extracting
                # the cluster and task description
                for value in running.values():
                    for cluster, url_desc in value.iteritems():
                        # Ignore any tasks that update host files
                        if "host file" in url_desc[0]['desc']:
                            continue

                        # Get order that tasks are run in
                        cluster_sequence.append(cluster)

                        # Check what cluster(s) has running tasks
                        dependee_running = ((dependee_running == True) or
                                            (cluster in dependee_cluster))
                        depender_running = ((depender_running == True) or
                                            (cluster in depender_cluster))

                        # Ensure that a task from both the dependee and
                        # depender clusters are not running simultaneously
                        self._multiple_clusters_running(
                            dependee_running, depender_running)

            # Ensure that the plan has completed successfully
            self.assertEqual(self.get_current_plan_state(self.ms1),
                             const.PLAN_COMPLETE,
                             "Plan not in expected Running/Complete state.")
            self.log("info", "8.1 Plan completed successfully.")

            # Assert that at some stage, 2 phases were running in parallel
            self.assertTrue(parallel_running,
                            "No phases were detected to run in parallel.")

            self.log("info", "9. Ensuring Phases ran in correct order.")
            # Get last occurrence of dependee cluster running in plan execution
            last_dependee = self._find_last_occurrence(
                            cluster_sequence, dependee_cluster[0])
            # Ensure that no dependee cluster tasks
            # ran after depender cluster tasks began
            self.assertFalse(
                dependee_cluster[0] in cluster_sequence[last_dependee + 1:],
                "Dependee task(s) ran after depender tasks began:"
                "\n{0}".format(cluster_sequence))
            # Ensure that no depender tasks began before dependee tasks finish
            self.assertFalse(
                depender_cluster[0] in cluster_sequence[:last_dependee],
                "Depender task(s) ran before dependee tasks "
                "finished:\n{0}".format(cluster_sequence))

        finally:
            self._revert_expansion()

    @attr('manual-test', 'revert', 'story124437dependencies',
          'story124437dependencies_tc03', 'expansion')
    def test_03_p_verify_multiple_and_no_dependencies(self):
        """
        @tms_id: torf_124437_dependencies_tc03
        @tms_requirements_id: TORF-124437
        @tms_title:
            Verify multiple dependencies in deploying and upgrading clusters.
        @tms_description:
            1) Verify that given a LITP model with clusters in "Initial" state
            with no dependencies, when I run the plan, then cluster specific
            phases are executed in parallel.
            2) Verify that given a LITP model with clusters C2, C3, C4 in
            "Applied" state and C3 depends on C2 and C4, when I run a plan to
            upgrade clusters, then cluster specific phases for C2 and C4 are
            deployed first in parallel and C3 will come after C2 and C4.
        @tms_test_steps:
            @step: Begin test for no dependency multiple deployment.
            Assert that the test environment has 1 cluster with 1 node.
            @result: Environment is verified to be correct.
            @step: Create a LITP snapshot.
            @result: LITP snapshot created successfully.
            @step: Create 3 additional clusters with
                1 node each, no dependencies.
            @result: 3 new clusters containing 1 node
                each added with no dependencies.
            @step: Kick off an expansion plan and
                ensure it is in a running state.
            @result: Expansion plan is running.
            @step: Wait for all nodes to be installed.
            @result: All nodes are installed.
            @step: Assert that at some stage, three
                phases were running in parallel.
            @result: Three phases were detected to run in parallel.
            @step: End test for no dependency multiple deployment.
                Begin test for multiple dependency upgrade.
            Make Cluster 3 depend on Cluster 2 and Cluster 4.
            @result: Cluster 3 depends on Clusters 2 and 4.
            @step: Create dummy firewall rules on each node.
            @result: Dummy firewall rules created on each node.
            @step: Create and run upgrade plan.
            @result: Plan is created and in a "Running" state.
            @step: Assert that a task from a dependee cluster and a task from
                a depender cluster are not running at the same time.
            @result: Tasks from dependee and depender
                clusters run asynchronously.
            @step: Assert that at some stage, two
                phases were running in parallel.
            @result: Two phases were detected to run in parallel at some point.
            @step: Ensure that no dependee cluster tasks
                ran after depender cluster tasks began.
            @result: Depender cluster tasks ran after dependee tasks completed.
            @step: Assert that no depender cluster tasks began
                before dependee cluster tasks finished.
            @result: Dependee cluster tasks completed
                before depender cluster tasks began.
            @step: Revert expansion.
            @result: Deployment successfully reverted to 1 cluster with 1 node.
        @tms_test_precondition: Test environment has 1 cluster with 1 node.
        @tms_execution_type: Automated
        """

        # This test is not run as part of the KGB due to the execution time
        # taking too long

        self.log('info', '1. Check that test environment is correct. '
                         'Create a LITP snapshot.')
        self._check_deployment_type_and_create_snapshot()

        self.log('info', '2. Create three new clusters with '
                         'one node each. No dependencies.')

        # Expand the LITP model with the new clusters and nodes
        self._expand_model()

        try:
            self.log('info', '3. Run an expansion plan.')
            self.run_and_check_plan(self.ms1, const.PLAN_IN_PROGRESS,
                                    plan_timeout_mins=5,
                                    add_to_cleanup=False)

            # Ensure plan is running
            self.assertTrue(self._is_plan_running(),
                            "Plan not in expected Running state.")

            self.log('info', '4. Wait for all nodes to be up.')
            # Wait for 40 minutes for all added nodes to be installed
            self._wait_for_nodes_installed(self.clusters_to_expand)
            self.log('info', '4.1. All nodes are up and SSHable.')

            parallel_running = False  # To check if parallelism is detected

            while self._is_plan_running():
                # Get list of phases with running tasks
                running = self.get_tasks_by_state(self.ms1)

                # Check if more than two phases are running
                if len(running) > 2:
                    parallel_running = True

            # Ensure that the plan has completed successfully
            self.assertEqual(self.get_current_plan_state(self.ms1),
                             const.PLAN_COMPLETE,
                             "Plan not in expected Running/Complete state.")
            self.log("info", "5. Plan completed successfully.")

            # Assert that at some stage at least
            # 3 phases were running in parallel
            self.assertTrue(parallel_running,
                            "3 phases were not detected to run in parallel.")

            self.log("info", "BEGINNING TEST FOR MULTIPLE DEPENDENCY UPGRADE.")

            self.log('info', '6. Cluster 3 will have a '
                             'dependency on Clusters 2 and 4.')
            props = 'dependency_list="c2,c4"'
            self.execute_cli_update_cmd(self.ms1, self.cluster3['url'], props)

            self.log('info', '7. Create dummy firewall rule on each node.')
            firewall_rules = {'fw_story_124437': '"550 story124437"'}
            self._dummy_firewall_rules(firewall_rules)

            self.log("info", "8. Create and run upgrade plan.")
            self.execute_cli_createplan_cmd(self.ms1)
            self.execute_cli_runplan_cmd(self.ms1)
            self.assertTrue(self.wait_for_plan_state(
                self.ms1, const.PLAN_IN_PROGRESS))

            parallel_running = False  # To check if parallelism is detected
            cluster_sequence = []  # Store order of cluster tasks executed

            # Other cluster(s) depend on the below cluster(s)
            dependee_cluster = ['c2', 'c4']
            # The below cluster(s) depends on another cluster(s)
            depender_cluster = ['c3']

            while self._is_plan_running():
                # Get list of phases with running tasks
                running = self.get_tasks_by_state(self.ms1)

                # Check if more than one phase is running
                if len(running) > 1:
                    parallel_running = True

                # To check what clusters are running tasks at a given time
                dependee_running = False
                depender_running = False

                # Iterate through the running tasks extracting
                # the cluster and task description
                for value in running.values():
                    for cluster in value.values():
                        # Get order that tasks are run in
                        cluster_sequence.append(cluster)

                        # Check what cluster(s) has running tasks
                        dependee_running = ((dependee_running == True) or
                                            (cluster in dependee_cluster))
                        depender_running = ((depender_running == True) or
                                            (cluster in depender_cluster))

                        # Ensure that a task from both a dependee and
                        # depender cluster are not running simultaneously
                        self._multiple_clusters_running(
                            dependee_running, depender_running)

            # Ensure that the plan has completed successfully
            self.assertEqual(self.get_current_plan_state(self.ms1),
                             const.PLAN_COMPLETE,
                             "Plan not in expected Running/Complete state.")
            self.log("info", "8.1. Plan completed successfully.")

            # Assert that at some stage, 2 phases were running in parallel
            self.assertTrue(parallel_running,
                            "No phases were detected to run in parallel.")

            self.log("info", "9. Ensuring Phases ran in correct order.")
            # Get last occurrences of dependee
            # clusters running in plan execution sequence
            last_c2 = self._find_last_occurrence(
                            cluster_sequence, dependee_cluster[0])
            last_c4 = self._find_last_occurrence(
                            cluster_sequence, dependee_cluster[1])
            # Find the sequence position of the last run dependee cluster
            last_dependee = max([last_c2, last_c4])
            # Ensure that no dependee cluster tasks
            # ran after depender cluster tasks began
            for dependee in dependee_cluster:
                self.assertFalse(
                    dependee in cluster_sequence[last_dependee + 1:],
                    "Dependee task(s) ran after depender tasks began:"
                    "\n{0}".format(cluster_sequence))
            # Ensure that no depender cluster tasks began
            # before dependee cluster tasks finished
            self.assertFalse(
                depender_cluster[0] in cluster_sequence[:last_dependee],
                "Depender task(s) ran before dependee tasks "
                "finished:\n{0}".format(cluster_sequence))

        finally:
            self._revert_expansion()

    @attr('manual-test', 'revert', 'story124437dependencies',
          'story124437dependencies_tc04', 'expansion')
    def test_04_p_verify_dependency_cluster_already_deployed(self):
        """
        @tms_id: torf_124437_dependencies_tc04
        @tms_requirements_id: TORF-124437
        @tms_title:
            Verify dependency on already deployed cluster.
        @tms_description:
            Verify that given a LITP model with clusters C2, C3, C4 in
            "Initial" state and C1 in "Applied" state and C3 depends on C1,
            when I run the plan, then cluster specific phases for
            C2, C3, C4 are executed in parallel.
        @tms_test_steps:
            @step: Assert that the test environment has 1 cluster with 1 node.
            @result: Environment is verified to be correct.
            @step: Create a LITP snapshot.
            @result: LITP snapshot created successfully.
            @step: Create 3 additional clusters with 1 node each.
            @result: 3 new clusters with 1 node each added.
            @step: Make Cluster 3 depend on Cluster 1.
            @result: Cluster 3 depends on Cluster 1.
            @step: Kick off an expansion plan and
                ensure it is in a running state.
            @result: Expansion plan is running.
            @step: Wait for all nodes to be installed.
            @result: All nodes are installed.
            @step: Assert that a task from a dependee cluster and a task from
                a depender cluster are not running at the same time.
            @result: Tasks from dependee and depender
                clusters run asynchronously.
            @step: Assert that at some stage, three
                phases were running in parallel.
            @result: Three phases were detected to run in parallel.
            @step: Assert that no dependee cluster tasks
            ran after depender cluster tasks began.
            @result: All dependee cluster tasks finished
            before any depender cluster tasks started.
            @step: Ensure no depender cluster tasks began
            before dependee cluster tasks finished.
            @result: Depender cluster tasks started running after
            the completion of all dependee cluster tasks.
            @step: Revert expansion.
            @result: Deployment successfully reverted to 1 cluster with 1 node.
        @tms_test_precondition: Test environment has 1 cluster with 1 node.
        @tms_execution_type: Automated
        """

        # This test is not run as part of the KGB due to the execution time
        # taking too long

        self.log('info', '1. Check that test environment is correct. '
                         'Create a LITP snapshot.')
        self._check_deployment_type_and_create_snapshot()

        self.log('info', '2. Create three new clusters with one node each.')
        # Expand the LITP model with the new clusters and nodes
        self._expand_model()

        self.log('info', '2.1. Cluster 3 will have a dependency on Cluster 1.')
        props = 'dependency_list="c1"'
        self.execute_cli_update_cmd(self.ms1, self.cluster3['url'], props)

        try:
            self.log('info', '3. Run an expansion plan.')
            self.run_and_check_plan(self.ms1,
                                    const.PLAN_IN_PROGRESS,
                                    plan_timeout_mins=5,
                                    add_to_cleanup=False)
            # Ensure plan is running
            self.assertTrue(self._is_plan_running(),
                            "Plan not in expected Running state.")

            self.log('info', '4. Wait for all nodes to be up.')
            # Wait for 40 minutes for all added nodes to be installed
            self._wait_for_nodes_installed(self.clusters_to_expand)
            self.log('info', '4.1. All nodes are up and SSHable.')

            # Other cluster(s) depend on the below cluster
            dependee_cluster = ['c1']
            # The below clusters depend on another cluster(s)
            depender_cluster = ['c3']

            parallel_running = False  # To check if parallelism is detected
            cluster_sequence = []  # Store order of cluster tasks executed

            while self._is_plan_running():
                # Get list of phases with running tasks
                running = self.get_tasks_by_state(self.ms1)

                # Check if more than two phases are running
                if len(running) > 2:
                    parallel_running = True

                # To check what clusters are running tasks at a given time
                dependee_running = False
                depender_running = False

                # Iterate through the running tasks extracting
                # the cluster and task description
                for value in running.values():
                    for cluster, url_desc in value.iteritems():
                        # Ignore any tasks that update host files
                        if "host file" in url_desc[0]['desc']:
                            continue

                        # Get order that tasks are run in
                        cluster_sequence.append(cluster)

                        # Check what cluster(s) has running tasks
                        dependee_running = ((dependee_running == True) or
                                            (cluster in dependee_cluster))
                        depender_running = ((depender_running == True) or
                                            (cluster in depender_cluster))

                        # Ensure that a task from both the dependee and
                        # depender clusters are not running simultaneously
                        self._multiple_clusters_running(
                            dependee_running, depender_running)

            # Ensure that the plan has completed successfully
            self.assertEqual(self.get_current_plan_state(self.ms1),
                             const.PLAN_COMPLETE,
                             "Plan not in expected Running/Complete state.")
            self.log("info", "5. Plan completed successfully.")

            # Assert that at some stage, 3 phases were running in parallel
            self.assertTrue(parallel_running,
                            "No phases were detected to run in parallel.")

            # Assert that no dependee cluster tasks were
            # run after the depender cluster node was installed
            # Get last occurrence of dependee cluster running in plan execution
            if dependee_cluster[0] in cluster_sequence:
                last_dependee = self._find_last_occurrence(
                    cluster_sequence, dependee_cluster[0])
                self.log("info", "6. Ensuring Phases ran in correct order.")
                # Ensure that no dependee cluster tasks
                # ran after depender cluster tasks began
                self.assertFalse(dependee_cluster[0] in
                                 cluster_sequence[last_dependee + 1:],
                                 "Dependee task(s) ran after depender tasks "
                                 "began:\n{0}".format(cluster_sequence))
                # Ensure no depender tasks began before dependee tasks finished
                for depender in depender_cluster:
                    self.assertFalse(
                        depender in cluster_sequence[:last_dependee],
                        "Depender task(s) ran before dependee tasks "
                        "finished:\n{0}".format(cluster_sequence))

        finally:
            self._revert_expansion()

    @attr('manual-test', 'revert', 'story124437dependencies',
          'story124437dependencies_tc05', 'expansion')
    def test_05_p_verify_multiple_and_circular_dependencies(self):
        """
        @tms_id: torf_124437_dependencies_tc05
        @tms_requirements_id: TORF-124437
        @tms_title:
            Verify multiple dependencies on one
            cluster and circular dependencies.
        @tms_description:
            1) Verify that given a LITP model with clusters C2, C3, C4 in
            "Initial" state and both C3 and C4 depend on C2, when I run the
            plan, then C2 is deployed first and cluster specific phases for
            C3, C4 are executed in parallel.
            2) Verify that given a LITP model with clusters C2, C3, C4 in
            "Applied" state and C4 depends on C3 and C3 depends on
            C2 and C2 depends on C4 (circular dependency), when I run
            "litp create_plan" an error is thrown.
        @tms_test_steps:
            @step: Begin test for multiple dependency deployment.
            Assert that the test environment has 1 cluster with 1 node.
            @result: Environment is verified to be correct.
            @step: Create a LITP snapshot.
            @result: LITP snapshot created successfully.
            @step: Create 3 additional clusters with 1 node each.
            @result: 3 new clusters with one node each added.
            @step: Make Cluster 3 depend on Cluster 2.
            @result: Cluster 3 depends on Cluster 2.
            @step: Make Cluster 4 depend on Cluster 2.
            @result: Cluster 4 depends on Cluster 2.
            @step: Kick off an expansion plan and
                ensure it is in a running state.
            @result: Expansion plan is running.
            @step: Wait for all nodes to be installed.
            @result: All nodes are installed.
            @step: Assert that a task from a dependee cluster and a task from
                a depender cluster are not running at the same time.
            @result: Tasks from dependee and depender
                clusters run asynchronously.
             @step: Assert that at some stage, two
                phases were running in parallel.
            @result: Two phases were detected to run in parallel at some point.
            @step: Ensure that no dependee cluster
                tasks ran after depender cluster tasks began.
            @result: All dependee cluster tasks
                completed before depender cluster tasks began.
            @step: Ensure that no depender cluster tasks
                began before dependee cluster tasks finished.
            @result: Depender cluster tasks began
                after all dependee cluster tasks completed.
            @step: End test for multiple dependency deployment.
                Begin test for circular dependency.
            Make Cluster 4 depend on Cluster 3.
            @result: Cluster 4 depends on Cluster 3.
            @step: Make Cluster 3 depend on Cluster 2.
            @result: Cluster 3 depends on Cluster 2.
            @step: Make Cluster 2 depend on Cluster 4.
            @result: Cluster 2 depends on Cluster 4.
            @step: Attempt to create an expansion plan.
            @result: Assert that expansion plan creation
            failed due to circular dependency.
            @step: Revert expansion.
            @result: Deployment successfully reverted to 1 cluster with 1 node.
        @tms_test_precondition: Test environment has 1 cluster with 1 node.
        @tms_execution_type: Automated
        """

        # This test is not run as part of the KGB due to the execution time
        # taking too long

        self.log('info', '1. Check that test environment is correct. '
                         'Create a LITP snapshot.')
        self._check_deployment_type_and_create_snapshot()

        self.log('info', '2. Create three new clusters with one node each.')
        # Expand the LITP model with the new clusters and nodes
        self._expand_model()

        self.log('info', '2.1. Cluster 3 will have a dependency on Cluster 2.')
        props = 'dependency_list="c2"'
        self.execute_cli_update_cmd(self.ms1, self.cluster3['url'], props)

        self.log('info', '2.2. Cluster 4 will have a dependency on Cluster 2.')
        props = 'dependency_list="c2"'
        self.execute_cli_update_cmd(self.ms1, self.cluster4['url'], props)

        try:
            self.log('info', '3. Run an expansion plan.')
            self.run_and_check_plan(self.ms1, const.PLAN_IN_PROGRESS,
                                    plan_timeout_mins=5,
                                    add_to_cleanup=False)
            # Ensure plan is running
            self.assertTrue(self._is_plan_running(),
                            "Plan not in expected Running state.")

            self.log('info', '4. Wait for all nodes to be up.')
            # Wait for 40 minutes for all added nodes to be installed
            self._wait_for_nodes_installed(self.clusters_to_expand)
            self.log('info', '4.1. All nodes are up and SSHable.')

            # Other cluster(s) depend on the below cluster
            dependee_cluster = ['c2']
            # The below clusters depend on another cluster(s)
            depender_cluster = ['c3', 'c4']

            parallel_running = False  # To check if parallelism is detected
            cluster_sequence = []  # Store order of cluster tasks executed

            while self._is_plan_running():
                # Get list of phases with running tasks
                running = self.get_tasks_by_state(self.ms1)

                # Check if more than one phase is running
                if len(running) > 1:
                    parallel_running = True

                # To check what clusters are running tasks at a given time
                dependee_running = False
                depender_running = False

                # Iterate through the running tasks extracting
                # the cluster and task description
                for value in running.values():
                    for cluster, url_desc in value.iteritems():
                        # Ignore any tasks that update host files
                        if "host file" in url_desc[0]['desc']:
                            continue

                        # Get order that tasks are run in
                        cluster_sequence.append(cluster)

                        # Check what cluster(s) has running tasks
                        dependee_running = ((dependee_running == True) or
                                            (cluster in dependee_cluster))
                        depender_running = ((depender_running == True) or
                                            (cluster in depender_cluster))

                        # Ensure that a task from both the dependee and
                        # depender clusters are not running simultaneously
                        self._multiple_clusters_running(
                            dependee_running, depender_running)

            # Ensure that the plan has completed successfully
            self.assertEqual(self.get_current_plan_state(self.ms1),
                             const.PLAN_COMPLETE,
                             "Plan not in expected Running/Complete state.")
            self.log("info", "5. Plan completed successfully.")

            self.log('info', '6. Assert that at some stage, 2 phases '
                             'were running in parallel.')
            self.assertTrue(parallel_running,
                            "No phases were detected to run in parallel.")

            self.log("info", "7. Ensuring Phases ran in correct order.")
            # Get last occurrence of dependee cluster running in plan execution
            last_dependee = self._find_last_occurrence(
                            cluster_sequence, dependee_cluster[0])
            self.log('info', '7.1. Ensure that no dependee cluster '
                             'tasks ran after depender cluster tasks began.')
            self.assertFalse(
                dependee_cluster[0] in cluster_sequence[last_dependee + 1:],
                "Dependee task(s) ran after depender tasks began:"
                "\n{0}".format(cluster_sequence))

            self.log('info', '7.2. Ensure that no depender cluster '
                             'tasks began before dependee tasks finished.')
            for depender in depender_cluster:
                self.assertFalse(depender in cluster_sequence[:last_dependee],
                        "Depender task(s) ran before dependee "
                        "tasks finished:\n{0}".format(
                            cluster_sequence))

            self.log("info", "BEGINNING TEST FOR CIRCULAR DEPENDENCY.")

            self.log('info', '8.1. Cluster 4 will have a '
                             'dependency on Cluster 3.')
            props = 'dependency_list="c3"'
            self.execute_cli_update_cmd(self.ms1, self.cluster4['url'], props)
            self.log('info', '8.1. Cluster 3 will have a '
                             'dependency on Cluster 2.')
            props = 'dependency_list="c2"'
            self.execute_cli_update_cmd(self.ms1, self.cluster3['url'], props)
            self.log('info', '8.1. Cluster 2 will have a '
                             'dependency on Cluster 4.')
            props = 'dependency_list="c4"'
            self.execute_cli_update_cmd(self.ms1, self.cluster2['url'], props)

            self.log('info', '9. Attempt to create an expansion plan.')
            std_out, std_err, rc = self.execute_cli_createplan_cmd(
                self.ms1, expect_positive=False)

            self.log('info', '10. Assert that expansion plan '
                             'failed due to circular dependency.')
            self.assertEqual([], std_out)
            self.assertEqual(1, rc)
            self.assertTrue(
                any("circular dependency has been detected"
                    in s for s in std_err))

        finally:
            self._revert_expansion()
