"""
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     August 2016
@author:    Roman Jarzebiak - Maurizio Senno
@summary:   Integration tests for TORF-124377
"""

import os
import re
import time
import datetime
from litp_generic_test import GenericTest, attr
from redhat_cmd_utils import RHCmdUtils
import test_constants as const
from litp_generic_utils import GenericUtils


class Story124377(GenericTest):
    """
    As A LITP User I want to modify the script that takes copies
    of the applied LITP model and generated puppet manifests,
    so that it takes account of the new DB
    """

    def setUp(self):
        """ Runs before every single test """
        super(Story124377, self).setUp()
        self.backup_dir = "/tmp/litp_archives/"
        self.backup_dir_2 = "/tmp/litp_archives_2/"
        self.corrupt_tar = "/tmp/corrupted_backup.tar.gz"
        self.logging_url = "/litp/logging"
        self.rhcmd = RHCmdUtils()
        self.utils = GenericUtils()
        self.ms1 = self.get_management_node_filename()
        self.managed_nodes = self.get_managed_node_filenames()
        self.export_before = "/tmp/export_before.xml"
        self.export_after = "/tmp/export_after.xml"
        self.puppet_manifests_dir = const.PUPPET_MANIFESTS_DIR[1:]
        self.expected_files = [
            self.puppet_manifests_dir + '{0}.pp'.format(self.ms1),
            'litp_db.dump'
        ]
        for node in self.managed_nodes:
            self.expected_files.append(
                self.puppet_manifests_dir + '{0}.pp'.format(node))

    def tearDown(self):
        """ Runs after every single test """
        self.remove_item(self.ms1, self.backup_dir, su_root=True)
        self.remove_item(self.ms1, self.backup_dir_2, su_root=True)
        self.remove_item(self.ms1, self.corrupt_tar, su_root=True)

        # Ensure /litp/logging is turned off after test run
        cmd = self.cli.get_update_cmd(self.logging_url, "force_debug=false")
        self.run_command(self.ms1, cmd)

        super(Story124377, self).tearDown()

    @staticmethod
    def _get_archive_timestamp(filename):
        """
        Return a date object from archive timestamp
        """
        filename = os.path.basename(filename)
        pattern = re.compile("litp_backup_(\\d{14})\\.tar\\.gz")
        res = pattern.search(filename)
        return datetime.datetime.strptime(res.group(1), "%Y%m%d%H%M%S")

    def _validate_archive_contents(self, archive_file):
        """
        Description:
            Checks if archive file contains all the expected files and if they
            are not empty (size not 0)
        Args:
            archive_file (str): The archive file to inspect
        """
        expected_files = self.expected_files[:]
        cmd = self.rhcmd.get_tar_cmd('-tvf', archive_file)
        out = self.run_command(self.ms1, cmd, default_asserts=True)[0]
        for line in out:
            file_name = (re.split(r'\s+', line))[5]
            file_size = (re.split(r'\s+', line))[2]
            if 'META-INF' in file_name or 'site.pp' in file_name:
                continue
            self.assertNotEqual('0', file_size)
            if file_name in expected_files:
                expected_files.remove(file_name)
            else:
                self.fail('Unexpected file "{0}" was found in the backup dir'.
                          format(file_name))
        self.assertEqual([], expected_files,
            'Missing backup files:\n{0}'.format('\n'.join(expected_files)))

    def _run_backup_script(self, target_dir, run_as_root=True):
        """
        run the backup script with given target directory argument and return
        output of command
        """
        cmd = "{0} {1}".format(const.LITP_BACKUP_SCRIPT, target_dir)
        return self.run_command(self.ms1, cmd, su_root=run_as_root)

    def _check_plan_not_running(self):
        """
        Check that no plan is running.
        """
        plans = self.find(self.ms1, '/plans', 'plan', assert_not_empty=False)
        if plans:
            plan_state = self.get_current_plan_state(self.ms1)
            self.assertEqual(plan_state, const.PLAN_COMPLETE,
                'Found plan in an unexpected state "{0}"'.format(plan_state))

    def _toggle_dummy_firewall_rule(self, item_id):
        """
        Description:
            Create or remove a dummy firewall rule so that changes are made in
            model and a backup archive can be created.
        Args:
            item_id (str): The firewall item id
        """
        ms_firewalls = self.find(self.ms1,
                                 '/ms',
                                 'collection-of-firewall-rule')[0]
        ms_fw_url = '{0}/{1}'.format(ms_firewalls, item_id)
        found = self.find(self.ms1,
                          ms_fw_url,
                          'firewall-rule',
                          assert_not_empty=False)

        if found:
            self.execute_cli_remove_cmd(self.ms1, ms_fw_url)
        else:
            self.execute_cli_create_cmd(self.ms1,
                                        ms_fw_url,
                                        'firewall-rule',
                                        props='name="550 story124377"')

    def _run_backup_and_assert_success(self, backup_dir):
        """
        Description:
            Run backup script and assert success:
            - check that a new archive file is created in specified directory
            - validate contents of created archive
        Args:
            backup_dir (str): Valid backup directory
        Return:
            str, The fully qualified name of the archive file just created

        """
        out, err, rc = self._run_backup_script(backup_dir)
        self.assertEqual(0, rc,
            'Backup script exited with unexpected RC "{0}"'.format(rc))
        self.assertEqual([], err,
            'Backup script posted the following error:\n {0}'.
             format('\n'.join(err)))
        archive_file_uri = out[0].split('Creating')[-1].strip()
        archive_file = os.path.basename(archive_file_uri)

        bkp_dir_contents = self.list_dir_contents(self.ms1, backup_dir)

        self.assertTrue(
            self.is_text_in_list(archive_file, bkp_dir_contents),
            'New archive should have been created in {0}'
            ' directory'.format(backup_dir))
        self._validate_archive_contents(archive_file_uri)

        return archive_file

    def _run_restore_script(self, backup):
        """
        Description:
            Runs the restore script to restore backup
                    archive specified by backup argument.
        Args:
            backup (str): LITP backup tarball.
        Returns:
            str, str, int: stdout, stderr and return
                code from running the restore script.
        """
        cmd = "{0} {1}".format(const.LITP_RESTORE_SCRIPT, backup)
        return self.run_command(self.ms1, cmd, su_root=True)

    def _get_ms_current_epoch_time(self):
        """
        Get MS current epoch time
        """
        cmd = '/bin/date +%s'
        timestamp = self.run_command(self.ms1, cmd, default_asserts=True)[0][0]
        return datetime.datetime.utcfromtimestamp(float(timestamp))

    @attr('all', 'revert', 'story124377', 'story124377_tc01', 'bur_only_test')
    def test_01_np_backup_script_generates_archive(self):
        """
        @tms_id: torf_124377_tc01
        @tms_requirements_id: TORF-124377
        @tms_title:
            Verify backup management under several conditions
        @tms_description:
            Verify that a backup is created when:
            The backup script is correctly invoked and no plan is running
            and either changes were made to the model since last backup
            was created or the archives directory is empty.
            Verify that a backup is not created when:
            The backup script is correctly invoked, no plan is running
            and no changes were made to the model since previous
            backup was created.
        @tms_test_steps:
            @step: Assert that file
                /opt/ericsson/nms/litp/bin/litp_state_backup.sh exists
            @result: script is in place
            @step: Assert that no plan is running
            @result: no plan running
            @step: Remove any existing plan
            @result: no plans present
            @step: Save current model by exporting root to
                /tmp/initial_root.xml file
            @result: Model exported successfully
            @step: Assert that no plan is running
            @result: no plans running
            @step: Run the litp_state_backup.sh /tmp/litp_archives script
            @result: The litp_state_backup.sh completed successfully
            @result: An archive file with a name that includes backup
                creation timestamp exists under /tmp/litp_archives folder
            @result: The archive file contains puppet manifest data
                (ms and nodes)
            @result: The archive file contains a dump of the LITP
                PostgresSQL data
            @step: Save current model by exporting root to
                /tmp/current_root.xml file
            @result: Model exported successfully
            @step: Assert that the two xml models are equal
            @result: they are
            @step: Assert that no plan is running
            @result: no plan is running
            @step: Run the litp_state_backup.sh /tmp/litp_archives script
            @result: The script exits with Return Code 0
            @result: The /tmp/litp_archives folder is still empty
            @step: Create a new item in deployment model
            @result: Item is created
            @step: Assert that no plan is running
            @result: no plan is running
            @step: Run the litp_state_backup.sh /tmp/litp_archives script
            @result: The litp_state_backup.sh completed successfully
            @result: An archive file with a name that includes backup
                creation timestamp exists under /tmp/litp_archives folder
            @result: The archive file contains puppet manifest data
                (ms and nodes)
            @result: The archive file contains a dump of the LITP
                PostgresSQL data
        @tms_test_precondition: An MS system with LITP DB solution running,
            /tmp/litp_archives exists and is empty
        @tms_execution_type: Automated
        """
        self.log('info',
        '1. Check that the backup script exists.')
        self.assertTrue(self.remote_path_exists(self.ms1,
                                                const.LITP_BACKUP_SCRIPT,
                                                su_root=True))

        self.log('info',
        '2. Export root of current model to xml')
        self.execute_cli_export_cmd(self.ms1, '/', self.export_before)

        self.log('info',
        '3. Check that no plan is running, remove any existing plan')
        self._check_plan_not_running()

        self.log('info',
        '4. Run backup script and assert that backup was created correctly')
        self.create_dir_on_node(self.ms1, self.backup_dir, su_root=True)
        expected_files = list()
        start_time = self._get_ms_current_epoch_time()
        archive = self._run_backup_and_assert_success(self.backup_dir)
        end_time = self._get_ms_current_epoch_time()
        expected_files.append(archive)
        archive_timestamp = self._get_archive_timestamp(archive)

        self.assertTrue(
            ((start_time <= archive_timestamp) and
             (end_time >= archive_timestamp),
            'Backup time embedded in archive file name is incorrect'))

        self.log('info',
        '5. Assert that no changes were made to the model since last backup')
        self.execute_cli_export_cmd(self.ms1, '/', self.export_after)
        cmd = '/usr/bin/diff {0} {1}'.format(self.export_before,
                                             self.export_after)
        stdout = self.run_command(self.ms1, cmd)[0]
        self.assertEqual([], stdout,
                        'Found changes to the model, test cannot continue')

        self.log('info',
        '6. Check that no plan is running')
        self._check_plan_not_running()

        self.log('info',
        '7. Run backup script and check no new archive files created')
        _, err, rc = self._run_backup_script(self.backup_dir)
        self.assertEqual([], err)
        self.assertEqual(0, rc)
        dir_contents = self.list_dir_contents(self.ms1, self.backup_dir)
        self.assertEqual(expected_files, dir_contents)

        self.log('info',
        '8. Update a model item')
        self.execute_cli_create_cmd(self.ms1,
                                    '/software/items/telnet',
                                    'software-item')

        self.log('info',
        '9. Check that no plan is running')
        self._check_plan_not_running()

        self.log('info',
        '10. Run backup script and assert that backup was created correctly')
        start_time = self._get_ms_current_epoch_time()
        archive = self._run_backup_and_assert_success(self.backup_dir)
        end_time = self._get_ms_current_epoch_time()
        expected_files.append(archive)
        archive_timestamp = self._get_archive_timestamp(archive)

        self.assertTrue(
            ((start_time <= archive_timestamp) and
             (end_time >= archive_timestamp),
            'Backup time embedded in archive file name is incorrect'))

    @attr('all', 'revert', 'story124377', 'story124377_tc02', 'bur_only_test')
    def test_02_np_no_backup_created_if_plan_running(self):
        """
        @tms_id: torf_124377_tc02
        @tms_requirements_id: TORF-124377, TORF-107196
        @tms_title:
            Verify that backup is not created if the backup script
            is correctly invoked while a plan is running
        @tms_description:
            Verify that backup is not created if the backup script
            is correctly invoked while a plan is running
        @tms_test_steps:
            @step: Update a property of an existing LITP item
            @result: Item is in "Updated" state
            @step: Create and run the deployment plan
            @result: Plan is running
            @step: Run the litp_state_backup.sh /tmp/archives script
            @result: The script exits with Return Code 0
            @result: The folder /tmp/archives is still empty
            @step: Wait for plan to complete
            @result: Plan completed successfully
            @result: Item is now in "Applied" state and has updated
                property value
            @result: there's no POST requests to /execution/puppet_feedback
                logged in /var/log/litp/litpd_access.log
        @tms_test_precondition: An MS system with LITP DB solution running,
            /tmp/litp_archives exists and is empty
        @tms_execution_type: Automated
        """
        cursor_pos = self.get_file_len(self.ms1, const.LITPD_ACCESS_LOG)

        self.log('info',
        '1. Create the archive folder')
        self.create_dir_on_node(self.ms1, self.backup_dir, su_root=True)

        ms_firewalls = self.find(self.ms1,
                                 '/ms',
                                 'collection-of-firewall-rule')[0]

        self.log('info',
        '2. Create and deploy a new firewall item')
        fw_dir = 'fw_story_124377_plan'
        ms_fw_url = '{0}/{1}'.format(ms_firewalls, fw_dir)

        props = 'name="550 story124377plan"'
        self.execute_cli_create_cmd(self.ms1,
                                    ms_fw_url,
                                    'firewall-rule',
                                    props)
        self.execute_cli_createplan_cmd(self.ms1)
        self.execute_cli_runplan_cmd(self.ms1)
        self.wait_for_plan_state(self.ms1, const.PLAN_IN_PROGRESS, 1, 1)

        self.log('info',
        "3. Attempt to run the backup script while deployment "
           "plan is running.")
        _, err, rc = self._run_backup_script(self.backup_dir)

        self.log('info',
        '4. wait for plan to complete')
        self.assertTrue(
                self.wait_for_plan_state(self.ms1, const.PLAN_COMPLETE))

        self.log('info',
        "5. Check backup script doesn't create archives while deployment "
           "plan is running.")
        self.assertEqual([], err)
        self.assertEqual(0, rc)
        bkp_dir_contents = self.list_dir_contents(self.ms1, self.backup_dir)
        self.assertEqual(0, len(bkp_dir_contents), 'Unexpected archive file')

        self.log('info',
        '6. Check that POST requests are not longer issued against '
           '"/execution/puppet_feedback" url TORF-107196')
        target = '/execution/puppet_feedback'
        post_req = 'POST {0}'.format(target)
        post_req_found = self.wait_for_log_msg(self.ms1,
                                               post_req,
                                               log_file=const.LITPD_ACCESS_LOG,
                                               timeout_sec=10,
                                               log_len=cursor_pos,
                                               return_log_msgs=True)
        self.assertEqual([], post_req_found,
            'POST requests to "{0}" found on "{1}"'.
            format(target, const.LITPD_ACCESS_LOG))

    @attr('all', 'revert', 'story124377', 'story124377_tc03', 'bur_only_test')
    def test_03_n_no_backup_created_if_script_invoked_invalidly(self):
        """
        @tms_id: torf_124377_tc03
        @tms_requirements_id: TORF-124377
        @tms_title:
            Verify that backup is not created if the backup script
            is invoked incorrectly
        @tms_description:
            Verify backup script behaviour on erroneous run attempts - without
            specifying the expected directory argument, more than one argument,
            invalid directory, no write rights etc.
        @tms_test_steps:
            @step: Update an existing applied item
            @result: Item is in "Updated" state
            @step: Assert no plan is running
            @result: no plan is running
            @step: Attempt to run the backup script with a path argument
                that point to a non <non_existing_path>
            @result: The script exits with Return Code 1
            @result: Error message "Specified path <non_existing_path>
                is not a directory" is posted
            @step: Attempt to run the backup script with a path argument
                that point to an <path/to/existing_file>
            @result: The script exits with Return Code 1
            @result: Error message "Specified path <path/to/existing_file>
                is not a directory" is posted
            @step: Attempt to run the backup script with missing path argument
            @result: The script exits with Return Code 1
            @result: Error message "No to-directory specified" is posted
            @step: Attempt to run the backup script
                with more than one argument
            @result: The script exits with Return Code 1
            @result: Error message "Too many arguments" is posted
            @step: Attempt to run the backup script as non-root user
            @result: The script exits with Return Code 1
            @result: Error message "Permission denied" is posted
        @tms_test_precondition: An MS system with LITP DB solution running,
            /tmp/litp_archives exists and is empty
        @tms_execution_type: Automated
        """
        self.create_dir_on_node(self.ms1, self.backup_dir, su_root=True)

        self.log('info',
        '1. make a change in the deployment model')
        self._toggle_dummy_firewall_rule('fw_story124377_tc03')

        self.log('info',
        '2. make sure no plan is running')
        self._check_plan_not_running()

        self.log('info',
        '3. Attempt to run backup script with a path argument pointing to a '
           'not existing path')
        no_such_dir = '/tmp/no/such/directory'
        no_dir_msg = 'Specified path \'{0}\' is not a directory.'. \
                       format(no_such_dir)
        out, _, rc = self._run_backup_script(no_such_dir)
        self.assertTrue(self.is_text_in_list(no_dir_msg, out))
        self.assertEqual(1, rc,
            'Backup script should return 1 if ran with invalid path argument')

        self.log('info',
        '4. Attempt to run backup script with a path argument pointing to an '
           'existing file')
        dummy_file_name = '/tmp/dummy_file_story124377.txt'
        self.create_file_on_node(self.ms1,
                                 dummy_file_name,
                                 ['dummy_file_contents'])
        out, _, rc = self._run_backup_script(dummy_file_name)

        no_dir_msg = 'Specified path \'{0}\' is not a directory.'. \
                       format(dummy_file_name)
        self.assertTrue(self.is_text_in_list(no_dir_msg, out))
        self.assertEqual(1, rc,
            'Backup script should return 1 if ran with invalid path argument')

        self.log('info',
        '5. Attempt to run backup script with missing path argument')
        out, _, rc = self._run_backup_script('')
        self.assertTrue(self.is_text_in_list('too few arguments', out))
        self.assertEqual(2, rc,
            'Backup script should return 2 if ran with missing path argument')

        self.log('info',
        '6. Attempt to run backup script with more than one argument')
        out, _, rc = self._run_backup_script(self.backup_dir + ' dummy/arg')
        self.assertTrue(self.is_text_in_list('unrecognized arguments', out))
        self.assertEqual(2, rc,
            'Backup script should return 2 if ran with too many arguments')

        self.log('info',
        '7. Attempt to run backup script as non root')
        out, err, rc = self._run_backup_script(self.backup_dir,
                                              run_as_root=False)
        self.assertTrue(self.is_text_in_list('Permission denied.', err))
        self.assertEqual(1, rc,
            'Backup script should return 1 if ran as non root')

        dir_contents = self.list_dir_contents(self.ms1, self.backup_dir)
        self.assertEqual([], dir_contents,
            'Backup script should create no archives if ran as non root')

    @attr('all', 'revert', 'story124377', 'story124377_tc04', 'bur_only_test')
    def test_04_np_max_five_archives_stored_under_same_folder(self):
        """
        @tms_id: torf_124377_tc04
        @tms_requirements_id: TORF-124377
        @tms_title:
            Verify that backup script creates not more than five archives
            in same directory.
        @tms_description:
            Verify that the archives folder contains no more than
            five archives. If the archives folder is changed the contents
            of previously used directory should remain unchanged.
        @tms_test_steps:
            @step: Run the litp_state_backup.sh /tmp/archives script five times
                making changes to the model in the meantime (create or
                remove a firewall rule)
            @result: The litp_state_backup.sh completed successfully each time
                and the backup directory contains five archives.
            @step: Make another change in the model
            @result: Model updated
            @step: Run the litp_state_backup.sh /tmp/archives script
            @result: The litp_state_backup.sh completed successfully
            @result: The /tmp/archives folder still contains 5 files
            @result: The oldest archive files has been removed
            @step: Run litp_state_backup.sh /tmp/archives_2 script
            @result: Valid backup archive created in /tmp/archives_2
            @result: Files stored in /tmp/archives remain unchanged
        @tms_test_precondition: An MS system with LITP DB solution running,
            /tmp/litp_archives and /tmp/litp_archives_2 dir exists and is empty
        @tms_execution_type: Automated
        """
        new_fw_rule_id = 'fw_story124377_tc04'
        self.create_dir_on_node(self.ms1, self.backup_dir, su_root=True)
        self.create_dir_on_node(self.ms1, self.backup_dir_2, su_root=True)

        self.log('info',
        '1. Create 5 backup archives in /tmp/litp_archives')
        for _ in range(5):
            time.sleep(1)  # sleep 1s so we don't create 2 files with same name
            self._toggle_dummy_firewall_rule(new_fw_rule_id)
            self._run_backup_script(self.backup_dir)

        bkp_dir_contents = self.list_dir_contents(self.ms1, self.backup_dir)

        archive_file_qty = len(bkp_dir_contents)
        self.assertEqual(5, archive_file_qty,
                         'Expected 5 archive files, found "{0}" in "{1}"'.
                         format(archive_file_qty, self.backup_dir))

        oldest_archive = sorted(bkp_dir_contents)[0]

        self.log('info',
        '2. Create one more backup archive in same directory')
        self._toggle_dummy_firewall_rule(new_fw_rule_id)
        new_archive_file = self._run_backup_and_assert_success(self.backup_dir)

        self.log('info',
        '3. Assert that there are still 5 archive files in the backup dir '
           'and the the new archive file replaced the oldest archive file')

        bkp_dir_contents = self.list_dir_contents(self.ms1, self.backup_dir)

        self.assertEqual(5, len(bkp_dir_contents),
            'Unexpected number of archive files found on backup dir')

        self.assertTrue(self.is_text_in_list(new_archive_file,
                                             bkp_dir_contents),
            'Archive file "{0}" not found in "{1}"'.
            format(new_archive_file, self.backup_dir))

        self.assertFalse(
                        self.is_text_in_list(oldest_archive, bkp_dir_contents),
                        'Extra old archive file "{0}" found in "{1}"'.
                        format(oldest_archive, self.backup_dir))

        self.log('info',
        '4. Run backup script with different target directory '
           '"/tmp/litp_bkp_dir_contents_2"')
        new_archive_file = self._run_backup_and_assert_success(
                                                        self.backup_dir_2)
        bkp_dir2_contents = self.list_dir_contents(self.ms1, self.backup_dir_2)

        self.assertEqual([new_archive_file],
                         bkp_dir2_contents,
            'No archive file was created in "{0}"'.format(self.backup_dir_2))

        self.assertEqual(sorted(bkp_dir_contents),
                         sorted(self.list_dir_contents(self.ms1,
                                                       self.backup_dir)),
                         '/tmp/litp_archives directory contents should '
                         'remain unchanged')

    @attr('all', 'revert', 'story124377', 'story124377_tc05', 'bur_only_test')
    def test_05_p_create_delete_snapshot_enables_backup_creation(self):
        """
        @tms_id: torf_124377_tc05
        @tms_requirements_id: TORF-124377
        @tms_title:
            Verify that creating or removing snapshot enables
            the creation of a backup.
        @tms_description:
            Verify that a backup archive can be created regardless of snapshot
            presence.
        @tms_test_steps:
            @step: Assure a Deployment snapshot exists on system
            @result: deployment snapshot present
            @step: Run the litp_state_backup.sh /tmp/archives script
            @result: The litp_state_backup.sh completed successfully
            @result: One archive file exists under the /tmp/archives folder
            @step: Remove the deployment snapshot and run backup script while
                plan is running
            @result: Backup not allowed while remove snapshot plan is running
            @result: Snapshot removed successfully
            @step: Run the litp_state_backup.sh /tmp/archives script
            @result: The litp_state_backup.sh completed successfully
            @result: Created archive file exists under the /tmp/archives folder
            @step: Create a named snapshot
            @result: named snapshot created successfully
            @step: Run the litp_state_backup.sh /tmp/archives script
            @result: The litp_state_backup.sh completed successfully
            @result: Created archive file exists under the /tmp/archives folder
            @step: remove the named snapshot
            @result: named snapshot removed successfully
            @step: Run the litp_state_backup.sh /tmp/archives script
            @result: The litp_state_backup.sh completed successfully
            @result: Created archive file exists under the /tmp/archives folder
            @step: Create a snapshot, run backup script while plan is running
            @result: Backup not allowed while create snapshot plan is running
            @result: Snapshot created successfully
            @step: Run the litp_state_backup.sh /tmp/archives script
            @result: The litp_state_backup.sh completed successfully
            @result: Created archive file exists under the /tmp/archives folder
        @tms_test_precondition: An MS system with LITP DB solution running,
            /tmp/litp_archives exists and is empty
        @tms_execution_type: Automated
        """
        self.create_dir_on_node(self.ms1, self.backup_dir, su_root=True)

        snapshot_name = 'story_124377_snap'

        self.log('info',
        '1. Make sure deployment snapshot exists')
        if not self.is_snapshot_item_present(self.ms1):
            self.execute_cli_createsnapshot_cmd(self.ms1)
            self.assertTrue(self.wait_for_plan_state(self.ms1,
                                                     const.PLAN_COMPLETE))

        self.log('info',
        '2. Check backup can be created')
        self._run_backup_and_assert_success(self.backup_dir)

        self.log('info',
        '3. Remove the deployment snapshot')
        self.execute_cli_removesnapshot_cmd(self.ms1)

        self.log('info',
        "4. Check that running backup script while snapshot is being removed "
           "isn't allowed")
        _, err, rc = self._run_backup_script(self.backup_dir)
        self.assertTrue(
                self.wait_for_plan_state(self.ms1, const.PLAN_COMPLETE))
        self.assertEqual([], err)
        self.assertEqual(0, rc)

        self.log('info',
        '5. Check backup can be created')
        self._run_backup_and_assert_success(self.backup_dir)

        self.log('info',
        '6. Make sure a named snapshot exists')
        if not self.is_snapshot_item_present(self.ms1,
                                             snapshot_name=snapshot_name):
            self.execute_cli_createsnapshot_cmd(
                                self.ms1,
                                args="-n {0}".format(snapshot_name))
            self.assertTrue(
                self.wait_for_plan_state(self.ms1, const.PLAN_COMPLETE))

        self.log('info',
        '7. Check backup can be created')
        self._run_backup_and_assert_success(self.backup_dir)

        self.log('info',
        '8. Remove the named snapshot')
        self.execute_cli_removesnapshot_cmd(
                                self.ms1,
                                args="-n {0}".format(snapshot_name))
        self.assertTrue(
            self.wait_for_plan_state(self.ms1, const.PLAN_COMPLETE))

        self.log('info',
        '9. Check backup can be created')
        self._run_backup_and_assert_success(self.backup_dir)

        self.log('info',
        '10. Recreate the deployment snapshot')
        self.execute_cli_createsnapshot_cmd(self.ms1)

        self.log('info',
        "11. Check that running backup script while snapshot is being created "
            "isn't allowed")
        _, err, rc = self._run_backup_script(self.backup_dir)
        self.assertTrue(
            self.wait_for_plan_state(self.ms1, const.PLAN_COMPLETE))
        self.assertEqual([], err)
        self.assertEqual(0, rc)

        self.log('info',
        "12. Check backup can be created")
        self._run_backup_and_assert_success(self.backup_dir)

    @attr('all', 'revert', 'story124377', 'story124377_tc016', 'bur_only_test')
    def test_16_n_verify_corrupt_tarball_restore_fails(self):
        """
        @tms_id: torf_124377_tc16
        @tms_requirements_id: TORF-124377
        @tms_title:
            Verify that if tarball file is missing the "litp_db.dump" file,
                the state restore script fails and an error is posted.
        @tms_description:
            Verify that if tarball file is missing the "litp_db.dump" file,
                the state restore script fails and an error is posted.
        @tms_test_steps:
            @step: Create /tmp/litp_archives/ folder
            @result: Folder created successfully
            @result: The folder is empty
            @step: Run the litp_state_backup.sh script
            @result: The litp_state_backup.sh completed successfully
            @result: One archive file exists under /tmp/litp_archives/
            @step: Create /tmp/litp_archives_2/ folder to
                extract backup tarball files to
            @result: Folder created successfully
            @result: The folder is empty
            @step: Extract the tarball to
                /tmp/litp_archives_2/ omitting litp_db.dump
            @result: /tmp/litp_archives_2/ contains the content
                of the backup tarball minus the litp_db.dump file
            @step: Create a tarball with the contents of /tmp/litp_archives_2/
                to produce an invalid backup tarball
            @result: Corrupt backup tarball created
            @step: Change the value of /litp/logging
                force_debug from false to true
            @result: Value of /litp/logging is updated to be true
            @step: Attempt to run a LITP restore with the corrupted tarball
            @result: LITP restore not successful
            @result: Command exits with message "Backup <CORRUPTED TARBALL>
                is incomplete. Binary dump is missing."
            @step: Ensure the value of /litp/logging
                force_debug has not been reverted to false
            @result: The value of /litp/logging force_debug is true
        @tms_test_precondition: An MS system with LITP DB solution running
        @tms_execution_type: Automated
        """
        self.log('info',
                 '1. Create the archive folder /tmp/litp_archives/ on the MS')
        self.create_dir_on_node(self.ms1, self.backup_dir, su_root=True)

        self.log('info', '2. Run backup script and assert success')
        self._run_backup_and_assert_success(self.backup_dir)

        self.log('info', '3. Create folder to extract tarball files to')
        self.create_dir_on_node(self.ms1, self.backup_dir_2, su_root=True)

        self.log('info', '4. Extract the tarball omitting litp_db.dump')
        corrupt_dir = "{0}litp_backup_*".format(self.backup_dir)
        exclude_tar_cmd = '-zxv --exclude "litp_db.dump" -f'
        cmd = self.rhcmd.get_tar_cmd(exclude_tar_cmd, corrupt_dir,
                                     dest="-C " + self.backup_dir_2)
        self.run_command(self.ms1, cmd, su_root=True)

        self.log('info', '5. Create tarball to contain corrupted backup files')
        cmd = self.rhcmd.get_tar_cmd('-czvf', self.corrupt_tar, "*")
        tar_cmd = "cd {0} ; {1} ; cd -".format(self.backup_dir_2, cmd)
        self.run_command(self.ms1, tar_cmd)

        self.log('info', '6. Execute: litp show -p /litp/logging and '
                         'ensure the value of force_debug is false')
        show_property_result = self.get_props_from_url(
            self.ms1, self.logging_url, filter_prop='force_debug')
        self.assertEqual(show_property_result, "false")

        self.log('info', '7. Execute: litp update -p /litp/logging -o '
                         'force_debug=true')
        self.execute_cli_update_cmd(
            self.ms1, self.logging_url, "force_debug=true")

        self.log('info', '8. Attempt to run a LITP backup '
                         'restore with the corrupted tarball')
        out, err, rc = self._run_restore_script(self.corrupt_tar)

        self.log('info', '9. Assert that the LITP backup '
                         'restore exited with correct message')
        self.assertTrue(
            self.is_text_in_list(
                "is incomplete. Binary dump is missing", out))

        self.assertEqual(1, rc, 'Restore script exited with RC "{0}", '
                                'expected RC 1.'.format(rc))

        self.assertEqual([], err, 'Restore script posted the following '
                                  'error:\n {0}'.format('\n'.join(err)))

        self.log('info', '10. Execute: litp show -p /litp/logging and ensure '
                    'the value of force_debug has not been reverted to false')
        show_property_result = self.get_props_from_url(
            self.ms1, self.logging_url, filter_prop='force_debug')
        self.assertEqual(show_property_result, "true")
