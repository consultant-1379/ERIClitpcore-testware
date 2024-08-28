# -*- coding: utf-8 -*-
# coding: utf-8

"""
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     May 2016
@author:    Roman Jarzebiak
@summary:   Integration test for story 107192: As a LITP Architect I
            want LITP to generate internal
            instrumentation metrics for all of the LITP operations
            Agile: TORF-107192, TORF-119350
"""

from litp_generic_test import GenericTest, attr
import test_constants
from redhat_cmd_utils import RHCmdUtils
import datetime
import os
import re


class Story107192(GenericTest):
    """
    As a LITP Architect I want LITP to generate internal
    instrumentation metrics for all of the LITP operations
    """

    def setUp(self):
        """
        Runs before every single test.
        """
        super(Story107192, self).setUp()
        self.ms_node = self.get_management_node_filename()
        self.redhatutils = RHCmdUtils()
        self.metrics_log_file = test_constants.METRICS_LOG
        self.plugin_id = 'story107192'
        self._install_rpms()
        self.default_plugins = ['bootmgr_plugin',
                                'puppet_manager',
                                'core_plugin',
                                'package_plugin']
        self.expected_metrics = dict()
        self.expected_metrics['Create'] = [
            'NoOfAppliedModelItems',
            'NoOfCallbackTasks',
            'NoOfClusters',
            'NoOfConfigTasks',
            'NoOfExtensions',
            'NoOfForRemovalModelItems',
            'NoOfInitialModelItems',
            'NoOfModelItems',
            'NoOfModelItemsInPlan',
            'NoOfNodes',
            'NoOfPhases',
            'NoOfPlugins',
            'NoOfRemoteExecutionTasks',
            'NoOfUpdatedModelItems',
            'NoOfItemRemovalTasks',
            'PlanType',
            'Status',
            'TimeTaken',
            'TotalNoOfTasks'
        ]
        self.expected_metrics['PluginCreateConfiguration'] = [
            'TotalNoOfTasks',
            'NoOfConfigTasks',
            'NoOfCallbackTasks',
            'NoOfRemoteExecutionTasks',
            'TimeTaken'
        ]
        self.expected_metrics['Run'] = [
            'Status',
            'TimeTaken'
        ]
        self.expected_metrics['Clear'] = [
            'TimeTaken'
        ]
        self.expected_metrics['StorageSave'] = [
            'Size',
            'TimeTaken'
        ]
        self.expected_metrics['Phase'] = [
            'NoOfConfigTasks',
            'NoOfCallbackTasks',
            'NoOfRemoteExecutionTasks',
            'NoOfFailedTasks',
            'NoOfStoppedTasks',
            'NoOfSuccessfulTasks',
            'TimeTaken'
        ]

    def tearDown(self):
        """
        Runs after every single test.
        """
        super(Story107192, self).tearDown()

    def create_packages(self):
        """
        Function which creates a telnet package and links to the ms and mns
        """
        self.execute_cli_create_cmd(self.ms_node,
                                    "/software/items/trigger",
                                    'software-item'
                                    )

        self.execute_cli_create_cmd(self.ms_node,
                                    "/software/items/fail_trigger",
                                    'software-item'
                                    )

        # Create links in the deployment to the package
        self.execute_cli_inherit_cmd(self.ms_node,
                                     "/ms/items/story107192",
                                     "/software/items/trigger")
        # self.execute_cli_inherit_cmd(self.ms_node,
        #                              node1_deployment + "test107192",
        #                              "/software/items/test107192")

    @staticmethod
    def get_local_rpm_paths(path, rpm_id):
        """
        Description:
        Method that returns a list of absolute paths to the
        RPMs required to be installed for testing
        """
        # get all RPMs in 'path' that contain 'rpm_substring' in their name
        rpm_names = [rpm for rpm in os.listdir(path) if rpm_id in rpm]

        if not rpm_names:
            return None

        # return a list of absolute paths to the RPMs found in 'rpm_names'
        return [os.path.join(rpath, rpm)
                for rpath, rpm in
                zip([os.path.abspath(path)] * len(rpm_names), rpm_names)
                ]

    def _install_rpms(self):
        """
        Description:
        Method that installs plugin and extension
        if they are not already installed
        """
        # Check if the plugin is already installed
        _, _, rcode = self.run_command(
            self.ms_node, self.rhc.check_pkg_installed([self.plugin_id]),
            su_root=True)

        # If not, copy plugin and extension onto MS
        if rcode == 1:
            local_rpm_paths = self.get_local_rpm_paths(
                os.path.abspath(
                    os.path.join(os.path.dirname(__file__), 'plugins')
                ),
                self.plugin_id
            )
            self.assertTrue(
                self.copy_and_install_rpms(self.ms_node, local_rpm_paths))

    def grep_for_metric(self, metric):
        """
        Description:
        greps for metrics in the /var/log/litp/metrics.log file
        returns all matches based on the arguments
        """
        grep = self.redhatutils.get_grep_file_cmd(
            self.metrics_log_file,
            metric,
            '-F'
        )

        metrics, _, _ = self.run_command(
            self.ms_node, grep, su_root=True
        )

        return metrics

    @staticmethod
    def check_timestamps_match_format(metrics_log):
        """
        Description:
        checks if every log line has a timestamp of expected format
        """
        pattern = '%Y-%m-%d %H:%M:%S.%f'
        for line in metrics_log:
            timestamp = line.split(',[')[0]
            print timestamp
            try:
                datetime.datetime.strptime(timestamp, pattern)
            except ValueError:
                return False
        return True

    def _snapshot_item_exists(self):
        """
        Description:
            Determine if a snapshot item exists in the model.
        Results:
            Boolean, True if exists or False otherwise
         """
        snapshot_url = self.find(self.ms_node, "/snapshots",
                                 "snapshot-base", assert_not_empty=False)
        if snapshot_url:
            return True
        else:
            return False

    def check_create_snapshot_metric(self):
        """
        Description:
        asserts if PlanType=CreateSnapshot metric posted on create plan
        """
        metric = self.grep_for_metric(
            ',[LITP][PLAN][Create].PlanType=CreateSnapshot'
        )
        self.assertNotEqual(
            [], metric,
            'CreateSnapshot plan type metric should be posted'
        )

    def check_remove_snapshot_metric(self):
        """
        Description:
        asserts if PlanType=RemoveSnapshot metric posted on create plan
        """
        metric = self.grep_for_metric(
            ',[LITP][PLAN][Create].PlanType=RemoveSnapshot'
        )
        self.assertNotEqual(
            [], metric,
            'RemoveSnapshot plan type metric should be posted'
        )

    def validate_metric_vals(self, metrics):
        """
        Description:
        asserts if all metrics have a val and if it's a valid format
        if TimeTaken or Size checks if format is as expected
        """
        for metric in metrics:
            self.assertFalse(
                'UnableToGetMetricsValue' in
                metric.split('=')[-1] or not metric.split('=')[-1],
                'all metrics should be gathered successfully'
                'failed to gather {0} metric'.format(metric.split('=')[0]))
            if 'TimeTaken' in metric:
                self.assertTrue(re.match(r'TimeTaken=[\d]+\.[\d]{3}', metric),
                    'TimeTaken metric should be posted '
                    'with expected format, failed: {0}'.format(metric))
            if 'Size' in metric:
                self.assertTrue(re.match(r'Size=[\d]+', metric),
                    'Size metric should be posted '
                    'with expected format, failed: {0}'.format(metric))

    @attr('all', 'revert', 'story107192', 'story107192_tc01')
    def test_01_create_file_on_startup(self):
        """
        @tms_id: torf_107192_tc01
        @tms_requirements_id: TORF-107192
        @tms_title: Verify metrics created on startup of litpd service
        @tms_description: Checks if expected metrics are stored in
         the /var/log/litp/messages.log file on litp startiup
         and if file created if not present
         NOTE: also TORF-130163 litp-admin is able to write to and
         remove litp log files owned by root
        @tms_test_steps:
         @step: remove /var/log/litp/metrics.log file if present,
                restart litpd service
         @result: litpd starts successfully, /var/log/litp/messages.log
                file created
         @step: try to access (cat) /var/log/litp/metrics.log file
            as litp-admin
         @result: Permission denied
         @step: check expected startup metric posted in file
            ([LITP][Service][Startup] prefix) TimeTaken
            (has valid format that matches a regex)
         @result: metric added, no other metrics present
         @step: check timestamps in /var/log/litp/metrics/log
         @result: timestamp on every line matches
            %Y-%m-%d %H:%M:%S.%f
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        self.log('info', 'backing up metrics file')
        self.backup_file(self.ms_node, self.metrics_log_file,
                         backup_mode_cp=False)

        self.restart_litpd_service(self.ms_node)

        self.assertTrue(
            self.remote_path_exists(self.ms_node,
                                    self.metrics_log_file,
                                    su_root=True),
            'metric file should be created on startup'
        )

        cat_cmd = self.redhatutils.get_cat_cmd(self.metrics_log_file)

        _, err, _ = self.run_command(self.ms_node, cat_cmd)

        self.assertTrue(self.is_text_in_list('Permission denied', err),
                'litp-admin should not be able '
                'to access metrics file')

        metrics = self.grep_for_metric(['[LITP][Service][Startup]'])

        self.assertTrue(
            len(metrics) == 1,
            'only one metric should be added on startup'
        )

        metric = metrics[0].split("].")[-1]

        self.assertTrue(re.match(
            r'TimeTaken=[\d]+\.[\d]{3}',
            metric),
            'TimeTaken metric should be posted'
        )

        self.assertTrue(
            self.check_timestamps_match_format(
                self.get_file_contents(self.ms_node,
                                       self.metrics_log_file,
                                       su_root=True)
            )
        )

    @attr('all', 'revert', 'story107192', 'story107192_tc02')
    def test_02_pn_create_and_run_plan_metrics_collection(self):
        """
        @tms_id: torf_107192_tc02
        @tms_requirements_id: TORF-107192, TORF-119350
        @tms_title: Verify plan create and run metrics are collected
        @tms_description: Checks if expected metrics are stored in
         the /var/log/litp/messages.log file on litp create and run
         plan and if file created if not present
        @tms_test_steps:
         @step: remove /var/log/litp/metrics.loog file if present
                execute create_plan command with no tasks in litp,
                check /var/log/litp/metrics/log
         @result: file created, [LITP][PLAN][Create].Status=Aborted
                logged as no plan created
         @step: execute litp create and inherit commands to add model
                items as defined in test plugin, create a plan
         @result: plan created
         @step: check [PLAN][Create][Build] with TimeTaken present
         @result: expected metric logged
         @step: check for expected [LITP][PLAN][Create] metrics
                in /var/log/litp/metrics.log
         @result: all metrics present
         @step: check all [LITP][PLAN][Create] metrics have values
         @result: metrics logged, no value empty, no
                UnableToGetMetricValue errors logged
         @step: check metrics for [LITP][PLAN][Create][<pluginName>]
                [PluginUpdateModel]
                [ModelValidation]
                present (with TimeTaken) for plugins present on every litp
                system 'bootmgr_plugin', 'puppet_manager', 'core_plugin',
                'package_plugin' and the custom story107192 plugin
         @result: present with TimeTaken logged
         @step: check metrics for [LITP][PLAN][Create][plugin107192]
                [PluginCreateConfiguration]
         @result: metrics present should be 'TotalNoOfTasks=3',
                'NoOfConfigTasks=1',
                'NoOfCallbackTasks=1',
                'NoOfRemoteExecutionTasks=1'
                and a valid TimeTaken
         @step: delete /var/log/litp/metrics.log and
                execute litp run_plan and wait till plan COMPLETE
         @result: plan runs successfully, /var/log/litp/metrics.log created
                for run metrics collection
         @step: check metrics related to [LITP][PLAN][Run] collected in file
         @result: all metrics present, no UnableToGetMetricValue, TimeTaken
                logged
         @step: check metric for [LITP][Plan][Run][Clear] logged with a valid
                TimeTaken value
         @result: Clear Plan Run TimeTaken metric logged
         @step: check metrics for specific phases in plan
         @result: phase metrics logged successfully, has valid TimeTaken
         @step: Compare total plan run time with sum of run times of each phase
                and clear time as logged in metrics.log
         @result: plan total is not greater than the sum
         @step: remove previously created trigger item, create plan, run plan
         @result: plan can be created and ran
         @step: stop plan and wait for plan STOPPED state
         @result: plan stops, metric [LITP][PLAN][Run].Status=Stopped logged
         @step: inherit previously created fail_trigger item to create
                a failing callback task, create plan
         @result: plan created
         @step: run plan, wait for FAILED state
         @result: plan fails, [LITP][PLAN][Run].Status=Failed logged
                failed callback metric task logged within its phase
         @step: check timestamps
         @result: timestamp on every line matches
            %Y-%m-%d %H:%M:%S.%f
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        self.log('info', 'backing up metrics file')
        self.backup_file(self.ms_node, self.metrics_log_file,
                         backup_mode_cp=False)

        self.log('info', 'execute create_plan command with no tasks in litp')

        self.execute_cli_createplan_cmd(self.ms_node, expect_positive=False)
        self.assertTrue(
            self.remote_path_exists(self.ms_node,
                                    self.metrics_log_file,
                                    su_root=True),
            'metric file should be created to log plan create messages'
        )
        metrics = self.grep_for_metric(['[LITP][PLAN][Create].Status'])

        self.assertTrue(
            len(metrics) == 1,
            'only one metric should be added on status'
        )

        metric = metrics[0].split("].")[-1]

        self.log('info', '[LITP][PLAN][Create].Status=Aborted '
                         'logged as no plan created')
        self.assertTrue(
            metric == 'Status=Aborted'
        )

        self.log('info', 'execute litp create and inherit commands to add '
                         'model items as defined in test plugin, create plan')

        self.create_packages()

        self.remove_item(self.ms_node, self.metrics_log_file, su_root=True)
        self.execute_cli_createplan_cmd(self.ms_node)

        self.log('info', 'check [PLAN][Create][Build] with TimeTaken present')
        metrics = self.grep_for_metric(['[PLAN][Create][Build]'])

        self.assertTrue(
            len(metrics) == 1,
            'only one metric should be added on create build'
        )

        metric = metrics[0].split("].")[-1]

        self.assertTrue(re.match(
            r'TimeTaken=[\d]+\.[\d]{3}',
            metric),
            'build TimeTaken metric should be posted'
        )

        self.log('info', 'check for expected [LITP][PLAN][Create] metrics')
        create_metrics = [met.split('].')[-1] for met in
                          self.grep_for_metric(
                              ',[LITP][PLAN][Create].'
                          )]

        self.assertTrue(
            sorted(self.expected_metrics['Create']) ==
            sorted(m.split('=')[0] for m in create_metrics),
            'all expected plan create metrics posted'
        )

        self.log('info', 'check all [LITP][PLAN][Create] metrics have values')
        self.validate_metric_vals(create_metrics)

        self.log('info', 'check metrics for [LITP][PLAN][Create] '
                         '[<pluginName>]'
                         '[PluginUpdateModel]'
                         '[ModelValidation]')
        plugin_update_model_metrics = [m.split('][')[-1] for m in
                                       self.grep_for_metric(
                                    ',[LITP][PLAN][Create][PluginUpdateModel]'
                                       )]

        self.assertTrue(
            set(self.default_plugins + [self.plugin_id]).issubset(
                set([met.split('].')[0] for met
                     in plugin_update_model_metrics])
            ), 'plugin update model metrics for known plugins posted'
        )

        self.validate_metric_vals(
            [met.split('].')[-1] for met in plugin_update_model_metrics])

        model_validation_metrics = [m.split('][')[-1] for m in
                                    self.grep_for_metric(
                                ',[LITP][PLAN][Create][ModelValidation]'
                                    )]

        self.assertTrue(
            set(self.default_plugins + [self.plugin_id]).issubset(
                set([met.split('].')[0] for met in model_validation_metrics])
            ), 'model validation metrics for known plugins posted'
        )

        self.validate_metric_vals([met.split('].')[-1]
                                   for met in model_validation_metrics])

        self.log('info', 'check metrics for [LITP][PLAN][Create]'
                         '[plugin107192]'
                         '[PluginCreateConfiguration]')

        plugin_cc_metrics = [m.split('].')[-1] for m in
                             self.grep_for_metric(
                                 ',[LITP][PLAN][Create]'
                                 '[PluginCreateConfiguration][{0}]'.format(
                                     self.plugin_id
                                 )
                             )]

        self.assertTrue(
            sorted([k.split('=')[0]
                    for k
                    in plugin_cc_metrics]) ==
            sorted(self.expected_metrics['PluginCreateConfiguration']),
            'plugin create configuration metrics for test plugin posted'
        )

        self.validate_metric_vals(plugin_cc_metrics)

        self.assertTrue(
            self.check_timestamps_match_format(
                self.get_file_contents(self.ms_node,
                                       self.metrics_log_file,
                                       su_root=True)
            )
        )

        self.remove_item(self.ms_node, self.metrics_log_file, su_root=True)

        self.log('info', 'execute litp run_plan')

        self.execute_cli_runplan_cmd(self.ms_node)
        self.execute_cli_stopplan_cmd(self.ms_node)
        self.log('info', 'stop plan and wait for plan STOPPED state')

        self.assertTrue(
            self.wait_for_plan_state(self.ms_node,
                                     test_constants.PLAN_STOPPED)
        )
        self.log('info', 'metric [LITP][PLAN][Run].Status=Stopped logged')

        plan_stopped = self.grep_for_metric(
            ',[LITP][PLAN][Run].Status=Stopped'
        )

        self.assertNotEqual(
            [], plan_stopped,
            'Plan stopped metric should be posted'
        )

        self.execute_cli_createplan_cmd(self.ms_node)
        self.remove_item(self.ms_node, self.metrics_log_file, su_root=True)

        self.log('info', 'run plan and wait for plan COMPLETE state')
        self.execute_cli_runplan_cmd(self.ms_node)

        self.assertTrue(
            self.wait_for_plan_state(self.ms_node,
                                     test_constants.PLAN_COMPLETE)
        )
        self.assertTrue(
            self.remote_path_exists(self.ms_node,
                                    self.metrics_log_file,
                                    su_root=True),
            'metric file should be created to log plan run metrics'
        )

        self.log('info', 'check metrics related to [LITP][PLAN][Run] '
                         'collected')

        run_metrics = [met.split('].')[-1] for met in
                       self.grep_for_metric(
                           ',[LITP][PLAN][Run].'
                       )]
        self.assertTrue(
            sorted(self.expected_metrics['Run']) ==
            sorted(met.split('=')[0] for met in run_metrics),
            'all expected plan run metrics posted'
        )

        self.validate_metric_vals(run_metrics)

        total_time = [met.split("=")[-1] for met in run_metrics
                      if 'TimeTaken' in met][0]

        self.log('info', 'check metrics for specific phases in plan')

        for metric in run_metrics:
            if 'Status' in metric:
                self.assertTrue(
                    metric == 'Status=Success'
                )

        phase_one_run_metrics = [met.split('].')[-1] for met in
                                 self.grep_for_metric(
                                     ',[LITP][PLAN][Run][Phase1].'
                                 )]

        self.validate_metric_vals(phase_one_run_metrics)

        phase_one_time = [metric.split("=")[-1] for metric in
                          phase_one_run_metrics
                          if 'TimeTaken' in metric][0]

        phase_two_run_metrics = [met.split('].')[-1] for met in
                                 self.grep_for_metric(
                                     ',[LITP][PLAN][Run][Phase2].'
                                 )]

        self.validate_metric_vals(phase_one_run_metrics)

        phase_two_time = [metric.split("=")[-1] for metric in
                          phase_two_run_metrics
                          if 'TimeTaken' in metric][0]

        all_phase_metrics = [met.split('=')[0] for
                             met in phase_one_run_metrics]

        all_phase_metrics.extend(
            [met_2.split('=')[0] for
             met_2 in phase_two_run_metrics])

        self.assertTrue(
            sorted(self.expected_metrics['Phase']) ==
            sorted(set(all_phase_metrics)),
            'all expected plan run metrics for phase posted'
        )

        self.validate_metric_vals(phase_two_run_metrics)

        self.log('info', 'check run plan clear metric')

        run_clear_metric = [met.split('].')[-1] for met in
                            self.grep_for_metric(
                                ',[LITP][PLAN][Run][Clear].'
                            )]

        self.assertTrue(self.expected_metrics["Clear"] ==
                        [metric.split("=")[0] for metric in run_clear_metric],
                        "one run clear metric should be posted")

        self.validate_metric_vals(run_clear_metric)

        clear_time = run_clear_metric[0].split("=")[-1]

        # sanity check for time values
        self.assertTrue(
            float(total_time) >= (
                float(phase_one_time) +
                float(phase_two_time) +
                float(clear_time)
            ),
            'total run plan time should be greater or equal to sum of '
            'phase run times and clear time, current:\ntotal = {0},'
            '\nphase1 = {1},'
            '\nphase2 = {2}, '
            '\nclear  = {3}'.format(
                total_time,
                phase_one_time,
                phase_two_time,
                clear_time
            ))

        self.log('info', 'inherit previously created fail_trigger item '
                         'to create a failing callback task, create plan')

        self.execute_cli_inherit_cmd(
            self.ms_node,
            '/ms/items/story107192_fail',
            '/software/items/fail_trigger'
        )

        self.execute_cli_createplan_cmd(self.ms_node)
        self.remove_item(self.ms_node, self.metrics_log_file, su_root=True)

        self.log('info', 'run plan, wait for FAILED state')

        self.execute_cli_runplan_cmd(self.ms_node)

        self.assertTrue(
            self.wait_for_plan_state(self.ms_node,
                                     test_constants.PLAN_FAILED)
        )

        self.log('info', 'plan fails, [LITP][PLAN][Run].Status=Failed '
                         'logged failed callback metric task logged '
                         'within its phase')

        plan_failed = self.grep_for_metric(
            ',[LITP][PLAN][Run].Status=Fail'
        )

        grep_for_failed = self.redhatutils.get_grep_file_cmd(
            self.metrics_log_file,
            [r',\[LITP\]\[PLAN\]\[Run\]\[Phase.\]'
             r'\[.*story107192.*\].Status=Fail'],
        )

        callback_task_failed, _, _ = self.run_command(
            self.ms_node,
            grep_for_failed,
            su_root=True
        )

        self.assertNotEqual(
            [], plan_failed,
            'posted plan failed metric'
        )

        self.assertNotEqual(
            [], callback_task_failed,
            'posted callback task failed metric'
        )

        self.log('info', 'check timestamps on each line')

        self.assertTrue(
            self.check_timestamps_match_format(
                self.get_file_contents(self.ms_node,
                                       self.metrics_log_file,
                                       su_root=True)
            )
        )

    @attr('all', 'revert', 'story107192', 'story107192_tc03')
    def test_04_p_snapshot_related_metrics_collection(self):
        """
        @tms_id: torf_107192_tc04
        @tms_requirements_id: TORF-107192
        @tms_title: Verify metrics created on snapshot create and remove
        @tms_description: Checks if an expected create plan type is logged
        on
        @tms_test_steps:
         @step: create snapshot, wait for plan to complete
         @result: snapshot created
         @step: check expected startup metric posted in file
            ([LITP][PLAN][Create].Type=CreateSnapshot)
         @result: metric added
         @step: remove snapshot, wait for plan to complete
         @result: snapshot removed
         @step: check expected startup metric posted in file
            ([LITP][PLAN][Create].Type=RemoveSnapshot)
         @result: metric added
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        self.log('info', 'backing up metrics file')
        self.backup_file(self.ms_node, self.metrics_log_file,
                         backup_mode_cp=False)
        # order of operations depending on whether a snapshot already exists
        # in the system or not, if exists - do remove, then create
        # if not - do create, then remove

        if self._snapshot_item_exists():

            self.execute_cli_removesnapshot_cmd(self.ms_node)
            self.assertTrue(self.wait_for_plan_state(self.ms_node,
                                            test_constants.PLAN_COMPLETE))

            self.assertTrue(
                self.remote_path_exists(self.ms_node,
                                        self.metrics_log_file,
                                        su_root=True),
                'metric file should be created to log plan create messages'
            )

            self.check_remove_snapshot_metric()

            self.execute_cli_createsnapshot_cmd(self.ms_node)
            self.assertTrue(self.wait_for_plan_state(self.ms_node,
                                            test_constants.PLAN_COMPLETE))
            self.check_create_snapshot_metric()

        else:
            self.execute_cli_createsnapshot_cmd(self.ms_node)
            self.assertTrue(self.wait_for_plan_state(self.ms_node,
                                            test_constants.PLAN_COMPLETE))
            self.assertTrue(
                self.remote_path_exists(self.ms_node,
                                        self.metrics_log_file,
                                        su_root=True),
                'metric file should be created to log plan create messages'
            )
            self.check_create_snapshot_metric()

            self.execute_cli_removesnapshot_cmd(self.ms_node)
            self.assertTrue(self.wait_for_plan_state(self.ms_node,
                                            test_constants.PLAN_COMPLETE))
            self.check_remove_snapshot_metric()
