"""
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     August 2015
@author:    Maria Varley
@summary:   LITPCDS-10575
            As a LITP Architect I want ERIClitpcore to generate configTasks
            to cater for the removal of Puppet resources from a node's
            manifest triggered by Model Item removal. (Part 1 of 3)
"""
import os
import re
from litp_generic_test import GenericTest, attr
from redhat_cmd_utils import RHCmdUtils
import test_constants as const
import time

LOCAL_PLUGINS_DIR = os.path.abspath(
                        os.path.join(os.path.dirname(__file__), 'plugins'))


class Story10575(GenericTest):
    """
    As a LITP Architect I want ERIClitpcore to generate configTasks to cater
    for the removal of Puppet resources from a node's manifest triggered
    by Model Item removal. (Part 1 of 3)
    """

    def setUp(self):
        """ Runs before every single test """
        super(Story10575, self).setUp()

        self.ms1 = self.get_management_node_filenames()[0]
        self.mn1 = self.get_managed_node_filenames()[0]
        self.plugin_id = 'story10575'
        self.item_type = 'story-10575a'
        self.depend_type = 'depend-story-10575'
        self.depend_type2 = 'depend2-story-10575'
        self.rhel = RHCmdUtils()
        self.timestamp_regex = re.compile(r'\w{3}\s+\d{1,2} \d{2}:\d{2}:\d{2}')
        self.litp_service_bin_file_path = \
                            '/opt/ericsson/nms/litp//bin/litp_service.py'

    def tearDown(self):
        """ Runs after every single test """
        super(Story10575, self).tearDown()
        self._uninstall_rpms()

    def ensure_puppet_is_not_running_or_about_to_run(self):
        """
        The puppet timeout value is triggered from the time the
        puppet runonce is called. It is not dependent on the
        mco cycle or puppet_poll_interval. The biggest delay is
        due to an ongoing puppet run
        Puppet run interval is 12 minutes
        """
        self.log('info',
                 'Ensuring that puppet is not applying catalog' +\
                 'on the MS before running plan')
        self.wait_for_puppet_idle(self.ms1, self.ms1)

        cmd = '/usr/bin/mco puppet status | grep ms1'
        self.log('info',
                 'ensuring that there is at least 2 minutes ' +\
                 'before next scheduled puppet run')

        for _ in range(0, 2):
            std_out, _, rcode = self.run_command(self.ms1, cmd)
            self.assertTrue(rcode == 0,
                            "Failed to get response from mco puppet status")

            search_pattern = re.compile(r'Currently idling; last completed' +\
                                        r' run (\d+) minutes \d+ seconds ago')

            search_result = search_pattern.match(std_out[0])
            if search_result:
                elapsed_puppet_time = int(search_result.groups()[-1])
                if elapsed_puppet_time > 9:
                    self.log('info',
                             'Puppet was last executed ' +\
                             '{0}'.format(elapsed_puppet_time) +\
                             ' minutes ago, sleeping for 180 sec')
                    time.sleep(180)
                else:
                    self.log('info',
                             'Puppet was last executed ' +\
                             '{0}'.format(elapsed_puppet_time) +\
                             ' minutes ago, running the plan')
                    break

    def _install_rpms(self, node, local_rpm_dir, rpm_filter):
        """
        Description:
            Install RPMs that match the given filter on the specified node
        Args:
            node (str): The node on which to install the RPMs
            local_rpm_dir (str): The directory where RPM files are located
            rpm_filter (str): Pattern used to select the RPMs required for
                              testing
        """
        rpms = self.get_local_rpm_path_ls(local_rpm_dir, rpm_filter)
        rpms_to_install = []
        for rpm in rpms:
            pkg_name = (os.path.basename(rpm)).rstrip('.rpm')
            is_pkg_installed = self.check_pkgs_installed(node,
                                                         [pkg_name],
                                                         su_root=True)
            if not is_pkg_installed:
                rpms_to_install.append(rpm)
        if rpms_to_install:
            self.assertTrue(self.copy_and_install_rpms(node, rpms_to_install))

    @staticmethod
    def get_local_rpm_paths(path, rpm_id):
        """
        Description:
            Method that returns a list of absolute paths to the
            RPMs required to be installed for testing.
        Args:
            path (str): Path dir to check for RPMs.
            rpm_id (str): RPM name to check for in path.
        """
        # Get all RPMs in 'path' that contain 'rpm_id' in their name
        rpm_names = [rpm for rpm in os.listdir(path) if rpm_id in rpm]

        if not rpm_names:
            return None

        # Return a list of absolute paths to the RPMs found in 'rpm_names'
        return [
            os.path.join(rpath, rpm)
            for rpath, rpm in
            zip([os.path.abspath(path)] * len(rpm_names), rpm_names)
            ]

    def _uninstall_rpms(self):
        """
        Description:
            Method that uninstalls plugin and extension on
            the MS.
        """
        local_rpm_paths = self.get_local_rpm_paths(
            os.path.join(
                os.path.dirname(repr(__file__).strip("'")), "plugins"
                ),
            self.plugin_id
            )

        if local_rpm_paths:
            installed_rpm_names = []
            for rpm in local_rpm_paths:
                std_out, std_err, rc = self.run_command_local(
                    self.rhc.get_package_name_from_rpm(rpm))
                self.assertEquals(0, rc)
                self.assertEquals([], std_err)
                self.assertEquals(1, len(std_out))

                installed_rpm_names.append(std_out[0])

            _, _, rc = self.run_command(self.ms1,
                                        self.rhc.get_yum_remove_cmd(
                                            installed_rpm_names),
                                        add_to_cleanup=False,
                                        su_root=True
                                       )
            self.assertEquals(0, rc)

    def _check_puppet_manifest(self, node, task_id, expect_positive=True):
        """
        Description:
        Method that checks the puppet manifests for an expected task id
        Will assert success (by default) or failure if the expect_positive
        argument is passed in as False.

        Args:
        node (str): Node you want to run command on

        task_id (str): Task to search manifest for

        Kwargs:
        expect_positive (bool): By default assumes command will run
                                without failure

        Returns:
        list, Puppet manifest lines if expect_positive=True
        """
        grep_cmd = self.rhc.get_grep_file_cmd(
            const.PUPPET_MANIFESTS_DIR + "/" + node + ".pp", task_id,
            grep_args="-A 3 -B 2"
        )

        std_out, std_err, rcode = self.run_command(self.ms1, grep_cmd,
            su_root=True)

        if expect_positive:
            self.assertNotEqual([], std_out)
            self.assertEqual([], std_err)
            self.assertEqual(0, rcode)

            return std_out

        else:
            self.assertEqual([], std_out)
            self.assertEqual([], std_err)
            self.assertEqual(1, rcode)

    def _get_puppet_manifest_data(self, manifest_file, class_id, log=True):
        """
        Description:
            Get contents of the class from specified puppet manifest file for
            the given class id
        Args:
            manifest_file (str): The manifest file to search
            class_id (str)     : The ID of the required class
            log (bool)         : Controls log dump
        Return:
            list, The content of the class definition
        """
        manifest_file_path = os.path.join(const.PUPPET_MANIFESTS_DIR,
                                          manifest_file)
        cmd = '/bin/grep -F -A 15 "{0}" {1}'. \
              format(class_id, manifest_file_path)
        stdout, _, _ = self.run_command(self.ms1, cmd, logging=False,
            su_root=True)

        manifest_data = []
        class_regex = re.compile('class ')
        for i, line in enumerate(stdout[1:]):
            if class_regex.match(line):
                manifest_data = stdout[:i]
                break
        if log:
            for line in manifest_data:
                self.log('info', line)

        return manifest_data

    @staticmethod
    def _parse_puppet_manifest(manifest_output):
        """
        Description:
        Method that parses the puppet manifest and checks that it contains
        expected values defined

        Args:
        manifest_output (str): Output from the manifest file to be parsed
        manifest_item (dict): Dictionary defining expected values
        """
        line_parts = list()
        for line in manifest_output:
            # Split will remove (){ from end of puppet class in manifest
            line_parts.append(re.split(r'\s|\(', line))

        return line_parts

    def _check_parse_puppet_manifest(self, expected_item, manifest_item):
        """
        Description:
        Checks the parsed manifest output
        contains expected values
        """
        self.assertEqual(expected_item["class_id"], manifest_item[0][1])
        self.assertEqual(expected_item["type"], manifest_item[1][0])

    def _get_coll_of_sw_item_url(self):
        """
        Description:
            Get path to collection of software item on MS
        """
        url = self.find(self.ms1,
                        '/software',
                        'collection-of-software-item')[0]
        return url

    def _get_ref_coll_of_item_url(self):
        """
        Description:
            Get path to reference to collection of software item on MS
        """
        url = self.find(self.ms1,
                        '/ms',
                        'ref-collection-of-software-item')[0]
        return url

    def get_node1_path(self):
        """
        Description:
        Returns nodes path under /deployments path
        """
        node_paths = self.find(self.ms1, "/deployments", "node", True)
        return node_paths[0]

    def _check_item_state(self, item_path, expected_state):
        """
        Method that compares the value of a property of
        a model item with an expected value of the property
        """
        actual_state = self.get_item_state(self.ms1, item_path)
        self.assertEqual(expected_state, actual_state)

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

            new_line = '{0} = {1}'.format(param, str(value))
            cmd = "/bin/sed -i 's/^{0}/{1}/g' {2}". \
                  format(line_to_update, new_line, const.LITPD_CONF_FILE)
            self.run_command(self.ms1, cmd, su_root=True, default_asserts=True)

        # Restart "celeryd" service so changes take effect
        self.stop_service(self.ms1, 'celery.service')
        self.start_service(self.ms1, 'celery.service')

        return initial_conf

    @staticmethod
    def _diffdates(timestamp1, timestamp2):
        """ Returns time difference in seconds"""
        return (time.mktime(time.strptime(timestamp2, "%b %d %H:%M:%S")) -
                time.mktime(time.strptime(timestamp1, "%b %d %H:%M:%S")))

    def _get_msg_timestamp(self, node, message, cursor_pos, timeout, index=1):
        """
        Description:
            Get timestamp of the first line in "/var/log/messages" that matches
            the given string
        Args:
            node (str)          : The node on which to check the messages file
            message (str)       : The message to look for
            cursor_pos (int)    : The line to start the search from
            timeout (int)       : Max time in seconds allowed for the string to
                                  appear in "messages" file
            index (int)         : Specify which occurrence of the match to use
        Returns:
            string, The timestamp of the "N" line of "messages" that matches
                    the given pattern
        """
        self.assertTrue(index >= 1,
            'Invalid index passed to _get_msg_timestamp() function')
        lines = self.wait_for_log_msg(node,
                                      message,
                                      log_len=cursor_pos,
                                      timeout_sec=timeout,
                                      return_log_msgs=True)
        self.assertTrue(len(lines) >= index,
            'Not enough occurrences of the string "{0}" were found in '
            '"/var/log/messages" file'
            .format(message))

        try:
            return self.timestamp_regex.match(lines[index - 1]).group()
        except AttributeError:
            self.fail('No valid timestamp section found on line "{0}"'.
                       format(lines[index - 1]))

    def _get_tasks_in_phase(self, plan, phase_number):
        """
        Description:
            Get description of all tasks in the given phase
        Args:
            plan (list): The plan listing
            phase_number (int): the phase we want the tasks of
        Returns:
            list, The list of tasks in the given phase
        """
        number_of_tasks_in_phase = \
            self.cli.get_num_tasks_in_phase(plan, phase_number)
        task_counter = 0
        tasks_in_phase = []
        while task_counter <= number_of_tasks_in_phase:
            tasks_in_phase.append(
                self.cli.get_task_desc(plan, phase_number, task_counter))
            task_counter += 1

        task_descriptions = []
        for description in tasks_in_phase:
            task_descriptions.append(description[1])

        return task_descriptions

    def _assert_task_in_phase(self, expected_tasks, actual_tasks):
        """
        Description:
            Assert that expected tasks are found in a given phase
        Args:
            expected_tasks (list): List of tasks expected
            actual_task (list): The actual tasks in the phase
        """
        actual_tasks.remove('-----------')
        self.assertEqual(sorted(expected_tasks), sorted(actual_tasks),
            'TASK MISMATCH\nExpected:\n{0}\nActual:\n{1}'
            .format('\n'.join(expected_tasks), '\n'.join(actual_tasks)))

    def _wait_for_text_in_manifest(self,
                    manifest_file, text, timeout, polling_interval=3):
        """
        Description
            wait until the specified string appears in the specified file
        Args:
            manifest_file (str): the manifest file to search
            text (str)         : the string to search for
            timeout (int)      : Max allowed time
            polling_intervall (int): Interval between polling
        Return:
            bool, True if string is found within the given time
        """
        cmd = 'cat {0}'.format(manifest_file)
        elapsed_time = 0
        while True:
            if elapsed_time > timeout:
                return False

            manifest_contents = self.run_command(self.ms1,
                                                 cmd,
                                                 su_root=True,
                                                 default_asserts=True,
                                                 logging=False)[0]

            if self.is_text_in_list(text, manifest_contents):
                return True

            time.sleep(polling_interval)
            elapsed_time += polling_interval

    def _assert_class_in_manifest(self, ms_manifest_file, items, class_ids):
        """
        Description
            Verify that the expected classes that define resource
            associated with the given items are present in the
            specified puppet manifest file
        Args:
            ms_manifest_file (str): The path to the manifest file to search
            items (list)          : The items to check for
            class_ids (list)      : The class ids to check for
        """
        for item in items:
            for resource in class_ids:
                if item.get(resource):
                    class_data = self._get_puppet_manifest_data(
                                                    ms_manifest_file,
                                                    item[resource])
                    self.assertNotEqual([], class_data,
                        'Puppet class "{0}" not found in manifest "{1}"'
                        .format(item[resource], ms_manifest_file))

    def _is_litpd_daemon_running(self):
        """
        Description
            Determine if "litp_service.py" process is running as daemon
        """
        cmd = '/usr/bin/pgrep -xf "python {0} --daemonize" -P 1'. \
              format(self.litp_service_bin_file_path)
        if len(self.run_command(self.ms1, cmd)[0]) == 1:
            return True
        return False

    def _wait_for_litpd_running(self, timeout=60, polling_freq=2):
        """
        Description
            Wait for the "litpd" service to become available
        Args:
            timeout (int)     : Max allowed time for litpd to become available
            polling_freq (int): Specify the polling interval
        """
        elapsed_time = 0
        while True:
            if elapsed_time > timeout:
                return False
            if self._is_litpd_daemon_running():
                break
            time.sleep(polling_freq)
            elapsed_time += polling_freq

        cmd = '/usr/bin/litp version'
        elapsed_time = 0
        while True:
            if elapsed_time > timeout:
                return False
            stdout, stderr, _ = self.run_command(self.ms1, cmd)
            if [] == stderr and self.is_text_in_list('LITP', stdout):
                return True
            time.sleep(polling_freq)
            elapsed_time += polling_freq

    @attr('all', 'revert', 'story10575', 'story10575_t01', 'bur_only_test')
    def test_01_p_no_associatedDeconfigTask_persistedTask(self):
        """
        @tms_id: litpcds_10575_tc01
        @tms_requirements_id: LITPCDS-10575, TORF-107192, TORF-119350
        @tms_title: Replacement ForRemoval task for items with no deconfigure
             tasks and persisted ConfigTasks present.
        @tms_description: Test that on the removal of a Model Item for which
             a plugin does not create an associated "ForRemoval" ConfigTask but
             a persisted ConfigTask(s) exists, a replacement "ForRemoval"
             ConfigTask for this model Item will be generated which will be
             phased in accordance with current task ordering rules
             Also verify story TORF-107192 (test_05_pn_xml_metrics_collection)
        @tms_test_steps:
            @step: Create and deploy new items using the dummy plugin
            @result: Item deployed successfully
            @step: Remove all the previously created Items and execute the
                   "create_plan" command
            @result: A Removal ConfigTask is generated for the Model items
                     that do not have associated deconfigure tasks
            @result: Tasks are placed in the correct phase
            @step: Execute "run_plan" command and wait until phase 2 task is
                   running to check puppet
            @result: All Puppet resources previously associated
                     with the model item are replaced with Notify resources
            @step: Resume the plan execution
            @result: Plan completed successfully
            @result: "notify" resource removed from the puppet manifest
            @step: Check /var/log/litp/metrics.log
            @result: "NoOfOrderedTaskList" metrics are logged with valid values
        @tms_test_precondition: Cluster with two (or more) nodes is deployed.
            Plugin available that will generate node lock/unlock tasks.
        @tms_execution_type: Automated
        """
        ms_manifest_file = '{0}.pp'.format(self.ms1)
        metrics_file = const.METRICS_LOG
        metrics_file_1 = const.METRICS_LOG + ".1"
        metrics_log_pos = self.get_file_len(self.ms1, metrics_file)

        self.log('info',
        '1. Install plugin rpms required for testing')
        self._install_rpms(self.ms1, LOCAL_PLUGINS_DIR, self.plugin_id)

        self.log('info',
        '2. Create new model items')
        coll_sw_item_url = self._get_coll_of_sw_item_url()
        ms_coll_sw_item_url = self._get_ref_coll_of_item_url()

        # In order deploy item of type "story-10575a" we need to create a
        # source item under /software and then inherit it (on the MS in
        # this case).
        # In the following section we define 2 source/child item pairs
        # with property "deconfigure" set to "true" and 2 source/child item
        # pairs with "deconfigure" set to "false"
        source_1 = {}
        source_1['id'] = 'story10575-tc01-s1'
        source_1['url'] = os.path.join(coll_sw_item_url, source_1['id'])
        source_1['type'] = 'story-10575a'
        source_1['props'] = ('name=test_01a '
                             'deconfigure=true ')
        source_1['remove_task'] = 'Remove Item'

        child_1 = {}
        child_1['id'] = 'story10575-tc01-c1'
        child_1['url'] = os.path.join(ms_coll_sw_item_url, child_1['id'])
        child_1['conf_task_1'] = \
            'First ConfigTask test_01a on node {0}'.format(self.ms1)
        child_1['call_task_1'] = 'standalone CallbackTask test_01a'
        child_1['call_task_2'] = 'Another CallbackTask test_01a'
        child_1['deconf_task'] = \
            'ConfigTask deconfigure test_01a on node {0}'.format(self.ms1)
        child_1['class_file_id'] = (
            'class task_{0}__file__file10575test__01a__task__id__test__01a'
            .format(self.ms1))

        source_2 = {}
        source_2['id'] = 'story10575-tc01-s2'
        source_2['url'] = os.path.join(coll_sw_item_url, source_2['id'])
        source_2['type'] = 'story-10575a'
        source_2['props'] = ('name=test_02a '
                             'deconfigure=true '
                             'wait=true '
                             'multipleconfig=true '
                             'packagename=firefox')
        source_2['remove_task'] = 'Remove Item'

        child_2 = {}
        child_2['id'] = 'story10575-tc01-c2'
        child_2['url'] = os.path.join(ms_coll_sw_item_url, child_2['id'])
        child_2['conf_task_1'] = \
            'First ConfigTask test_02a on node {0}'.format(self.ms1)
        child_2['conf_task_2'] = \
            'Second ConfigTask test_02a on node {0}'.format(self.ms1)
        child_2['call_task_1'] = 'standalone CallbackTask test_02a'
        child_2['call_task_2'] = 'Another CallbackTask test_02a'
        child_2['deconf_task'] = \
            'ConfigTask deconfigure test_02a on node {0}'.format(self.ms1)
        child_2['call_task_wait'] = 'Wait CallbackTask test_02a'
        child_2['class_file_id'] = (
            'class task_{0}__file__file10575test__02a__task__id__test__02a'
            .format(self.ms1))
        child_2['class_pkg_id'] = (
            'class task_{0}__package__firefox10575__task__id__test__02a'
            .format(self.ms1))

        source_3 = {}
        source_3['id'] = 'story10575-tc01-s3'
        source_3['url'] = os.path.join(coll_sw_item_url, source_3['id'])
        source_3['type'] = 'story-10575a'
        source_3['props'] = ('name=test_03a '
                             'deconfigure=false ')
        source_3['remove_task'] = 'Remove Item'

        child_3 = {}
        child_3['id'] = 'story10575-tc01-c3'
        child_3['url'] = os.path.join(ms_coll_sw_item_url, child_3['id'])
        child_3['conf_task_1'] = \
            'First ConfigTask test_03a on node {0}'.format(self.ms1)
        child_3['call_task_1'] = 'standalone CallbackTask test_03a'
        child_3['call_task_2'] = 'Another CallbackTask test_03a'
        child_3['remove_task'] = \
            'Remove Item\'s resource from node "{0}" puppet'.format(self.ms1)
        child_3['class_file_id'] = (
            'class task_{0}__file__file10575test__03a__task__id__test__03a'
            .format(self.ms1))

        source_4 = {}
        source_4['id'] = 'story10575-tc01-s4'
        source_4['url'] = os.path.join(coll_sw_item_url, source_4['id'])
        source_4['type'] = 'story-10575a'
        source_4['props'] = ('name=test_04a '
                             'deconfigure=false '
                             'multipleconfig=true '
                             'packagename=telnet')
        source_4['remove_task'] = 'Remove Item'

        child_4 = {}
        child_4['id'] = 'story10575-tc01-c4'
        child_4['url'] = os.path.join(ms_coll_sw_item_url, child_4['id'])
        child_4['conf_task_1'] = \
            'First ConfigTask test_04a on node {0}'.format(self.ms1)
        child_4['conf_task_2'] = \
            'Second ConfigTask test_04a on node {0}'.format(self.ms1)
        child_4['call_task_1'] = 'standalone CallbackTask test_04a'
        child_4['call_task_2'] = 'Another CallbackTask test_04a'
        child_4['remove_task'] = \
            'Remove Item\'s resource from node "{0}" puppet'.format(self.ms1)
        child_4['class_file_id'] = (
            'class task_{0}__file__file10575test__04a__task__id__test__04a'
            .format(self.ms1))
        child_4['class_pkg_id'] = (
            'class task_{0}__package__telnet10575__task__id__test__04a'
            .format(self.ms1))

        all_source_items = [source_1, source_2, source_3, source_4]
        all_child_items = [child_1, child_2, child_3, child_4]

        for item in all_source_items:
            self.execute_cli_create_cmd(self.ms1,
                                        item['url'],
                                        item['type'],
                                        item['props'])
        for source, child in zip(all_source_items, all_child_items):
            self.execute_cli_inherit_cmd(self.ms1,
                                         child['url'],
                                         source['url'])

        self.log('info',
        '3. Create the plan and check it is as expected')
        # Plugin uses OrderedTaskList tasks to create
        # a chain of tasks, 2 ConfigTasks and 1 callback task
        # Each task becomes a dependency of the previous one
        # resulting in the callback task in its own phase
        # The plugin also generates a standalone callback task
        # which has no dependency on other tasks but is inserted
        # into the plan in the second phase due to LITPCDS-11400
        # and bug LITPCDS-12304 introducing new core dependencies.
        # The plan has 2 phases:
        self.execute_cli_createplan_cmd(self.ms1)
        plan_raw, _, _ = self.execute_cli_showplan_cmd(self.ms1)
        self.assertEqual(int(2), self.cli.get_num_phases_in_plan(plan_raw))

        # Check that the expected callback task not in ordered list
        # and with no dependency is in the second phase of the plan
        # and that there is one for each item created
        # Callback tasks are pushed to the second phase due to model-driven
        # dependencies (LITPCDS-11400 and associated bug LITPCDS-12304)
        expected_tasks_phase_1 = [child_1['conf_task_1'],
                                  child_2['conf_task_1'],
                                  child_2['conf_task_2'],
                                  child_3['conf_task_1'],
                                  child_4['conf_task_1'],
                                  child_4['conf_task_2']]

        expected_tasks_phase_2 = [child_1['call_task_1'],
                                  child_1['call_task_2'],
                                  child_2['call_task_1'],
                                  child_2['call_task_2'],
                                  child_3['call_task_1'],
                                  child_3['call_task_2'],
                                  child_4['call_task_1'],
                                  child_4['call_task_2']]

        phase1_tasks = self._get_tasks_in_phase(plan_raw, 1)
        phase2_tasks = self._get_tasks_in_phase(plan_raw, 2)

        self._assert_task_in_phase(expected_tasks_phase_1, phase1_tasks)
        self._assert_task_in_phase(expected_tasks_phase_2, phase2_tasks)

        self.log('info',
        '4. Run the plan and wait for completion')
        self.execute_cli_runplan_cmd(self.ms1)
        self.assertTrue(self.wait_for_plan_state(self.ms1,
                                                 const.PLAN_COMPLETE,
                                                 timeout_mins=5))

        self.log('info',
        '5. Check that puppet manifest file on MS is correct')
        items = [child_1, child_2, child_3, child_4]
        class_ids = ['class_file_id', 'class_pkg_id']
        self._assert_class_in_manifest(ms_manifest_file, items, class_ids)

        self.log('info',
        '6. Remove the items created previously and check the plan')
        for item in all_child_items + all_source_items:
            self.execute_cli_remove_cmd(self.ms1, item['url'])
        self.execute_cli_createplan_cmd(self.ms1)

        plan_raw, _, _ = self.execute_cli_showplan_cmd(self.ms1)
        self.assertEqual(int(3), self.cli.get_num_phases_in_plan(plan_raw))

        expected_tasks_phase_1 = [child_1['deconf_task'],
                                  child_2['deconf_task'],
                                  child_2['deconf_task'],
                                  child_3['remove_task'],
                                  child_4['remove_task']]

        expected_tasks_phase_3 = [source_1['remove_task'],
                                  source_2['remove_task'],
                                  source_3['remove_task'],
                                  source_4['remove_task']]

        phase1_tasks = self._get_tasks_in_phase(plan_raw, 1)
        phase3_tasks = self._get_tasks_in_phase(plan_raw, 3)

        self._assert_task_in_phase(expected_tasks_phase_1, phase1_tasks)
        self._assert_task_in_phase(expected_tasks_phase_3, phase3_tasks)

        self.log('info',
        '7. Run the plan and wait until it reaches the "wait" callback task')
        # This task will wait until the file "/tmp/story10575.txt" is
        # present
        self.execute_cli_runplan_cmd(self.ms1)
        self.assertTrue(self.wait_for_task_state(self.ms1,
                                                 child_2['call_task_wait'],
                                                 const.PLAN_TASKS_RUNNING,
                                                 ignore_variables=False,
                                                 timeout_mins=5))

        self.log('info',
        '8. Check MS puppet manifest file for "notify" resource definition')
        child_3['class_notify_id'] = (
            'class task_{0}__notify___2fms_2fitems_2fstory10575_2dtc01_2dc3'
            .format(self.ms1))

        child_4['class_notify_id'] = (
            'class task_{0}__notify___2fms_2fitems_2fstory10575_2dtc01_2dc4'
            .format(self.ms1))

        items = [child_3, child_4]
        class_ids = ['class_notify_id']
        self._assert_class_in_manifest(ms_manifest_file, items, class_ids)

        items = [child_1, child_2]
        class_ids = ['class_file_id', 'class_pkg_id']
        self._assert_class_in_manifest(ms_manifest_file, items, class_ids)

        self.log('info',
        '9. Resume the plan execution and wait until it completes')
        # We achieve that by touching the file "/tmp/story10575.txt" which
        # will unlock the waiting task
        self.run_command(self.ms1,
                         "touch /tmp/story10575.txt",
                         su_root=True,
                         add_to_cleanup=True)
        self.assertTrue(self.wait_for_plan_state(self.ms1,
                                                 const.PLAN_COMPLETE,
                                                 timeout_mins=5))

        self.log('info',
        '10. Check all the MS puppet resources created by this test are '
            'removed')
        for item in [child_1, child_2, child_3, child_4]:
            for resource in ['class_file_id', 'class_pkg_id']:
                if item.get(resource):
                    class_data = self._get_puppet_manifest_data(
                                                    ms_manifest_file,
                                                    item[resource])
                    self.assertEqual([], class_data,
                        'Extra puppet class "{0}" found in manifest "{1}"'
                        .format(item[resource], ms_manifest_file))

        self.log('info',
        '11. Check "NoOfOrderedTaskList" metrics')
        lines = self.wait_for_log_msg(self.ms1,
                                      'NoOfOrderedTaskList',
                                      log_file=metrics_file,
                                      timeout_sec=10,
                                      log_len=metrics_log_pos,
                                      rotated_log=metrics_file_1,
                                      return_log_msgs=True)

        actual_metrics = {}
        for line in lines:
            parts = line.split('=')
            actual_metrics[parts[0]] = parts[1]

        expected_metrics = {
           '[LITP][PLAN][Create][PluginCreateConfiguration][story10575].'
           'NoOfOrderedTaskList': int
        }

        for exp_key, exp_type in expected_metrics.iteritems():
            for act_key, act_val in actual_metrics.iteritems():
                if act_key.endswith(exp_key):
                    try:
                        act_val = exp_type(act_val)
                    except ValueError:
                        act_val = None
                    self.assertNotEqual(None, act_val,
                                        'Wrong value type for'
                                        ' metric "{0}"'.
                                        format(exp_key))
                    break
            else:
                self.fail('Metrics not found for "{0}"'.format(exp_key))

    @attr('all', 'revert', 'story10575', 'story10575_t02', 'bur_only_test')
    def test_02_p_task_list_ordering_maintained(self):
        """
        @tms_id: litpcds_10575_tc02
        @tms_requirements_id: LITPCDS-10575
        @tms_title: Task list ordering is maintained at removal
             when Model Item tasks have dependencies on one another
        @tms_description: Test that Task depending on task that is
             in "ForRemoval" state will adjust its dependecy
        @tms_test_steps:
            @step: Create a deployment model with the following dependencies:
            A <--B <--C where B has no associated deconfigure task
            @result: The items are created
            @step: create and run plan
            @result: plan runs successfully, all items in Applied state
            @result: manifest contains expected dependency
            @step: remove item B, create and run plan
            @result: plan runs successfully
            @result: manifest has updated dependency
        @tms_test_precondition: Cluster with two (or more) nodes is deployed.
            Plugin available that will generate node lock/unlock tasks.
        @tms_execution_type: Automated
        """
        # Presequite:
        self.log('info', 'Install Plugin rpms required for testing')
        self._install_rpms(self.ms1, LOCAL_PLUGINS_DIR, self.plugin_id)

        file_task = "task_ms1__file__call__id__depend1"
        notify_task = "task_ms1__notify__call__id__depend2"

        self.log('info', 'Create a model item B with dependencies')
        #    A <--B <--C and has no associated deconfigure task
        # Find path required to create model items
        collection_sw_item = self._get_coll_of_sw_item_url()
        ms_collection_sw_item = self._get_ref_coll_of_item_url()

        # Define attributes required
        sitem1 = os.path.join(
            collection_sw_item, self.item_type + "test2")
        sitem2 = os.path.join(
            collection_sw_item, self.depend_type + "depend1")
        sitem3 = os.path.join(
            collection_sw_item, self.depend_type2 + "depend2")
        msitem1 = os.path.join(
            ms_collection_sw_item, self.item_type + "test2a")
        msitem2 = os.path.join(
            ms_collection_sw_item, self.depend_type + "test2b")
        msitem3 = os.path.join(
            ms_collection_sw_item, self.depend_type2 + "test2c")

        self.log('info', 'Create a model item that generates multiple '
                         'ConfigTasks to create the resource and '
                         'has no deconfigure tasks (item A)')
        props = ('name=item_t2a deconfigure=false packagename=firefox '
                 'multipleconfig=true')
        self.execute_cli_create_cmd(self.ms1, sitem1, self.item_type, props)
        self.execute_cli_inherit_cmd(self.ms1, msitem1, sitem1)

        self.log('info', 'Create a model item that depends '
                         'on story-10575 item type (item B)')
        props = 'name=depend1'
        self.execute_cli_create_cmd(self.ms1, sitem2, self.depend_type, props)
        self.execute_cli_inherit_cmd(self.ms1, msitem2, sitem2)

        self.log('info', 'Create a model item that depends on '
                         'depend2-story-10575 item type (item C)')
        props = 'name=depend2'
        self.execute_cli_create_cmd(self.ms1, sitem3, self.depend_type2, props)

        self.execute_cli_inherit_cmd(self.ms1, msitem3, sitem3)

        self.log('info', 'Execute "create_plan" command')
        self.execute_cli_createplan_cmd(self.ms1)

        self.log('info', 'Execute "run_plan" command to set all the items '
                         'to Applied state')
        self.execute_cli_runplan_cmd(self.ms1)

        self.log('info', 'Wait for plan to complete')
        self.assertTrue(self.wait_for_plan_state(
            self.ms1, const.PLAN_COMPLETE))

        self.log('info', 'Check manifest contains expected dependency')
        output = self._check_puppet_manifest(self.ms1, notify_task)
        manifest_output = self._parse_puppet_manifest(output)
        self.assertTrue(self.is_text_in_list(file_task, manifest_output[7]))

        self.log('info', 'Remove the depend-story-10575 Model Items (item B')
        self.execute_cli_remove_cmd(self.ms1, msitem2)
        self.execute_cli_remove_cmd(self.ms1, sitem2)

        self.log('info', 'create plan, run and wait to complete')
        self.execute_cli_createplan_cmd(self.ms1)
        self.execute_cli_runplan_cmd(self.ms1)

        self.assertTrue(self.wait_for_plan_state(
            self.ms1, const.PLAN_COMPLETE))

        self.log('info', 'Check manifest has updated dependency')
        output = self._check_puppet_manifest(self.ms1, notify_task)
        manifest_output = self._parse_puppet_manifest(output)
        self.assertFalse(self.is_text_in_list(file_task, manifest_output[7]))

    @attr('all', 'revert', 'story10575', 'story10575_t03', 'bur_only_test')
    def test_03_n_no_associatedDeconfigTask_persistedTask_plan_fail(self):
        """
        @tms_id: litpcds_10575_tc03
        @tms_requirements_id: LITPCDS-10575
        @tms_title: Contents of puppet manifest on failed plan with model items
            that have forRemoval replacement tasks
        @tms_description: Test that on the removal of a Model Item which does
            not have an associated ConfigTask but a persisted ConfigTask exists
            a replacement "ForRemoval" ConfigTask for this model Item
            which will be phased in accordance with current task ordering
            rules and if the plan fails, the replaced config
            tasks will be reinstated and the previous manifest restored
        @tms_test_steps:
            @step: Two model items that generate multiple ConfigTasks,
            one with and one without deconfigure tasks
            @result: items created successfully
            @step: create and run plan
            @result: plan runs successfully, all items in Applied state
            @step: Remove the previously created model items, create plan
            @result: Removal ConfigTask is generated and is placed in
                the correct phase
            @step: run plan
            @result: plan fails
            @result: the successful Removal ConfigTask has been removed from
                the manifest
            @result: plugin generated ConfigTasks are still present in the plan
                as APD=False on that model item that has an associated callback
                task that failed
            @result: the core generated Removal ConfigTask is still present
                in the manifest
            @step: update model so plugin will no longer generate failing
                tasks, create plan
            @result: a Removal ConfigTask is not generated
            @step: run plan
            @result: plan runs successfully
        @tms_test_precondition: Cluster with two (or more) nodes is deployed.
            Plugin available that will generate node lock/unlock tasks.
        @tms_execution_type: Automated
        """
        # Presequite:
        self.log('info', 'Install Plugin rpms required for testing')
        self._install_rpms(self.ms1, LOCAL_PLUGINS_DIR, self.plugin_id)

        # Attributes:
        file_task = "file10575item_t{0}_task_id_item_t{1}"
        pkg_task = "{0}10575_task_id_item_t{1}"
        file_class_id = \
            "task_{0}__file__file10575item__t{1}__task__id__item__t{2}"
        pkg_class_id = \
            "task_{0}__package__{1}10575__task__id__item__t{2}"

        self.log('info', 'Create model items')
        # Create a model item that generates multiple
        # ConfigTasks and will have deconfigure tasks
        # and will also generate a callback task at removal that will fail
        collection_sw_item = self._get_coll_of_sw_item_url()
        mitem = os.path.join(collection_sw_item, self.item_type + "{0}")

        props = ('name=item_t3a deconfigure=true packagename=firefox '
                 'multipleconfig=true failplan=true')
        self.execute_cli_create_cmd(
            self.ms1, mitem.format("3a"), self.item_type, props)

        # Create a model item that generates multiple
        # ConfigTasks to create the resource and will
        # not have deconfigure tasks
        props = ('name=item_t3b deconfigure=false packagename=telnet '
                 'multipleconfig=true failplan=false')
        self.execute_cli_create_cmd(
            self.ms1, mitem.format("3b"), self.item_type, props)

        ms_collection_sw_item = self._get_ref_coll_of_item_url()
        nitem = os.path.join(ms_collection_sw_item, self.item_type + "{0}")
        self.execute_cli_inherit_cmd(
            self.ms1, nitem.format("3c"), mitem.format("3a"))
        self.execute_cli_inherit_cmd(
            self.ms1, nitem.format("3d"), mitem.format("3b"))

        node1_path = self.get_node1_path()
        n1item = os.path.join(node1_path + "/items", self.item_type + "{0}")
        self.execute_cli_inherit_cmd(
            self.ms1, n1item.format("3e"), mitem.format("3b"))

        self.log('info', 'Create and run plan, wait to complete')
        self.execute_cli_createplan_cmd(self.ms1)
        self.execute_cli_runplan_cmd(self.ms1)
        self.assertTrue(self.wait_for_plan_state(
            self.ms1, const.PLAN_COMPLETE))

        self.log('info', 'Remove the previously created Model Items')
        self.execute_cli_remove_cmd(self.ms1, nitem.format("3c"))
        self.execute_cli_remove_cmd(self.ms1, nitem.format("3d"))
        self.execute_cli_remove_cmd(self.ms1, n1item.format("3e"))
        self.execute_cli_remove_cmd(self.ms1, mitem.format("3a"))
        self.execute_cli_remove_cmd(self.ms1, mitem.format("3b"))

        try:
            self.log('info', 'Execute "create_plan" command')
            self.execute_cli_createplan_cmd(self.ms1)

            self.log('info', 'Check that the Removal ConfigTasks are generated'
                             ' and are placed in the correct phase')
            stdout, _, _ = self.execute_cli_showplan_cmd(self.ms1)
            self.assertEqual(int(6), self.cli.get_num_phases_in_plan(stdout))
            plan = self.cli.parse_plan_output(stdout)
            # ConfigTask description definition
            task_desc = \
                "Remove Item's resource from node \"{0}\" puppet"
            # check expected deconfigure config tasks are in plan
            self.assertEqual(
                task_desc.format(self.ms1), plan[1][3]['DESC'][1])
            self.assertEqual("manifest", plan[1][3]['DESC'][2])
            self.assertEqual(
                task_desc.format(self.mn1), plan[4][1]['DESC'][1])
            self.assertEqual("manifest", plan[4][1]['DESC'][2])

            self.log('info', 'run plan and wait to fail')
            self.execute_cli_runplan_cmd(self.ms1)
            self.assertTrue(self.wait_for_plan_state(
                self.ms1, const.PLAN_FAILED))

            self.log('info', 'Check model item states')
            apd_state = "ForRemoval (deployment of properties indeterminable)"
            rm_state = "ForRemoval"
            self.assertEqual(apd_state, self.execute_show_data_cmd(
                self.ms1, nitem.format("3c"), "state"))
            # Plan failed after ConfigTask for following item was executed
            # so item has been removed
            self.execute_cli_show_cmd(
                self.ms1, nitem.format("3d"), expect_positive=False)
            self.assertEqual(rm_state, self.execute_show_data_cmd(
                self.ms1, n1item.format("3e"), "state"))
            self.assertEqual(rm_state, self.execute_show_data_cmd(
                self.ms1, mitem.format("3a"), "state"))
            self.assertEqual(rm_state, self.execute_show_data_cmd(
                self.ms1, mitem.format("3b"), "state"))

            self.log('info', 'Check that the successful generated Removal '
                             'ConfigTask has been removed from the manifest')
            self._check_puppet_manifest(
                self.ms1, "item__t3b", expect_positive=False)

            self.log('info', 'Check that the plugin generated ConfigTasks '
                             'are still present in the plan as APD=False'
                             'on that model item that has an associated '
                             'callback task that failed')
            output = self._check_puppet_manifest(
                self.ms1, file_task.format("3a", "3a"))
            expected_item = dict()
            expected_item["class_id"] = file_class_id.format(
                self.ms1, "3a", "3a")
            expected_item["type"] = "file"
            manifest_item = self._parse_puppet_manifest(output)
            self._check_parse_puppet_manifest(expected_item, manifest_item)

            output = self._check_puppet_manifest(
                self.ms1, pkg_task.format("firefox", "3a"))
            expected_item["class_id"] = \
                pkg_class_id.format(self.ms1, "firefox", "3a")
            expected_item["type"] = "package"
            manifest_item = self._parse_puppet_manifest(output)
            self._check_parse_puppet_manifest(expected_item, manifest_item)

            self.log('info', 'Check that the core generated Removal ConfigTask'
                             ' is still present in the manifest')
            self._check_puppet_manifest(
                self.mn1, "item__t3b")
            output = self._check_puppet_manifest(
                self.mn1, pkg_task.format("telnet", "3b"))
            expected_item["class_id"] = \
                pkg_class_id.format(self.mn1, "telnet", "3b")
            expected_item["type"] = "package"
            manifest_item = self._parse_puppet_manifest(output)
            self._check_parse_puppet_manifest(expected_item, manifest_item)

            self.log('info', 'Update model item so plan succeeds')
            props = "failplan=false"
            self.execute_cli_update_cmd(
                self.ms1, mitem.format("3a"), props)

            self.log('info', 'create and run plan')
            self.execute_cli_createplan_cmd(self.ms1)
            self.execute_cli_createplan_cmd(self.ms1)

            self.log('info',
            'Check that a Removal ConfigTask is not generated '
            'as it was previously successfully ran')
            stdout, _, _ = self.execute_cli_showplan_cmd(self.ms1)
            self.assertEqual(
                int(6), self.cli.get_num_phases_in_plan(stdout))
            self.log('info', 'Check that the successful Core generated '
                             'deconfigure task for the ms is not added '
                             'to recreated plan as this task was previously '
                             'successful but the node task is still present')
            self.assertEqual(
                int(2), self.cli.get_num_tasks_in_phase(stdout, "1"))
            plan = self.cli.parse_plan_output(stdout)
            self.assertNotEqual(
                task_desc.format(self.ms1), plan[1][1]['DESC'][1])
            self.assertNotEqual(task_desc.format(self.ms1),
                                plan[1][2]['DESC'][1])
            self.assertEqual(
                task_desc.format(self.mn1), plan[4][1]['DESC'][1])
            self.assertEqual("manifest", plan[4][1]['DESC'][2])

            self.log('info', 'run plan and wait to succeed')
            self.execute_cli_runplan_cmd(self.ms1)
            self.assertTrue(self.wait_for_plan_state(
                self.ms1, const.PLAN_COMPLETE))

        finally:
            # If test fails while the following property is
            # true, the cleanup plan will fail
            prop = "failplan"
            val = self.execute_show_data_cmd(
                self.ms1, mitem.format("3a"), prop)
            if val == "true":
                self.execute_cli_update_cmd(self.ms1, mitem.format("3a"),
                                            "failplan=false")
                self.execute_cli_createplan_cmd(self.ms1)
                self.execute_cli_runplan_cmd(self.ms1)
                self.assertTrue(self.wait_for_plan_state(
                      self.ms1, const.PLAN_COMPLETE))

            else:
                # Cleanup
                # Remove model that required configuration update
                # to prevent plan failure
                self.execute_cli_remove_cmd(self.ms1, nitem.format("3c"))
                self.execute_cli_remove_cmd(self.ms1, mitem.format("3a"))

                # Execute "create_plan" command
                self.execute_cli_createplan_cmd(self.ms1)

                # Execute "run_plan" command
                self.execute_cli_runplan_cmd(self.ms1)

                # Wait for the plan to be successful
                # Wait for plan to complete
                self.assertTrue(self.wait_for_plan_state(
                    self.ms1, const.PLAN_COMPLETE))

    @attr('all', 'revert', 'story10575', 'story10575_t04', 'bur_only_test')
    def test_04_n_no_associatedDeconfigTask_persistedTasks_stop_plan(self):
        """
        @tms_id: litpcds_10575_tc04
        @tms_requirements_id: LITPCDS-10575
        @tms_title: Puppet manifest contents if plan execution stopped
            before ConfigTasks executed
        @tms_description: Test that on a subsequent plan after a plan has been
            run to remove a Model Item which does not have an associated
            ConfigTask, if the plan is stopped before ConifgTasks have been
            executed the resources in the manifests will not have been removed
        @tms_test_steps:
            @step: Create model item that will generate configtasks and will
                 have deconfigure tasks and a failing callback task on removal.
                 Create model items that will generate configtasks and will
                 not have deconfigure tasks.
            @result: items created.
            @step: Create and run plan
            @result: Plan runs successfully and all items in Applied state.
            @step: Remove the previously created model items, create plan.
            @result: Removal ConfigTasks are generated and are placed
                 in the correct phase
            @step: run plan and stop at first phase
            @result: plan stopped
            @result: the successful core generated deconifgure ConfigTask
                 and plugin generated deconfigure ConfigTasks
                 has been removed from the manifest on the MS
            @result: plugin generated ConfigTasks are still present in the
                 manifest on node1 as the plan was stopped before this task
                 was executed
            @step: create plan
            @result: the previously successful core generated Removal
                 ConfigTask is not present in the plan
            @result: the previously not executed deconfigure config task
                 is in plan
            @step: run plan
            @result: successful Removal ConfigTask has been removed from the
                 manifest on the node and MS
        @tms_test_precondition: Cluster with two (or more) nodes is deployed.
            Plugin available that will generate node lock/unlock tasks.
        @tms_execution_type: Automated
        """
        # Presequite:
        self.log('info', 'Install Plugin rpms required for testing')
        self._install_rpms(self.ms1, LOCAL_PLUGINS_DIR, self.plugin_id)

        self.log('info', 'Create model items')
        # 1a.Create a model item that generate multiple ConfigTasks to
        #   create the resource and will have deconfigure tasks
        #   and will also generate a callback task at removal that will fail
        collection_sw_item = self._get_coll_of_sw_item_url()
        mitem = os.path.join(collection_sw_item, self.item_type + "{0}")

        props = ('name=item_t4a deconfigure=true packagename=firefox '
                 'multipleconfig=true')
        self.execute_cli_create_cmd(
            self.ms1, mitem.format("4a"), self.item_type, props)

        # 1b.Create a model item that generate multiple ConfigTasks to
        #   create the resource and will not have deconfigure tasks
        props = ('name=item_t4b deconfigure=false packagename=telnet '
                 'multipleconfig=true failplan=false')
        self.execute_cli_create_cmd(
            self.ms1, mitem.format("4b"), self.item_type, props)

        ms_collection_sw_item = self._get_ref_coll_of_item_url()
        nitem = os.path.join(ms_collection_sw_item, self.item_type + "{0}")
        self.execute_cli_inherit_cmd(
            self.ms1, nitem.format("4c"), mitem.format("4a"))
        self.execute_cli_inherit_cmd(
            self.ms1, nitem.format("4d"), mitem.format("4b"))

        node1_path = self.get_node1_path()
        n1item = os.path.join(node1_path + "/items", self.item_type + "{0}")
        self.execute_cli_inherit_cmd(
            self.ms1, n1item.format("4e"), mitem.format("4b"))

        self.log('info', 'Create plan, run and wait for successful completion')
        self.execute_cli_createplan_cmd(self.ms1)
        self.execute_cli_runplan_cmd(self.ms1)
        self.assertTrue(self.wait_for_plan_state(
            self.ms1, const.PLAN_COMPLETE))

        self.log('info', 'Remove the previously created Model Items')
        self.execute_cli_remove_cmd(self.ms1, nitem.format("4c"))
        self.execute_cli_remove_cmd(self.ms1, nitem.format("4d"))
        self.execute_cli_remove_cmd(self.ms1, n1item.format("4e"))
        self.execute_cli_remove_cmd(self.ms1, mitem.format("4a"))
        self.execute_cli_remove_cmd(self.ms1, mitem.format("4b"))

        self.log('info', 'Create plan, check Removal Configtasks generated '
                         'and placed in correct phase')
        self.execute_cli_createplan_cmd(self.ms1)
        stdout, _, _ = self.execute_cli_showplan_cmd(self.ms1)
        self.assertEqual(int(5), self.cli.get_num_phases_in_plan(stdout))
        plan = self.cli.parse_plan_output(stdout)
        # Core generated ConfigTask description definition
        task_desc = "Remove Item's resource from node \"{0}\" puppet"
        # Check expected deconfigure config tasks are in plan
        self.assertEqual(
            task_desc.format(self.ms1), plan[1][3]['DESC'][1])
        self.assertEqual(
            "manifest", plan[1][3]['DESC'][2])
        self.assertEqual(
            task_desc.format(self.mn1), plan[3][1]['DESC'][1])
        self.assertEqual(
            "manifest", plan[3][1]['DESC'][2])

        self.log('info', 'Run plan and stop on 1st phase, wait till stopped')
        self.execute_cli_runplan_cmd(self.ms1)
        config_desc = "ConfigTask deconfigure item_t4a on node {0}"
        self.assertTrue(self.wait_for_task_state(
            self.ms1, config_desc.format(self.ms1),
            const.PLAN_TASKS_RUNNING, ignore_variables=False))

        self.execute_cli_stopplan_cmd(self.ms1)
        self.assertTrue(self.wait_for_plan_state(
            self.ms1, const.PLAN_STOPPED))

        self.log('info', 'Check the successful core generated deconifgure'
                         ' ConfigTask and plugin generated deconfigure '
                         'ConfigTasks removed from the manifest on the MS')
        self._check_puppet_manifest(
            self.ms1, "[a-z]10575", expect_positive=False)

        self.log('info', 'Check plugin generated ConfigTasks still present'
                         'in manifest on node1 as plan was stopped '
                         'before it was executed')
        self._check_puppet_manifest(
            self.mn1, "10575")

        self.log('info', 'create plan')
        self.execute_cli_createplan_cmd(self.ms1)

        self.log('info', 'Check that the previoulsy successful core generated '
                         'Removal ConfigTask is not present in the plan')
        stdout, _, _ = self.execute_cli_showplan_cmd(self.ms1)
        plan = self.cli.parse_plan_output(stdout)
        self.assertEqual(int(4), self.cli.get_num_phases_in_plan(stdout))
        self.log('info', 'not executed deconfigure config task is still'
                         ' in plan')
        self.assertEqual(
            task_desc.format(self.mn1), plan[2][1]['DESC'][1])
        self.assertEqual(
            "manifest", plan[2][1]['DESC'][2])

        self.log('info', 'run plan and wait till successfull')
        self.execute_cli_runplan_cmd(self.ms1)

        self.assertTrue(self.wait_for_plan_state(
            self.ms1, const.PLAN_COMPLETE))

        self.log('info', 'the successful Removal ConfigTask has been removed '
                         'from the manifest on the node and MS')
        self._check_puppet_manifest(
           self.mn1, "10575", expect_positive=False)
        self._check_puppet_manifest(
           self.ms1, "[a-z]10575", expect_positive=False)

    @attr('all', 'revert', 'story10575', 'story10575_t05', 'bur_only_test')
    def test_05_n_no_associatedConfigTask_persistedTasks_kill_plan(self):
        """
        @tms_id: litpcds_10575_tc05
        @tms_requirements_id: LITPCDS-10575
        @tms_title: Puppet manifest contents if plan execution stopped
                    by restarting litpd service
        @tms_description: If litpd service is restarted plan stops and all
            tasks not finished successfully are recreated in a subsequent plan
        @tms_test_steps:
            @step: Create model items that don't create any ConfigTasks, model
                items that will create ConfigTasks on ms and nodes, none will
                have deconfigure tasks
            @result: model items created
            @step: create and run plan
            @result: plan runs successfully
            @step: remove the previously created model items and create plan
            @result: Removal ConfigTasks are generated and are placed
                in the correct phase
            @step: run plan and immediately restart litpd service
            @result: plan stopped
            @step: create plan
            @result: plan created successfully
            @result: expected deconfigure config tasks are in plan
            @step: run plan and restart kill litp service when specific phase
                reached
            @result: plan stopped
            @result: not executed Core generated ConfigTask is still present
                in the manifest
            @step: create plan
            @result: the not executed core generated Removal ConfigTask
                is still present in the plan
            @step: run plan
            @result: plan runs successfully
            @result: all tasks created by this test are removed from manifests
        @tms_test_precondition: Cluster with two (or more) nodes is deployed.
            Plugin available that will generate node lock/unlock tasks.
        @tms_execution_type: Automated
        """
        file_task = "file10575item_t5b_task_id_item_t5b"

        self.log('info',
        '1. Install Plugin rpms required for testing')
        self._install_rpms(self.ms1, LOCAL_PLUGINS_DIR, self.plugin_id)

        self.log('info',
        '2. Create model items')
        collection_sw_item = self._get_coll_of_sw_item_url()
        ms_collection_sw_item = self._get_ref_coll_of_item_url()
        node1_path = self.get_node1_path()

        self.log('info',
        '3. Create two source items')
        mitem = os.path.join(collection_sw_item, self.item_type + "{0}")
        props = ('name=item_t5a '
                 'deconfigure=false '
                 'packagename=firefox '
                 'multipleconfig=true')
        self.execute_cli_create_cmd(self.ms1,
                                    mitem.format("5a"),
                                    self.item_type,
                                    props)
        props = ('name=item_t5b '
                 'deconfigure=false '
                 'packagename=telnet '
                 'multipleconfig=true')
        self.execute_cli_create_cmd(self.ms1,
                                    mitem.format("5b"),
                                    self.item_type,
                                    props)

        self.log('info',
        '4. Inherit items from the source item just created')
        # None of the inherited items will have "deconfigure" task
        nitem = os.path.join(ms_collection_sw_item, self.item_type + "{0}")
        self.execute_cli_inherit_cmd(self.ms1,
                                     nitem.format("5c"),
                                     mitem.format("5a"))

        self.execute_cli_inherit_cmd(self.ms1,
                                     nitem.format("5d"),
                                     mitem.format("5b"))

        n1item = os.path.join(node1_path + "/items", self.item_type + "{0}")
        self.execute_cli_inherit_cmd(self.ms1,
                                     n1item.format("5e"),
                                     mitem.format("5b"))

        self.log('info',
        '5. Deploy the item just created')
        self.execute_cli_createplan_cmd(self.ms1)
        self.execute_cli_runplan_cmd(self.ms1)
        self.assertTrue(self.wait_for_plan_state(self.ms1,
                                                 const.PLAN_COMPLETE))

        self.log('info',
        '6. remove previously created model items')
        self.execute_cli_remove_cmd(self.ms1, nitem.format("5c"))
        self.execute_cli_remove_cmd(self.ms1, nitem.format("5d"))
        self.execute_cli_remove_cmd(self.ms1, n1item.format("5e"))
        self.execute_cli_remove_cmd(self.ms1, mitem.format("5a"))
        self.execute_cli_remove_cmd(self.ms1, mitem.format("5b"))

        self.log('info',
        '7. Execute "create_plan" command')
        self.execute_cli_createplan_cmd(self.ms1)

        self.log('info',
        '8. Create plan and check that the Removal ConfigTasks are generated '
            'and are placed in the correct phase')
        stdout, _, _ = self.execute_cli_showplan_cmd(self.ms1)
        self.assertEqual(int(5), self.cli.get_num_phases_in_plan(stdout))
        plan = self.cli.parse_plan_output(stdout)
        task_desc = "Remove Item's resource from node \"{0}\" puppet"
        self.assertEqual(task_desc.format(self.ms1), plan[1][1]['DESC'][1])
        self.assertEqual("manifest", plan[1][1]['DESC'][2])
        self.assertEqual(task_desc.format(self.ms1), plan[1][2]['DESC'][1])
        self.assertEqual("manifest", plan[1][2]['DESC'][2])
        self.assertEqual(task_desc.format(self.mn1), plan[3][1]['DESC'][1])
        self.assertEqual("manifest", plan[3][1]['DESC'][2])

        self.log('info',
        '9. Execute "run_plan" command followed immediately by litpd service '
           'restart')
        self.execute_cli_runplan_cmd(self.ms1)
        cmd = '/sbin/service litpd restart &'
        self.run_command(self.ms1, cmd, su_root=True, default_asserts=True)

        self.log('info',
        '10. Wait for the notify task to appear in ms1.pp manifest file')
        manifest_file = os.path.join(const.PUPPET_MANIFESTS_DIR, 'ms1.pp')
        class_id = (
            'class task_ms1__notify___2fms_2fitems_2fstory_2d10575a5c')
        notify_class_found = self._wait_for_text_in_manifest(manifest_file,
                                                             class_id,
                                                             timeout=60)
        self.assertTrue(notify_class_found)

        self.log('info',
        '11. Wait for the plan to stop')
        self.assertTrue(self._wait_for_litpd_running(timeout=180))
        self.assertTrue(self.wait_for_plan_state(self.ms1, const.PLAN_STOPPED))

        self.log('info',
        '12. Create plan and check that expected deconfigure config tasks are '
            'in the plan')
        self.execute_cli_createplan_cmd(self.ms1)
        self.assertEqual(task_desc.format(self.ms1), plan[1][1]['DESC'][1])
        self.assertEqual("manifest", plan[1][1]['DESC'][2])
        self.assertEqual(task_desc.format(self.ms1), plan[1][2]['DESC'][1])
        self.assertEqual("manifest", plan[1][2]['DESC'][2])
        self.assertEqual(task_desc.format(self.mn1), plan[3][1]['DESC'][1])
        self.assertEqual("manifest", plan[3][1]['DESC'][2])

        self.log('info',
        '13. Run the plan and wait until "Lock VCS on node" is running, '
            'restart litpd service and wait for the plan to stop')
        self.execute_cli_runplan_cmd(self.ms1)

        lock_task_desc = "Lock VCS on node \"{0}\"".format(self.mn1)
        self.assertTrue(self.wait_for_task_state(self.ms1,
                                                 lock_task_desc,
                                                 const.PLAN_TASKS_RUNNING,
                                                 ignore_variables=False,
                                                 seconds_increment=1))
        self.restart_litpd_service(self.ms1)
        self.assertTrue(self.wait_for_plan_state(self.ms1, const.PLAN_STOPPED))

        self.log('info',
        '14. Check that the not executed Core generated ConfigTask is still '
            'present in the manifest')
        self._check_puppet_manifest(self.mn1, file_task)

        self.log('info',
        '15. Create the plan and Check that the not executed core generate '
             'Removal ConfigTask is still present')
        self.execute_cli_createplan_cmd(self.ms1)

        self.log('info',
        '16. Check that the not executed core generate Removal ConfigTask is '
            'still present in the plan')
        self.assertEqual(task_desc.format(self.mn1), plan[3][1]['DESC'][1])
        self.assertEqual("manifest", plan[3][1]['DESC'][2])

        self.log('info',
        '17. Run plan and wait until the notify class for node1 item appears '
            'in the manifest file')
        self.execute_cli_runplan_cmd(self.ms1)

        manifest_file = os.path.join(const.PUPPET_MANIFESTS_DIR, 'node1.pp')
        class_id = (
            'class task_node1__notify___2fdeployments_2fd1_2fclusters_'
            '2fc1_2fnodes_2fn1_2fitems_2fstory_2d10575a5e')
        notify_class_found = self._wait_for_text_in_manifest(manifest_file,
                                                             class_id,
                                                             timeout=60)
        self.assertTrue(notify_class_found)

        self.log('info',
        '18. Wait until the plan completes and check the new resources '
            'have been removed from the manifests')

        self.assertTrue(self.wait_for_plan_state(self.ms1,
                                                 const.PLAN_COMPLETE))
        self._check_puppet_manifest(self.ms1, "[a-z]10575",
                                    expect_positive=False)
        self._check_puppet_manifest(self.mn1, "10575", expect_positive=False)

    @attr('all', 'revert', 'story10575', 'story10575_tc06', 'bur_only_test')
    def test_06_n_fail_deconfigure_task(self):
        """
        @tms_id: litpcds_10575_tc06
        @tms_requirements_id: LITPCDS-10575
        @tms_title: Changes to puppet manifest by a deconfigure config task are
            reverted if the plan fails
        @tms_description: Verify that when Core generated "Deconfigure Task"
            fails, the puppet manifest will be reverted to the last known
            good configuration.
            Also verify that puppet configuration parameters can be updated
            by editing the "litpd.conf" file and restarting the "litpd" service
        @tms_test_steps:
            @step: Deploy new model items of type "story-10575a"
            @result: Items deployed successfully
            @result: puppet manifest updated accordingly
            @step: Update "puppet_poll_frequency" and "puppet_phase_timeout" in
                   /etc/litpd.conf file.
            @result: "litpd.conf" file updated
            @step: Restart "litpd" service to load new configuration
            @result: "litpd" service restarted successfully
            @step: Attempt to remove the previously created model items
            @result: Plan fails as expected
            @result: Plan phase timed out according the "puppet_phase_timeout"
                     value
            @result: Puppet agent was polled according to
                     "puppet_poll_frequency" value
            @result: Last known good puppet manifest configuration was
                     reinstated
        @tms_test_precondition: Plugin that will cause a deconfigure task to
                                fail.
        @tms_execution_type: Automated
        """
        ms_manifest_file = '{0}.pp'.format(self.ms1)

        self.log('info',
        '1. Install plugin rpms required for testing')
        self._install_rpms(self.ms1, LOCAL_PLUGINS_DIR, self.plugin_id)

        self.log('info',
        '2. Create and deploy model items')
        coll_sw_item_url = self._get_coll_of_sw_item_url()
        ms_coll_sw_item_url = self._get_ref_coll_of_item_url()

        # In order deploy item of type "story-10575a" we need to create a
        # source item under /software and then inherit it (on the MS in
        # this case).
        # In the following section we define 2 source/child item pairs
        # with property "deconfigure" set to "true" and 2 source/child item
        # pairs with "deconfigure" set to "false"

        # Item with property "deconfigure=true"
        source_1 = {}
        source_1['id'] = 'story10575-tc06-sa'
        source_1['url'] = os.path.join(coll_sw_item_url, source_1['id'])
        source_1['type'] = 'story-10575a'
        source_1['props'] = ('name=item_t6a '
                             'deconfigure=true '
                             'packagename=firefox '
                             'multipleconfig=true '
                             'failphase=true')
        child_1 = {}
        child_1['id'] = 'story10575-tc06-ca'
        child_1['url'] = os.path.join(ms_coll_sw_item_url, child_1['id'])
        child_1['type'] = 'story-10575a'
        child_1['class_file_id'] = (
            'class task_{0}__file__file10575item__t6a__task__id__item__t6a'
            .format(self.ms1))
        child_1['class_pkg_id'] = (
            'class task_{0}__package__firefox10575__task__id__item__t6a'
            .format(self.ms1))

        # Item with property "deconfigure=false"
        source_2 = {}
        source_2['id'] = 'story10575-tc06-sb'
        source_2['url'] = os.path.join(coll_sw_item_url, source_2['id'])
        source_2['type'] = 'story-10575a'
        source_2['props'] = ('name=item_t6b '
                             'deconfigure=false '
                             'multipleconfig=true '
                             'packagename=telnet')

        child_2 = {}
        child_2['id'] = 'story10575-tc06-cb'
        child_2['url'] = os.path.join(ms_coll_sw_item_url, child_2['id'])
        child_2['type'] = 'story-10575a'
        child_2['class_file_id'] = (
            'class task_{0}__file__file10575item__t6b__task__id__item__t6b'
            .format(self.ms1))
        child_2['class_pkg_id'] = (
            'class task_{0}__package__telnet10575__task__id__item__t6b'
            .format(self.ms1))

        self.execute_cli_create_cmd(self.ms1,
                                    source_1['url'],
                                    source_1['type'],
                                    source_1['props'])

        self.execute_cli_inherit_cmd(self.ms1,
                                     child_1['url'],
                                     source_1['url'])

        self.execute_cli_create_cmd(self.ms1,
                                    source_2['url'],
                                    source_2['type'],
                                    source_2['props'])

        self.execute_cli_inherit_cmd(self.ms1,
                                     child_2['url'],
                                     source_2['url'])

        self.run_and_check_plan(self.ms1,
                                const.PLAN_COMPLETE,
                                plan_timeout_mins=10)

        self.log('info',
        '3. Check that expected classes are defined in MS puppet manifest')
        manifest_before = []
        for item in [child_1, child_2]:
            for resource in [item['class_file_id'], item['class_pkg_id']]:
                class_data = self._get_puppet_manifest_data(ms_manifest_file,
                                                            resource)
                self.assertNotEqual([], class_data,
                    'Puppet class "{0}" not found in manifest "{1}"'
                    .format(resource, ms_manifest_file))
                manifest_before.append(class_data)

        try:
            self.log('info',
            '4. Update value of "puppet_phase_timeout" and '
               '"puppet_poll_frequency" on "litpd.conf" file')
            # The "puppet_phase_timeout" parameter defines the Timeout value,
            # in seconds, for puppet phase
            # The "puppet_poll_frequency" parameter defines the puppet poll
            # frequency in seconds, to check puppet agent is still alive
            #
            # "puppet_phase_timeout" value MUST be greater than
            # "puppet_poll_frequency" for this test to be valid
            self.backup_file(self.ms1, const.LITPD_CONF_FILE)
            new_litpd_conf = {}
            new_litpd_conf['puppet_poll_frequency'] = 90
            new_litpd_conf['puppet_phase_timeout'] = \
                                new_litpd_conf['puppet_poll_frequency'] * 2
            self._update_litpd_conf_file(new_litpd_conf)

            self.log('info',
            '5. Attempt to remove items previously created')
            # The plan is expected to fail because of the property
            # "failphase=true" set on item child_1
            self.get_props_from_url(self.ms1, child_1['url'], 'failphase')
            self.get_props_from_url(self.ms1, child_2['url'], 'failphase')

            self.execute_cli_remove_cmd(self.ms1, child_1['url'])
            self.execute_cli_remove_cmd(self.ms1, child_2['url'])
            self.execute_cli_remove_cmd(self.ms1, source_1['url'])
            self.execute_cli_remove_cmd(self.ms1, source_2['url'])

            self.execute_cli_createplan_cmd(self.ms1)
            cursor_pos = self.get_file_len(self.ms1, const.GEN_SYSTEM_LOG_PATH)

            # Ensure that puppet is not busy while
            # the plan is executing
            self.ensure_puppet_is_not_running_or_about_to_run()

            self.execute_cli_runplan_cmd(self.ms1)

            self.log('info',
            '6. Assert that phase timed out within the expected time')
            mco_cycle = 10
            plan_poll_intervall = 3
            phase_cleanup_time = 20
            expected_phase_timeout = (new_litpd_conf['puppet_phase_timeout'] +
                                      phase_cleanup_time)

            self.assertTrue(self.wait_for_task_state(
                                        self.ms1,
                                        'ConfigTask deconfigure',
                                        const.PLAN_TASKS_RUNNING,
                                        seconds_increment=plan_poll_intervall,
                                        timeout_mins=1))
            start_phase_time = int(time.time())

            self.execute_cli_showplan_cmd(self.ms1)

            self.assertTrue(self.wait_for_task_state(
                                        self.ms1,
                                        'ConfigTask deconfigure',
                                        const.PLAN_TASKS_FAILED,
                                        seconds_increment=plan_poll_intervall))
            timeout_time = int(time.time())

            # We need to allow for plan cleanup to complete before moving on
            self.wait_for_plan_state(self.ms1,
                                     const.PLAN_FAILED,
                                     timeout_mins=1)

            actual_phase_timeout = timeout_time - start_phase_time
            self.log('info',
            'Actual phase timeout is "{0}s", expected phase timeout is "{1}"s'
            .format(actual_phase_timeout, expected_phase_timeout))
            self.assertTrue(expected_phase_timeout > actual_phase_timeout)

            self.log('info',
            '7. Assert that puppet polls happened according to '
               '"puppet_poll_frequency" value set on "litpd.conf" file')
            puppet_poll_msg = (r"DEBUG: executing command: \['mco', 'rpc',"
                                " '--json', '--timeout=10', '-I', u'ms1', "
                                "'puppet', 'status'")

            puppet_poll_ts1 = self._get_msg_timestamp(self.ms1,
                                                      puppet_poll_msg,
                                                      cursor_pos,
                                                      index=1,
                                                      timeout=10)

            puppet_poll_ts2 = self._get_msg_timestamp(self.ms1,
                                                      puppet_poll_msg,
                                                      cursor_pos,
                                                      index=2,
                                                      timeout=10)

            actual_poll_intervall = self._diffdates(puppet_poll_ts2,
                                                    puppet_poll_ts1)
            expected_poll_intervall = \
                    new_litpd_conf['puppet_poll_frequency'] + mco_cycle
            self.assertTrue(expected_poll_intervall >= actual_poll_intervall)

            self.log('info',
            '8. Check that changes to puppet MS manifest that were made while '
               'the plan was running have been reverted')
            manifest_after = []
            for item in [child_1, child_2]:
                for resource in [item['class_file_id'], item['class_pkg_id']]:
                    class_data = self._get_puppet_manifest_data(
                                                        ms_manifest_file,
                                                        resource)
                    self.assertNotEqual([], class_data,
                        'Puppet class "{0}" not found in manifest "{1}"'
                        .format(resource, ms_manifest_file))
                    manifest_after.append(class_data)

            for before, after in zip(manifest_before, manifest_after):
                self.assertEqual(before, after,
                'MANIFEST CONFIGURATION MISMATCH\nBefore:\n{0}\nAfter\n{1}'
                .format('\n'.join(before), '\n'.join(after)))
        finally:
            self.log('info',
            'FINALLY: Restore initial version of "litpd.conf" file')
            self.restore_backup_files(self.ms1, const.LITPD_CONF_FILE)
            self.stop_service(self.ms1, 'celery.service')
            self.start_service(self.ms1, 'celery.service')

            self.log('info',
            'FINALLY: Ensure that "failphase" property is set to "false"')
            failphase = self.get_props_from_url(self.ms1,
                                                source_1['url'],
                                                filter_prop="failphase")
            if failphase == 'true':
                self.execute_cli_update_cmd(self.ms1,
                                            source_1['url'],
                                            "failphase=false")

            item_to_remove = False
            for item in [child_1, child_2, source_1, source_2]:
                if self.find(self.ms1,
                             item['url'],
                             item['type'],
                             assert_not_empty=False):
                    item_to_remove = True
                    self.execute_cli_remove_cmd(self.ms1, item['url'])
            if item_to_remove:
                self.run_and_check_plan(self.ms1,
                                        const.PLAN_COMPLETE,
                                        plan_timeout_mins=10)
