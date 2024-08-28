"""
COPYRIGHT Ericsson 2023
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     February 2023
@author:    Neil Cronin, Aniket Vyawahare
@summary:   TORF-634587
            If PuppetDB runs out of heap memory, the following changes have
            been requested:
            -Add a SIGKILL command when puppetdb runs out of memory.
            -Remove java args for out of memory and heap dump.
            -Increase heap size to 4g
            -Change log rotation policy for puppetdb.log
            These changes have been made in code, automated tests for that
            code change are included here.
"""
from litp_generic_test import GenericTest, attr


class Story634587(GenericTest):
    """
        Checks for OnOutOfMemoryError, Heap Size, Heap Dump,Log rotates
        when exceeds maximum size and on weekly basis
    """

    def setUp(self):
        """ Runs before every single test """
        super(Story634587, self).setUp()
        self.ms1 = self.get_management_node_filenames()[0]

    def tearDown(self):
        """ Runs after every single test """
        super(Story634587, self).tearDown()

    def backup_log(self):
        """
        Function that creates a new directory and store the
        existing logs.
        """
        cmd = \
            '/usr/bin//mkdir /tmp/logrotate_bkp'
        stdout, _, _ = self.run_command(self.ms1, cmd, default_asserts=True,
                                        su_root=True)
        self.assertEquals([], stdout)
        cmd = \
            '/usr/bin/mv /var/log/puppetdb/* /tmp/logrotate_bkp'
        stdout, _, _ = self.run_command(self.ms1, cmd, default_asserts=True,
                                        su_root=True)
        self.assertEquals([], stdout)

    def cleanUp_restore_log(self):
        """
        Function that clean up the log used for testing and restore the
        existing logs.
        """
        cmd = \
            '/usr/bin/rm -rf /var/log/puppetdb/*'
        stdout, _, _ = self.run_command(self.ms1, cmd, default_asserts=True,
                                        su_root=True)
        self.assertEquals([], stdout)
        cmd = \
            '/usr/bin/mv  /tmp/logrotate_bkp/* /var/log/puppetdb'
        stdout, _, _ = self.run_command(self.ms1, cmd, default_asserts=True,
                                        su_root=True)
        self.assertEquals([], stdout)
        cmd = \
            '/usr/bin/rm -rf /tmp/logrotate_bkp'
        stdout, _, _ = self.run_command(self.ms1, cmd, default_asserts=True,
                                        su_root=True)
        self.assertEquals([], stdout)

    @attr('all', 'revert', 'story634587', 'story634587_tc01')
    def test_01_p_check_OnOutOfMemoryError_Present(self):
        """
        @tms_id:
            torf_634587_tc_01
        @tms_requirements_id:
            TORF-634587
        @tms_title:
            Checking that the OnOutOfMemoryError is present and SIGKILL is sent
            if it runs OnOutOfMemoryError.
        @tms_description:
            Checking that the OnOutOfMemoryError is present and SIGKILL is sent
            if it runs OnOutOfMemoryError.
        @tms_test_steps:
        @step: Run "Systemctl status puppetdb".
               Grep for the kill-9 command in JAVA_ARGS.
        @result: Grep output shows that the command is in place.

        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        cmd = '/usr/bin/systemctl status puppetdb | ' \
              '/usr/bin/grep -- "-XX:OnOutOfMemoryError=kill -9 %p"'
        stdout, _, _ = self.run_command(self.ms1, cmd, default_asserts=True)
        self.assertTrue(len(stdout) > 0,
                        'FAILURE: Puppetdb was missing the kill -9 command.')

    @attr('all', 'revert', 'story634587', 'story634587_tc02')
    def test_02_p_check_HeapSize(self):
        """
        @tms_id:
            torf_634587_tc_02
        @tms_requirements_id:
            TORF-634587
        @tms_title:
            Check that the heap has been set
                to 4G in size on the puppetdb service.
        @tms_description:
            Check that the heap has been set
                 to 4G in size on the puppetdb service.
        @tms_test_steps:
        @step: Run "Systemctl status puppetdb".
                 Grep for specification of 4g Heap in JAVA_ARGS
        @result: Grep output shows that the -Xmx (max heap size) flag
                  has been set

        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        cmd = '/usr/bin/systemctl status puppetdb | grep -- "-Xmx4g"'
        stdout, _, _ = self.run_command(self.ms1, cmd, default_asserts=True)
        self.assertTrue(len(stdout) > 0,
                        'FAILURE: Puppetdb 4g heap size flag was missing.')

    @attr('all', 'revert', 'story634587', 'story634587_tc03')
    def test_03_p_check_HeapDump(self):
        """
        @tms_id:
            torf_634587_tc_03
        @tms_requirements_id:
            TORF-634587
        @tms_title:
            Check that the HeapDumpOnOutOfMemoryError and HeapDumpPath are not
                present in the list of arguments
        @tms_description:
            Check that the HeapDumpOnOutOfMemoryError and HeapDumpPath are not
            present in the list of arguments
        @tms_test_steps:
        @step: Run systemctl status puppetdb | grep -i "HeapDump"
        @result: HeapDumpOnOutOfMemoryError and HeapDumpPath are not present in
                 the list of arguments.

        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        cmd = '/usr/bin/systemctl status puppetdb | ' \
              '/usr/bin/grep -i "HeapDump"'
        stdout, _, _ = self.run_command(self.ms1, cmd, default_asserts=False)
        self.assertTrue(len(stdout) == 0,
                        'FAILURE: HeapDump parameters are present.')

    @attr('all', 'revert', 'story634587', 'story634587_tc04')
    def test_04_p_check_MaxSize_Logrotate(self):
        """
        @tms_id:
            torf_634587_tc_04

        @tms_requirements_id:
            TORF-634587
        @tms_title:
            Check that the puppetdb log is rotated on a size basis.
        @tms_description:
            Check that the puppetdb log is rotated on a size basis
            when it grows past a certain size (100mb).
        @tms_test_steps:
        @step: Truncate the latest logfile in puppetdb.log, make it 101mb
        @result: A new compressed logfile appears.

        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        # backup of existing log
        self.backup_log()
        try:
            # command to truncate puppetdb.log by 101mb
            cmd = '/usr/bin/truncate -s 101m /var/log/puppetdb/puppetdb.log'
            stdout, _, _ = self.run_command(self.ms1, cmd,
                                            default_asserts=True, su_root=True)
            self.assertEquals([], stdout)
            # setting up the owner and group
            cmd = '/usr/bin/chgrp puppetdb /var/log/puppetdb/puppetdb.log'
            stdout, _, _ = self.run_command(self.ms1, cmd,
                                            default_asserts=True, su_root=True)
            self.assertEquals([], stdout)
            cmd = '/usr/bin/chown puppetdb /var/log/puppetdb/puppetdb.log'
            stdout, _, _ = self.run_command(self.ms1, cmd,
                                            default_asserts=True, su_root=True)
            self.assertEquals([], stdout)
            # run log rotation
            cmd = '/usr/sbin/logrotate /etc/logrotate.d/puppetdb'
            stdout, _, _ = self.run_command(self.ms1, cmd,
                                            default_asserts=True, su_root=True)
            self.assertEquals([], stdout)
            # check that a new compressed file appears
            cmd = "/usr/bin/find /var/log/puppetdb" \
                  " -type f -name puppetdb.log.1.gz"
            stdout, _, _ = self.run_command(self.ms1, cmd,
                                            default_asserts=True, su_root=True)
            self.assertTrue(len(stdout) > 0, 'FAILURE: Log did not rotate.')
        finally:
            # cleanup and log restore
            self.cleanUp_restore_log()

    @attr('all', 'revert', 'story634587', 'story634587_tc04')
    def test_05_p_check_Weekly_Logrotate(self):
        """
        @tms_id:
            torf_634587_tc_05
        @tms_requirements_id:
            TORF-634587
        @tms_title:
            Check that the puppetdb log is rotated on a weekly basis.
        @tms_description:
            Check that the puppetdb log is rotated on a weekly basis.
        @tms_test_steps:
        @step: Truncate the log file with 10mb size and give timestamp of one
               week ago.
        @result: A new compressed logfile appears.

        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        # backup of existing log
        self.backup_log()
        try:
            # creating temporary directory for status file
            cmd = '/usr/bin/mkdir /tmp/temporary.status'
            stdout, _, _ = self.run_command(self.ms1, cmd,
                                            default_asserts=True, su_root=True)
            self.assertEquals([], stdout)
            # creating a temporary status file
            cmd = \
            "/usr/bin/echo $'logrotate state -- version 2' > " \
            "/tmp/temporary.status/logrotate.status "
            stdout, _, _ = self.run_command(self.ms1, cmd,
                                            default_asserts=True, su_root=True)
            self.assertEquals([], stdout)
            # changing the time stamp in status file
            cmd = \
            "/usr/bin/echo $\"'/var/log/puppetdb/puppetdb.log' " \
            "$(date +%Y-%m-%d-%H:%M:%S --date='7 days ago')\" >> " \
            "/tmp/temporary.status/logrotate.status"
            stdout, _, _ = self.run_command(self.ms1, cmd,
                                            default_asserts=True, su_root=True)
            self.assertEquals([], stdout)
            # command to truncate puppetdb.log by 10mb
            cmd = '/usr/bin/truncate -s 10m /var/log/puppetdb/puppetdb.log'
            stdout, _, _ = self.run_command(self.ms1, cmd,
                                            default_asserts=True, su_root=True)
            self.assertEquals([], stdout)
            # setting up the owner and group
            cmd = '/usr/bin/chgrp puppetdb /var/log/puppetdb/puppetdb.log'
            stdout, _, _ = self.run_command(self.ms1, cmd,
                                            default_asserts=True, su_root=True)
            self.assertEquals([], stdout)
            cmd = '/usr/bin/chown puppetdb /var/log/puppetdb/puppetdb.log'
            stdout, _, _ = self.run_command(self.ms1, cmd,
                                            default_asserts=True, su_root=True)
            self.assertEquals([], stdout)
            # run log rotation with a temporary status file
            cmd = '/usr/sbin/logrotate -s ' \
                  '/tmp/temporary.status/logrotate.status '\
                  '/etc/logrotate.d/puppetdb'
            stdout, _, _ = self.run_command(self.ms1, cmd,
                                            default_asserts=True, su_root=True)
            self.assertEquals([], stdout)
            # check that a new compressed file appears
            cmd = "/usr/bin/find /var/log/puppetdb " \
                  "-type f -name puppetdb.log.1.gz"
            stdout, _, _ = self.run_command(self.ms1, cmd,
                                            default_asserts=True, su_root=True)
            self.assertTrue(len(stdout) > 0, 'FAILURE: Log did not rotate.')
        finally:
            # cleanup, log restore and remove temporary file
            cmd = '/usr/bin/rm -rf /tmp/temporary.status'
            stdout, _, _ = self.run_command(self.ms1, cmd,
                                            default_asserts=True, su_root=True)
            self.assertEquals([], stdout)
            self.cleanUp_restore_log()
