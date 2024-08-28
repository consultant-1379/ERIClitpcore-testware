"""
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     September 2022
@author:    Paul Chambers
@summary:   To-Do
"""
from litp_generic_test import GenericTest, attr
from litp_cli_utils import CLIUtils
import test_constants as const


class Story603745(GenericTest):
    '''
    As a LITP User I want to be able to retrieve the version information,
    so that I can provide this info when troubleshooting issues
    '''

    def setUp(self):
        """
        Description:
            Runs before every single test
        """
        # 1. Call super class setup
        super(Story603745, self).setUp()
        self.cli = CLIUtils()
        self.ms_node = self.get_management_node_filename()

    def tearDown(self):
        """
        Description:
            Runs after every test to perform the test teardown/cleanup
        """
        # call super class teardown
        super(Story603745, self).tearDown()

    def snapshot_item_exists(self):
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

    def _create_snapshot(self, snapshot_names):
        """
        Description:
            Create snapshots and wait for plan to complete
        Args:
            snapshot_name (list): The list of snapshots to create
        """
        if snapshot_names is not None:
            for snapshot in snapshot_names:
                self.execute_cli_createsnapshot_cmd(
                    self.ms_node, '-n {0}'.format(snapshot))
                self.assertTrue(
                    self.wait_for_plan_state(
                        self.ms_node, const.PLAN_COMPLETE),
                        'Plan to create snapshot "{0}" ' \
                        'failed'.format(snapshot))
        else:
            self.execute_cli_createsnapshot_cmd(
                self.ms_node)
            self.assertTrue(
                self.wait_for_plan_state(
                    self.ms_node, const.PLAN_COMPLETE),
                    'Plan to create snapshot failed')

    def record_tables(self, version_no):
        """
        Description:
            Create file containing the model and extension tables.
        Args:
            version_no (str): This will be part of the name of the created
            files.
        """
        get_extensions = 'sudo su - postgres -c "psql ' \
        ' -d litp -h ms1 -c \\"select model_id from extensions\\""'
        self.log('info', 'get_extensions = {0}'.format(get_extensions))
        get_model = 'sudo su - postgres -c "psql -d litp -h ms1 -c ' \
        ' \\"select model_id from model\\""'
        self.log('info', 'get_model = {0}'.format(get_model))

        extension_note_version = "> extension_{0}.txt".format(version_no)
        model_note_version = " > model_{0}.txt".format(version_no)

        cmd = get_extensions + extension_note_version
        self.log('info', 'extensions cmd = {0}'.format(cmd))
        self.run_command(self.ms_node, cmd, su_root=True, default_asserts=True)

        cmd = get_model + model_note_version
        self.log('info', 'model cmd = {0}'.format(cmd))
        self.run_command(self.ms_node, cmd, su_root=True, default_asserts=True)

    def remove_snapshot(self, args=''):
        """
        Description:
            Removes either defualt snapshot or named snapshot if a name
            is specified.
        Args:
            args (str): This will be added to the end of the remove_snapshot
            acommand. eg "-n snapshot_name".
        """
        cmd = self.cli.get_remove_snapshot_cmd(args)
        self.run_command(self.ms_node, cmd, default_asserts=True)
        self.assertTrue(
            self.wait_for_plan_state(self.ms_node,
                const.PLAN_COMPLETE))

    def get_table_contents(self):
        """
        Description:
            Collects contents from generated model and extension table files.
        Returns:
            list, list. List of lists containing the the recoreded tables
            from the model and extension tables.
        """
        cmd = "cat extension_a.txt"
        ext_a, _, _ = self.run_command(self.ms_node, cmd,
            su_root=True, default_asserts=True)
        self.log('info', 'ext_a = {0}'.format(ext_a))
        cmd = "cat extension_b.txt"
        ext_b, _, _ = self.run_command(self.ms_node, cmd,
            su_root=True, default_asserts=True)
        self.log('info', 'ext_b = {0}'.format(ext_b))
        cmd = "cat extension_c.txt"
        ext_c, _, _ = self.run_command(self.ms_node, cmd,
            su_root=True, default_asserts=True)
        ext_list = [ext_a, ext_b, ext_c]

        cmd = "cat model_a.txt"
        mod_a, _, _ = self.run_command(self.ms_node, cmd,
            su_root=True, default_asserts=True)
        self.log('info', 'ext_a = {0}'.format(ext_a))
        cmd = "cat model_b.txt"
        mod_b, _, _ = self.run_command(self.ms_node, cmd,
            su_root=True, default_asserts=True)
        self.log('info', 'ext_b = {0}'.format(ext_b))
        cmd = "cat model_c.txt"
        mod_c, _, _ = self.run_command(self.ms_node, cmd,
            su_root=True, default_asserts=True)
        mod_list = [mod_a, mod_b, mod_c]

        return ext_list, mod_list

    @attr('all', 'revert', 'story603745', 'story603745_tc01')
    def test_01_p_remove_snapshots_dataset(self):
        """
        @tms_id: TORF-603745_tc01
        @tms_requirements_id: TORF-603745
        @tms_title: Remove snapshots
        @tms_description: Create a snapshot, then remove it, checking LITP
            Database model table and the extension table for any leftover
            datasets.
        @tms_test_steps:
            @step: Remove any existing snapshots.
            @result: Any existing snapshots are removed.
            @step: Take a recording of the model and extension tables.
            @result: A recording of the model and extension tables was made.
            @step: Create a snpashot.
            @result: A snapshot was created.
            @step: Take a recording of the model and extension tables.
            @result: A recording of the model and extension tables was made.
            @step: Remove the snapshots.
            @result: The shpashot was removed.
            @step: Take a recording of the model and extension tables.
            @result: A recording of the model and extension tables was made.
        @tms_test_precondition: Litp installed on RHEL7
        @tms_execution_type: Automated
        """
        if self.snapshot_item_exists() == True:
            self.log('info', 'Removing all snapshots.')
            self.remove_all_snapshots(self.ms_node)
        self.record_tables('a')

        self._create_snapshot(None)
        self.assertTrue(self.snapshot_item_exists(), 'Snapshot not created')
        self.record_tables('b')

        self.remove_all_snapshots(self.ms_node)
        self.assertFalse(self.snapshot_item_exists(), 'Snapshot still present')
        self.record_tables('c')

        ext, mod = self.get_table_contents()
        self.log('info', 'ext = {0}'.format(ext))
        self.log('info', 'mod = {0}'.format(mod))

        assert "SNAPSHOT_snapshot" not in ext[0]
        assert "SNAPSHOT_snapshot" in ext[1]
        assert "SNAPSHOT_snapshot" not in ext[2]

        assert "SNAPSHOT_snapshot" not in mod[0]
        assert "SNAPSHOT_snapshot" in mod[1]
        assert "SNAPSHOT_snapshot" not in mod[2]

    @attr('all', 'revert', 'story603745', 'story603745_tc02')
    def test_02_p_remove_named_snapshots_dataset(self):
        """
        @tms_id: TORF-603745_tc02
        @tms_requirements_id: TORF-603745
        @tms_title: Remove Named snapshots.
        @tms_description: Create a named snapshot, then remove it,
            checking LITP Database model table and the extension
            table for any leftover datasets.
        @tms_test_steps:
            @step: Remove any existing snapshots.
            @result: Any existing snapshots are removed.
            @step: Take a recording of the model and extension tables.
            @result: A recording of the model and extension tables was made.
            @step: Create 2 named test snpashots.
            @result: Two named test snapshots were created.
            @step: Take a recording of the model and extension tables.
            @result: A recording of the model and extension tables was made.
            @step: Remove one named test snapshot.
            @result: One named test shpashot was removed.
            @step: Take a recording of the model and extension tables.
            @result: A recording of the model and extension tables was made.
        @tms_test_precondition: Litp installed on RHEL7
        @tms_execution_type: Automated
        """
        if self.snapshot_item_exists() == True:
            self.log('info', 'Removing all snapshots.')
            self.remove_all_snapshots(self.ms_node)
        self.record_tables('a')

        self._create_snapshot(["TestOne", "TestTwo"])
        self.assertTrue(self.snapshot_item_exists(), 'Snapshot not created')
        self.record_tables('b')

        self.remove_snapshot(" -n {0}".format("TestOne"))
        self.record_tables('c')

        ext, mod = self.get_table_contents()
        self.log('info', 'ext = {0}'.format(ext))
        self.log('info', 'mod = {0}'.format(mod))

        assert "SNAPSHOT_TestOne" not in ext[0]
        assert "SNAPSHOT_TestTwo" not in ext[0]
        assert "SNAPSHOT_TestOne" in ext[1]
        assert "SNAPSHOT_TestTwo" in ext[1]
        assert "SNAPSHOT_TestOne" not in ext[2]
        assert "SNAPSHOT_TestTwo" in ext[2]

        assert "SNAPSHOT_TestOne" not in mod[0]
        assert "SNAPSHOT_TestTwo" not in mod[0]
        assert "SNAPSHOT_TestOne" in mod[1]
        assert "SNAPSHOT_TestTwo" in mod[1]
        assert "SNAPSHOT_TestOne" not in mod[2]
        assert "SNAPSHOT_TestTwo" in mod[2]

    @attr('all', 'revert', 'story603745', 'story603745_tc02')
    def test_03_p_remove_snapshots_dataset_restart_LITPd(self):
        """
        @tms_id: TORF-603745_tc03
        @tms_requirements_id: TORF-603745
        @tms_title: Verify run plan help is correct.
        @tms_description: Verify help for "litp run_plan -h"
        @tms_test_steps:
            @step: Remove any existing snapshots.
            @result: Any existing snapshots are removed.
            @step: Take a recording of the model and extension tables.
            @result: A recording of the model and extension tables was made.
            @step: Create a named snapshot and an un-named snapshot.
            @result: Two snapshots were created.
            @step: Take a recording of the model and extension tables.
            @result: A recording of the model and extension tables was made.
            @step: Remove the un-named snapshot.
            @result: The un-named shpashot was removed.
            @step: Take a recording of the model and extension tables.
            @result: A recording of the model and extension tables was made.
        @tms_test_precondition: Litp installed on RHEL7
        @tms_execution_type: Automated
        """
        if self.snapshot_item_exists() == True:
            self.log('info', 'Removing all snapshots.')
            self.remove_all_snapshots(self.ms_node)
        self.record_tables('a')

        self._create_snapshot(None)
        self._create_snapshot(["TestOne"])
        self.assertTrue(self.snapshot_item_exists(), 'Snapshot not created')

        # restrart litpd
        self.restart_litpd_service(self.ms_node)
        self.record_tables('b')

        self.remove_snapshot()
        # restrart litpd
        self.restart_litpd_service(self.ms_node)
        self.record_tables('c')

        ext, mod = self.get_table_contents()
        #self.log('info', 'ext = {0}'.format(ext))
        #self.log('info', 'mod = {0}'.format(mod))

        assert "SNAPSHOT_TestOne" not in ext[0]
        assert "SNAPSHOT_snapshot" not in ext[0]
        assert "SNAPSHOT_TestOne" in ext[1]
        assert "SNAPSHOT_snapshot" in ext[1]
        assert "SNAPSHOT_TestOne" in ext[2]
        assert "SNAPSHOT_snapshot" not in ext[2]

        assert "SNAPSHOT_TestOne" not in mod[0]
        assert "SNAPSHOT_snapshot" not in mod[0]
        assert "SNAPSHOT_TestOne" in mod[1]
        assert "SNAPSHOT_snapshot" in mod[1]
        assert "SNAPSHOT_TestOne" in mod[2]
        assert "SNAPSHOT_snapshot" not in mod[2]
