'''
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     October 2018
@author:    Niamh McGann
@summary:   Integration tests for the litpmsdbpwd script.
            User Story: TORF-289941
'''

from collections import OrderedDict
from hashlib import md5
from litp_generic_test import GenericTest, attr

import test_constants as const


class Story289941(GenericTest):
    """ TORF-289941:
    As a LITP user I want the ability to configure the password
    for the 'postgres' superuser in the PostgreSQL DB on the LMS.
    """

    def setUp(self):
        """ Runs before every test to perform required setup. """
        super(Story289941, self).setUp()
        self.backup_filepath = '/tmp/'
        self.db_backup_path = "{0}pg_litp-db_backup.sql".format(
                                            self.backup_filepath)
        self.ms_node = self.get_management_node_filename()
        self.ms_path = self.find(self.ms_node, '/', 'ms',
                                exact_match=True)[0]
        self.ms_hostname = self.get_hostname_of_node(self.ms_node,
                                                     self.ms_path)
        self.start_pos = self.get_file_len(self.ms_node,
                                           const.GEN_SYSTEM_LOG_PATH)
        self.initial_pg_passwd_hash = self.set_password_hash(
                                        const.POSTGRES_INITIAL_PASSWORD)
        self.new_pg_passwd = 'T3st_P4ssw0rd'
        self.new_pg_passwd_hash = self.set_password_hash(
                                        self.new_pg_passwd)
        self.puppet_manifest_file = "{0}db_pwd.pp".format(
                                            const.PUPPETDB_MANIFESTS_DIR)
        self.puppet_backup_file = "{0}db_pwd.pp".format(
                                                    self.backup_filepath)
        self.backup_puppet_manifest()
        self.backup_postgres()

    def tearDown(self):
        """ Runs after every test to perform required cleanup/teardown. """
        self.restore_puppet_manifest()
        self.restore_postgres()
        super(Story289941, self).tearDown()

    def backup_postgres(self):
        """ Description:
                Backup the postgres litp database to a file.
            Actions:
                1. Create a backup file of postgres on the MS.
            Results:
                Backup file created.
        """
        cmd = "{0} - postgres -- pg_dump -Fc -c -h ms1 -f {1} litp". \
            format(const.SU_PATH, self.db_backup_path)
        self.run_command(self.ms_node, cmd, su_root=True, default_asserts=True)

    def backup_puppet_manifest(self):
        """ Description:
                Copy the db_pwd.pp puppet manifest file to back it up.
            Actions:
                1. cp the puppet manifest file to the backup location.
            Results:
                Puppet manifest file backed-up successfully.
        """
        self.assertTrue(self.cp_file_on_node(self.ms_node,
            self.puppet_manifest_file, self.puppet_backup_file,
            su_root=True, add_to_cleanup=False),
            "Puppet manifest backup failed!")

    def restore_postgres(self):
        """ Description:
                Restore postgres on the MS from the backup file
            Actions:
                1. Stop the litpd service.
                2. Restore postgres from the backup file.
                3. Start the litpd service.
            Results:
                Backup restored.
        """
        self.stop_service(self.ms_node, 'litpd')

        cmd = "{0} - postgres -- pg_restore -d litp -c -h ms1 {1}". \
              format(const.SU_PATH, self.db_backup_path)
        self.run_command(self.ms_node, cmd, su_root=True)

        self.del_file_after_run(self.ms_node, self.db_backup_path)

        # Restore password in pg_shadow view
        postgres_cmd = "{0} -U postgres -h ms1 -c ".format(const.PSQL_PATH)
        psql_cmd = "\\\"ALTER ROLE postgres PASSWORD '{0}'".format(
                    self.initial_pg_passwd_hash)
        cmd = "{0} - postgres -c \"{1} {2}; \\\"\" ". \
            format(const.SU_PATH, postgres_cmd, psql_cmd)
        self.run_command(self.ms_node, cmd, su_root=True)

        self.start_service(self.ms_node, 'litpd')

    def restore_puppet_manifest(self):
        """ Description:
                Restore the puppet manifest file on the MS.
            Actions:
                1. Stop the puppet service.
                2. Copy the back-up file to the puppet location.
                3. Start the puppet service.
            Results:
                Backup restored.
        """
        self.stop_service(self.ms_node, 'puppet')

        self.cp_file_on_node(self.ms_node, self.puppet_backup_file,
                        self.puppet_manifest_file, su_root=True,
                        add_to_cleanup=False)

        self.start_service(self.ms_node, 'puppet')

        self.del_file_after_run(self.ms_node, self.puppet_backup_file)

    @staticmethod
    def set_password_hash(password):
        """ Description:
                Create a hash of the supplied password.
            Args:
                password (str): The password to generate a hash of.
            Actions:
                1. Create a hash of the password with 'postgres'
                appended to it.
                2. Prepend 'md5' to the hash.
                3. Return the final hash value.
            Results:
                Created hash is returned.
        """
        return 'md5{0}'.format(md5('{0}postgres'.format(password)).hexdigest())

    def get_password_hash_from_db(self):
        """ Description:
                Read the password hash from the db.
            Actions:
                1. Build up the command to run.
                2. Run the command.
                3. Return the output of the command.
            Results:
                Password hash is retrieved from the db & returned.
        """
        db_name = 'postgres'
        db_user = 'postgres'
        table = 'pg_shadow'
        postgres_cmd = "{0} -U {1} -d {2} -h ms1 -c".format(
                    const.PSQL_PATH, db_user, db_name)
        psql_cmd = "'SELECT usename, passwd FROM {0}; '".format(table)
        # Get passwd hash from DB
        cmd = "{0} - postgres -c \"{1} {2}\" ".format(const.SU_PATH,
            postgres_cmd, psql_cmd)
        query_out, _, _ = self.run_command(self.ms_node, cmd, su_root=True,
                                            default_asserts=True)
        self.assertNotEqual([], query_out, "Query response is empty!")

        for line in query_out:
            if db_user in line:
                pg_user_hash = line.split(" | ")

        return pg_user_hash[len(pg_user_hash) - 1]

    @attr('all', 'revert', 'Story289941', 'Story289941_tc15')
    def test_15_p_change_postgres_superuser_password(self):
        """
        @tms_id: torf_289941_tc_15
        @tms_requirements_id: TORF-289941
        @tms_title:
            Change 'postgres' superuser password (Pos).
        @tms_description:
            Verify that the 'postgres' superuser password is
            changed when all of the conditions are met.
        @tms_test_steps:
            @step: Run the 'litpmsdbpwd' script on the MS as root user.
            @result: The script exits with result code 0.
            @step: Confirm that the 'pg_shadow' view has been updated with the
                   new password hash.
            @result: New password hash exists in the 'pg_shadow' view.
            @step: Confirm new password hash is not equal to
                   the initial one.
            @result: Password hash values are not equal.
            @step: Confirm that no instances of the password have been logged.
            @result: Plain text & password hash not logged.
        @tms_test_precondition:
            - A backup of the db_pwd.pp puppet manifest file has been taken.
            - A backup of the litp database has been taken.
            - The current 'postgres' superuser password is available.
            - The hash of the current 'postgres' superuser password is
              available.
            - The hash of the new 'postgres' superuser password is available.
        @tms_execution_type: Automated
        """

        self.log('info', "1. Running the 'litpmsdbpwd' script on"
            " the MS as root user.")
        # Building a list of prompt-response dictionaries for
        # use when running the script.
        expects_cmds = []
        passwd_dict = OrderedDict([("Current password:",
                                    const.POSTGRES_INITIAL_PASSWORD),
                                    ("New password:",
                                     self.new_pg_passwd),
                                    ("Confirm new password:",
                                     self.new_pg_passwd)])

        for prompt, passwd in passwd_dict.iteritems():
            expects_cmds.append(self.get_expects_dict(prompt, passwd))

        stdout, stderr, rc = self.run_expects_command(
            self.ms_node, const.POSTGRES_PASSWORD_SCRIPT,
            expects_cmds, su_root=True)
        self.assertEqual(0, rc, "Return code was {0}".format(rc))
        self.assertEqual([], stderr, "Error encountered: {0}".format(stderr))
        self.assertEqual(['Password set'], stdout,
                         "{0} returned output: {1}".format(
                        const.POSTGRES_PASSWORD_SCRIPT, stdout))

        self.log(
            'info', "2. Waiting until the current puppet run "
            "and a subsequent one has completed")
        # Wait for puppet to trigger the password change.
        self.start_new_puppet_run(self.ms_node)
        self.wait_full_puppet_run(self.ms_node)

        self.log(
            'info', "3. Confirming that the 'pg_shadow' view "
            "has been updated with the new password hash.")
        password_hash_in_db = self.get_password_hash_from_db()
        self.assertEqual(password_hash_in_db, self.new_pg_passwd_hash,
                         "The 'pg_shadow' view has NOT been updated!")

        self.log(
            'info', "4. Confirming that no instances of the password "
            "have been logged.")
        msgs_to_check = [self.new_pg_passwd, self.new_pg_passwd_hash]
        for log_msg in msgs_to_check:
            self.assertFalse(self.check_for_log(self.ms_node,
                    log_msg, const.GEN_SYSTEM_LOG_PATH, self.start_pos),
                    "{0} was logged in {1}".format(log_msg,
                    const.GEN_SYSTEM_LOG_PATH))

    @attr('all', 'revert', 'Story289941', 'Story289941_tc16')
    def test_16_n_litpmsdbpwd_script_ownership_and_permissions(self):
        """
        @tms_id: torf_289941_tc_16
        @tms_requirements_id: TORF-289941
        @tms_title:
            Non-privileged user 'litpmsdbpwd' script execution (Neg).
        @tms_description:
            Verify that the 'litpmsdbpwd' script can not be
            executed by a non-privileged user. e.g. litp-admin
        @tms_test_steps:
            @step: Run the 'litpmsdbpwd' script on the MS as
                   litp-admin user.
            @result: The script does not execute and result
                     code 126 returned.
        @tms_test_precondition: n/a
        @tms_execution_type: Automated
        """

        self.log('info', "1. Running the 'litpmsdbpwd' script on"
            " the MS as litp-admin user.")
        _, stderr, rc = self.run_command(self.ms_node,
                            const.POSTGRES_PASSWORD_SCRIPT, "litp-admin")
        self.assertEqual(126, rc, "Return code was {0}".format(rc))
        self.assertTrue(
            self.is_text_in_list(
                "bash: /usr/bin/litpmsdbpwd: Permission denied", stderr),
            "The following error was encountered: {0}".format(stderr))
