"""
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     February 2014
@author:    Luke Murphy
@summary:   Integration test for litpcrypt
            Agile: STORY-378, Sub-Task: 1105
"""

from litp_generic_test import GenericTest, attr
from redhat_cmd_utils import RHCmdUtils
import test_constants
from litp_security_utils import SecurityUtils


class Story378(GenericTest):
    """
    As a site engineer I want to identify a system as requiring a password
    so that the plan can read encrypted passwords required for
    tasks in the plan.
    """

    def setUp(self):
        """
        Run before every test
        """
        super(Story378, self).setUp()
        self.test_ms = self.get_management_node_filename()
        self.rhcmd = RHCmdUtils()
        self.crypt = SecurityUtils()

        # init details for litpcrypt commannds
        self.test_service = "test_service"
        self.test_uname = "test_uname"
        self.test_b64usr = "dGVzdF91bmFtZQ"
        self.test_pword = "test_pword"

    def tearDown(self):
        """
        Run after every test
        """
        super(Story378, self).tearDown()

    def _backup_file(self, node, abs_file_path,
                    reset=False, expect_positive=True):
        """
        Given an absolute path to a file 'abs_file_path', backup this
        file by moving it into the same directory with an identifier
        string appended to it. (identifier = '_Story378_backup')
        """
        # create backup file string
        backup = "{0}_{1}_backup".format(
            abs_file_path, self.__class__.__name__
        )

        # do a 'mv' to backup file
        # if 'reset' is True, we want to move the backup file
        # back to the original
        if reset:
            cmd = self.rhcmd.get_move_cmd(backup, abs_file_path)
        else:
            cmd = self.rhcmd.get_move_cmd(abs_file_path, backup)

        std_out, std_err, rcode = self.run_command(node, cmd, su_root=True)

        if expect_positive:
            self.assertEqual([], std_out)
            self.assertEqual([], std_err)
            self.assertEqual(0, rcode)
        else:
            self.assertEqual([], std_out)
            self.assertNotEqual([], std_err)
            self.assertNotEqual(0, rcode)

    @attr('all', 'revert', 'story378', 'story378_tc01')
    def test_01_p_litpcrypt_cli(self):
        """
        @tms_id: litpcds_378_tc01
        @tms_requirements_id: LITPCDS-378
        @tms_title: litpcrypt command restores valid
            litp_shadow file if missing
        @tms_description: Backup current litp_shadow file and run a test
            litpcrypt command that should create a new litp_shadow file
            and within it hold the correct contents:
            (item name, username, password hash)
        @tms_test_steps:
         @step: run "litpcrypt set test_service test_uname test_pword"
         @result: new shadow_file created
         @result: the created shadow_file contains specified service name
         @result: the created shadow_file contains specified user name encoded
            in base64
         @result: the created shadow_file does not contain specified username
            in plain text
         @step: run "litpcrypt delete test_service test_uname"
         @result: the shadow_file contents are removed but file is not deleted
        @tms_test_precondition: /opt/ericsson/nms/litp/etc/litp_shadow missing
            (backed up)
        @tms_execution_type: Automated
        """
        file_backed_up = False
        try:
            self.log('info', '1. backup current litp_shadow file')
            self._backup_file(
                self.test_ms, test_constants.LITP_SHADOW_FILE, reset=False)
            file_backed_up = True

            self.log('info', '2. run litpcrypt command')
            set_cmd = self.crypt.get_litpcrypt_set_cmd(self.test_service,
                                                       self.test_uname,
                                                       self.test_pword)

            # using root here because we have remove litp_crypt file
            # and litp-admin will not have permissions to create
            # a new litp_shadow file
            std_out, std_err, rcode = self.run_command(
                self.test_ms, set_cmd, su_root=True
            )
            self.assertEqual([], std_out)
            self.assertEqual([], std_err)
            self.assertEqual(0, rcode)

            self.log('info', '3. check litp_shadow file exists')
            self.assertTrue(
                self.remote_path_exists(
                    self.test_ms, test_constants.LITP_SHADOW_FILE,
                    expect_file=True
                )
            )

            self.log('info', '4. parse information')
            std_out = self.get_file_contents(self.test_ms,
                                             test_constants.LITP_SHADOW_FILE)
            self.assertNotEqual([], std_out)

            self.log('info', '5. do formatting of returned values from '
                             'litp_shadow file')
            shadow_dict = self.crypt.get_litpshadow_dict(std_out)

            self.log('info', '6. assert expected values from litp_shadow file')
            self.assertTrue(self.test_service in shadow_dict.keys(),
                            "Service name does not appear in shadow file")

            self.assertTrue(self.test_b64usr in shadow_dict[self.test_service],
                            "Username does not exist under expected service "\
                                + "in shadow file")

            self.assertFalse(self.test_uname in shadow_dict[self.test_service],
                    "Plaintext username found under expected service in "\
                    "shadow file")

            self.log('info', '7. run litpcrypt delete command')
            delete_cmd = self.crypt.get_litpcrypt_delete_cmd(self.test_service,
                                                             self.test_uname)

            std_out, std_err, rcode = self.run_command(
                self.test_ms, delete_cmd,
            )
            self.assertEqual([], std_out)
            self.assertEqual([], std_err)
            self.assertEqual(0, rcode)

            self.log('info', '8. verify that the contents of litp_shadow '
                             'are empty')
            len_cmd = self.rhcmd.get_file_len_cmd(
                test_constants.LITP_SHADOW_FILE
            )

            # run command
            std_out, std_err, rcode = self.run_command(self.test_ms, len_cmd)
            self.assertNotEqual([], std_out)
            self.assertEqual([], std_err)
            self.assertEqual(0, rcode)
            self.assertEqual(0, int(std_out[0]))
        finally:
            if file_backed_up:
                self.log('info', 'FINALLY 9. reset backup of litp_shadow file')
                self._backup_file(
                    self.test_ms, test_constants.LITP_SHADOW_FILE, reset=True
                )

    @attr('all', 'revert', 'story378', 'story378_tc02')
    def test_02_p_verify_security_conf(self):
        """
        @tms_id: litpcds_378_tc02
        @tms_requirements_id: LITPCDS-378
        @tms_title: validate /etc/litp_security.conf file on ms
        @tms_description: For every MS, there is a security conf file located
            at /etc/litp_security.conf. In this file, there
            are paths defined that should exist. This test verifies
            that.
        @tms_test_steps:
         @step: check that /etc/litp_security.conf file exists on ms
            and is not empty
         @result: file exists and is not empty
         @step: check each "path:" in file points to an existing file on ms
         @result: each "path:" specified in /etc/litp_security.conf file
            points to a file existing on the ms
        @tms_test_precondition: N/A
        @tms_execution_type: Automated
        """
        self.log('info', '1. check /etc/litp_security.conf exists')
        self.assertTrue(
            self.remote_path_exists(
                self.test_ms,
                test_constants.LITP_SEC_CONF_FILE,
                expect_file=True
            )
        )

        self.log('info', '2. check /etc/litp_security.conf file is not empty')
        std_out = self.get_file_contents(self.test_ms,
                                         test_constants.LITP_SEC_CONF_FILE)
        self.assertNotEqual([], std_out)

        self.log('info', '3. parse paths from /etc/litp_security.conf')
        paths = list()
        for line in std_out:
            if line.startswith("path:"):
                paths.append(line.replace("path:", "").strip())

        self.log('info', '4. check paths as specified '
                         'in /etc/litp_security.conf exist')
        for path in paths:
            self.assertTrue(
                self.remote_path_exists(
                    self.test_ms, path, expect_file=True
                )
            )

    @attr('all', 'revert', 'story378', 'story378_tc03')
    def test_03_n_start_stop_litp(self):
        """
        @tms_id: litpcds_378_tc03
        @tms_requirements_id: LITPCDS-378
        @tms_title: litp doesn't start if /etc/litp_security.conf missing
        @tms_description: Stop litpd service, move the security conf file,
            assert that the litpd service will fail when starting
            back up.
        @tms_test_steps:
         @step: issue service litpd start command
         @result: litp fails to start with return code 1
        @tms_test_precondition: /etc/litp_security.conf file missing
            (backed up), litp stopped
        @tms_execution_type: Automated
        """
        file_backed_up = False
        try:
            self.log('info', '1. Stop litpd service on ms')
            self.stop_service(self.test_ms, "litpd")

            self.log('info', '2. remove backup the file')
            self._backup_file(
                self.test_ms, test_constants.LITP_SEC_CONF_FILE, reset=False)
            file_backed_up = True

            self.log('info', '3. start litpd service')
            std_out, _, rc = self.start_service(self.test_ms, "litpd",
                                               assert_success=False)
            # No error message is returned when service fails
            # to start because the command uses systemctl in RHEL7
            # which returns no output and return code should be 1
            self.assertEqual([], std_out)
            self.assertEqual(1, rc)

        finally:
            self.log('info', '6. FINALLY restore the backed up file and '
                             'restart litp')
            # if the test failed before backing up the conf file, don't restore
            if file_backed_up:
                self._backup_file(
                    self.test_ms, test_constants.LITP_SEC_CONF_FILE, reset=True
                )
            # 7. start back up the litp service
            # This util also re-enables debug
            self.restart_litpd_service(self.test_ms)

    @attr('all', 'revert', 'story378', 'story378_tc04')
    def test_04_n_litpcrypt_cli(self):
        """
        @tms_id: litpcds_378_tc04
        @tms_requirements_id: LITPCDS-378
        @tms_title: litp_shadow file not created/removed on invalid
            litpcrypt params
        @tms_description: Attempt to set a service password + username
            with empty values using the litpcrypt command and assert
            that the command fails and no litp_shadow file is created (since
            we backed the original up)
        @tms_test_steps:
         @step: run an invalid "litpcrypt set" command - no mandatory arguments
         @result: "litpcrypt set: error: too few arguments" error message
            posted, litp_shadow file not created
         @step: run "/usr/bin/litpcrypt set test_service test_uname" command
            i.e. missing mandatory password argument
         @result: "Error: password must not be empty" error message posted
            litp_shadow file not created
         @step: recreate litp_shadow file by issuing a valid litpcrypt command
         @result: litp_shadow file created successfully
         @step: run a "litpcrypt delete service_blah test_uname" i.e. with an
            unknown service name
         @result: "Given service does not exist" error message posted
         @step: run a "litpcrypt delete test_service user_blah " i.e. with an
            unknown username
         @result: "Given user does not exist" error message posted
         @step: run a "litpcrypt delete" command i.e. missing mandatory
            arguments
         @result: "litpcrypt delete: error: too few arguments" error message
            posted
         @step: run a "litpcrypt delete  test_uname" command without mandatory
            service argument
         @result: "litpcrypt delete: error: too few arguments" error message
            posted
        @tms_test_precondition: /opt/ericsson/nms/litp/etc/litp_shadow missing
            (backed up)
        @tms_execution_type: Automated
        """
        # init error messages
        too_few_args_err = "error: too few arguments"
        password_empty_err = "Error: password must not be empty"
        file_backed_up = False

        try:
            self.log('info', '1. backup current litp_shadow file')
            self._backup_file(
                self.test_ms, test_constants.LITP_SHADOW_FILE, reset=False)
            file_backed_up = True

            self.log('info', '2. run invalid litpcrypt commands'
                             ' and check litp_shadow file wasn\'t created')

            # all params empty
            set_cmd = self.crypt.get_litpcrypt_set_cmd('', '', '')
            std_out, std_err, rcode = self.run_command(self.test_ms, set_cmd)

            self.assertEqual([], std_out)
            self.assertNotEqual([], std_err)
            self.assertNotEqual(0, rcode)
            self.assertTrue(self.is_text_in_list(too_few_args_err, std_err))

            self.assertFalse(
                self.remote_path_exists(
                    self.test_ms,
                    test_constants.LITP_SHADOW_FILE,
                    expect_file=True
                )
            )

            # password empty
            set_cmd = self.crypt.get_litpcrypt_set_cmd(self.test_service,
                                                       self.test_uname,
                                                       '')

            std_out, std_err, rcode = self.run_command(self.test_ms, set_cmd)
            self.assertNotEqual([], std_err)
            self.assertTrue(self.is_text_in_list(password_empty_err, std_err))
            self.assertEqual([], std_out)
            self.assertNotEqual(0, rcode)

            self.assertFalse(
                self.remote_path_exists(
                    self.test_ms,
                    test_constants.LITP_SHADOW_FILE,
                    expect_file=True
                )
            )

            self.log('info', '4. Provide valid commands to create '
                             'litp_shadow file to test')
            # delete case
            set_cmd = self.crypt.get_litpcrypt_set_cmd(self.test_service,
                                                       self.test_uname,
                                                       self.test_pword)

            # using root here because we have remove litp_crypt file
            # and litp-admin will not have permissions to create
            # a new litp_shadow file
            std_out, std_err, rcode = self.run_command(
                self.test_ms, set_cmd, su_root=True
            )
            self.assertEqual([], std_out)
            self.assertEqual([], std_err)
            self.assertEqual(0, rcode)

            self.log('info', '4. run invalid litpcrypt delete commands')
            #    and assert they failed
            # invalid parameters - service name does not exist
            delete_cmd = self.crypt.get_litpcrypt_delete_cmd('service_blah',
                                                             self.test_uname)

            std_out, std_err, rcode = self.run_command(
                self.test_ms, delete_cmd
            )

            self.assertNotEqual([], std_err)
            self.assertTrue(
                self.is_text_in_list("Given service does not exist", std_err)
            )
            self.assertEqual([], std_out)
            self.assertNotEqual(0, rcode)

            # invalid parameters - username does not exist
            delete_cmd = self.crypt.get_litpcrypt_delete_cmd(self.test_service,
                                                             'user_blah')

            std_out, std_err, rcode = self.run_command(
                self.test_ms, delete_cmd
            )

            self.assertNotEqual([], std_err)
            self.assertTrue(
                self.is_text_in_list("Given username does not exist", std_err)
            )
            self.assertEqual([], std_out)
            self.assertNotEqual(0, rcode)

            # missing parameters
            delete_cmd = self.crypt.get_litpcrypt_delete_cmd('', '')
            std_out, std_err, rcode = self.run_command(
                self.test_ms, delete_cmd
            )

            self.assertNotEqual([], std_err)
            self.assertEqual([], std_out)
            self.assertNotEqual(0, rcode)
            self.assertTrue(self.is_text_in_list(too_few_args_err, std_err))

            # service parameter missing
            delete_cmd = \
                self.crypt.get_litpcrypt_delete_cmd('', self.test_uname)

            std_out, std_err, rcode = self.run_command(
                self.test_ms, delete_cmd
            )
            self.assertNotEqual([], std_err)
            self.assertTrue(self.is_text_in_list(too_few_args_err, std_err))
            self.assertEqual([], std_out)
            self.assertNotEqual(0, rcode)

        finally:
            if file_backed_up:
                self.log('info', 'FINALLY 5. restore backed up '
                                 'litp_shadow file')
                self._backup_file(
                    self.test_ms, test_constants.LITP_SHADOW_FILE, reset=True
                )

    @attr('all', 'revert', 'story378', 'story378_tc05')
    def test_05_n_invalid_security_conf(self):
        """
        @tms_id: litpcds_378_tc05
        @tms_requirements_id: LITPCDS-378
        @tms_title: litpd service doesn't start when litp_security conf file
                    contains invalid information
        @tms_description: Verify that if the litp_security conf file contains
            invalid information, a litpd service start will fail
        @tms_test_steps:
         @step: issue a service litpd start command
         @result: litp doesn't start, returns return code 1 and std_out empty
        @tms_test_precondition: /etc/litp_security.conf file with invalid
            contents present, litp stopped
        @tms_execution_type: Automated
        """
        file_backed_up = False

        try:
            self.log('info', '1. Stop litpd service')
            self.stop_service(self.test_ms, "litpd")

            self.log('info', '2. backup the file')
            self._backup_file(
                self.test_ms, test_constants.LITP_SEC_CONF_FILE, reset=False)
            file_backed_up = True

            self.log('info', '3. create a garbled litp_security_conf file')
            invalid_contents = ['invalid']
            self.assertTrue(
                self.create_file_on_node(self.test_ms,
                                         test_constants.LITP_SEC_CONF_FILE,
                                         invalid_contents, su_root=True,
                                         add_to_cleanup=False),
                "Could not create file")

            self.log('info', '4. start litpd service')

            std_out, _, rcode = self.start_service(self.test_ms, "litpd",
                                                   assert_success=False)

            # check for expected std_out and return code
            self.assertEqual([], std_out)
            self.assertEqual(1, rcode)

        finally:
            self.log('info', 'FINALLY 6. restore the backed up file '
                             'and restart litp')
            # if the test failed before backing up the conf file, don't restore
            if file_backed_up:
                # the 'mv' will overwrite the garbled
                # file we created previously
                self._backup_file(
                    self.test_ms, test_constants.LITP_SEC_CONF_FILE, reset=True
                )

            # 7. start back up the litp service
            # This util also re-enables debug
            self.restart_litpd_service(self.test_ms)
