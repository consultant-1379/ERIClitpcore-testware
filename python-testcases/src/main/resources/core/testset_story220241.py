'''
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     February 2018
@author:    Bryan McNulty
@summary:   TORF-220241
            As a LITP user I want increased logging of the PostgreSQL DB on
            the MS to enable diagnosis of security incidents (DTAG Item 46)
'''
import test_constants as const
from litp_generic_test import GenericTest, attr
import re


class Story220241(GenericTest):
    """
    TORF-220241:
        A test on the logging configuration on the PostgreSQL DB on the MS.
        connections, connection attempts and disconnections should be logged.
    """
    def setUp(self):
        """runs before every test to perform required setup"""
        super(Story220241, self).setUp()
        self.ms_node = self.get_management_node_filename()
        self.sed_cmd_partial = "{0} -n -e '{1}, {2}p' -e '{2} q' {3}"
        self.conn_recieved_log_str = "LOG:  connection received: host=ms1"

    def tearDown(self):
        """runs after every test to perform required cleanup/teardown"""
        super(Story220241, self).tearDown()

    def _set_force_postgres_debug(self, force_postgres_debug):
        """
        Set the value of postgres logging by changing the value for
         force_postgres_debug and then restart puppet to apply the change.
        """
        self.log('info', 'updating force_postgres_debug to be {0}'.format(
            force_postgres_debug))
        self.execute_cli_update_cmd(
            self.ms_node, "/litp/logging",
            "force_postgres_debug={0}".format(
                force_postgres_debug))
        self.restart_service(self.ms_node, "puppet", su_root=True)
        self.wait_full_puppet_run(self.ms_node)

    def _test_line_for_valid_time(self, line):
        """
        Asserts that the line provided has a timestamp in the line. Timestamp
        should be in the format "Mon dd hh:mm:ss" or "Mon  d hh:dd:ss".

        Args:
            line (str): The line that will be checked.
        """
        pattern = re.compile(r"\b(?:Jan|Feb|Mar|Apr|May|Jun"\
            r"|Jul|Aug|Sep|Oct|Nov|Dec?)((\s{1}[1-3]\d)|(\s{2}"\
            r"\d{1}))\s(\b([0-1][0-9]|[2][0-3]):[0-5][0-9]:[0-5][0-9])")
        self.assertTrue(re.match(pattern, line), "There is no valid"
            " timestamp in the supplied string.")

    def _assert_line_in_logs(self, expected_line, log_excerpt):
        """
        Asserts that the log excerpt from /var/log/messages contains the
        expected line.

        Args:
            expected_line (str): This line is expected in the log & will be
            checked for.

            log_excerpt (list): This is the excerpt of logs in list format.
        """
        log_not_found_msg = '"{0}" not found in {1} as expected.'.format(
            expected_line, const.GEN_SYSTEM_LOG_PATH)
        line_found = False
        self.log('info', 'log_excerpt: {0} '.format(log_excerpt))
        for line in log_excerpt:
            if expected_line in line:
                line_found = True
                self.log('info', '"{0}" found in {1} as expected.'.format(
                    expected_line, log_excerpt))
        self.assertTrue(line_found, log_not_found_msg)

    @attr('all', 'revert', 'Story220241', 'Story220241_tc01')
    def test_01_n_postgres_logging_unsuccessful_connections(self):
        """
        @tms_id: TORF-220241_tc01
        @tms_requirements_id: TORF-220241
        @tms_title: Verify when an unsuccessful connection attempt is made to
            the postgresql DB, then connection attempt logs are added to
            /var/log/messages on the MS.
        @tms_description: Verify when unsuccessful connection attempt is made
            to the postgresql DB, then connection attempt logs are added to
            /var/log/messages on the MS. This logging includes the timestamp,
            the hostname from which the connection attempt originates, username
            and the database being accessed.
        @tms_test_steps:
            @step:  Using root user, attempt to connect to the postgres db.
            @result:  Connection is unsuccessful.
            @step:  Search in /var/log/messages logs on the MS for connection
                attempt.
            @result:  Logging related to the failed connection includes
                the timestamp, hostname, username and the database.
        @tms_test_precondition: None
        @tms_execution_type: Automated
        """
        # For the logs to appear in /var/log/messages we need to enable
        #  logging first, as it will be set to disabled by default.
        self._set_force_postgres_debug("true")
        db_name = 'litpcelery'
        db_user = 'postgres'
        self.log('info', ' 1. Find the {0} file\'s position at the start'
            ' of the test.'.format(const.GEN_SYSTEM_LOG_PATH))
        pos_1 = self.get_file_len(
            self.ms_node, const.GEN_SYSTEM_LOG_PATH)

        self.log('info', ' 2. Unsuccessfully attempt to connect to the'
            ' postgresql db {0} with the database user {1} as root'
            ' user.'.format(db_name, db_user))
        cmd = "{0} -U {1} -h ms1 -d {2}".format(const.PSQL_PATH, db_user,
            db_name)
        self.log('info', ' 2b. cmd:{0}'.format(cmd))
        _, std_err, rc = self.run_command(
                self.ms_node, cmd, su_root=True)
        self.assertEqual(std_err, [])
        self.assertNotEqual(rc, 0)

        self.log('info', " 3. Find the {0} file's position at the end of"
            " connection attempt.".format(const.GEN_SYSTEM_LOG_PATH))
        pos_2 = self.get_file_len(
            self.ms_node, const.GEN_SYSTEM_LOG_PATH)

        self.log('info', ' 4. Find the data between start & end of test '
            'in {0} file.'.format(const.GEN_SYSTEM_LOG_PATH))
        sed_cmd = self.sed_cmd_partial.format(const.SED_PATH, pos_1 + 1,
            pos_2, const.GEN_SYSTEM_LOG_PATH)
        std_out, _, _ = self.run_command(
                self.ms_node, sed_cmd, su_root=True, default_asserts=True)

        self.log('info', ' 5. Check that each line from the retrieved logs'
            ' has a validly formatted timestamp.')
        for line in std_out:
            self._test_line_for_valid_time(line)

        self.log('info', ' 6. Check that expected log lines for a failed'
                ' connection to the postgresql db are in {0}.'
                .format(const.GEN_SYSTEM_LOG_PATH))
        unames_no_match_log_str = "LOG:  provided user name ({0}) and"\
                " authenticated user name (litp) do not match".format(db_user)
        ident_fail_log_str = "FATAL:  certificate authentication failed for "\
                             'user "{0}"'.format(db_user)
        self._assert_line_in_logs(self.conn_recieved_log_str, std_out)
        self._assert_line_in_logs(unames_no_match_log_str, std_out)
        self._assert_line_in_logs(ident_fail_log_str, std_out)
        self._set_force_postgres_debug("false")

    @attr('all', 'revert', 'Story220241', 'Story220241_tc02')
    def test_02_p_postgres_logging_successful_connection(self):
        """
        @tms_id: TORF-220241_tc02
        @tms_requirements_id: TORF-220241
        @tms_title: Verify when a successful connection to the postgresql db
            is made, the correct logs are added to /var/log/messages taken on
            connection and upon disconnection.
        @tms_description: Verify when a successful connection is made to
            the postgresql DB, that the correct logs are taken & added to
            /var/log/messages on connection and upon disconnection. Logging
            includes the timestamp, the hostname from which the connection
            attempt originates, username and the database being accessed.
        @tms_test_steps:
            @step:  Connect to the postgres db as the postgres user then
            disconnect from the db.
            @result:  Connection and disconnection are successful.
            @step:  Observe /var/log/messages logs for connection and
                disconnection.
            @result:  Logging includes the timestamp, hostname, username
                and the database being accessed.
        @tms_test_precondition: None
        @tms_execution_type: Automated
        """
        self._set_force_postgres_debug("true")
        db_name = db_user = 'postgres'

        self.log('info', ' 1. Find the {0} file\'s position at the start of'
            ' the test.'.format(const.GEN_SYSTEM_LOG_PATH))
        pos_1 = self.get_file_len(
            self.ms_node, const.GEN_SYSTEM_LOG_PATH)

        self.log('info', ' 2. Connect to the postgresql db then disconnect'
            ' as postgres user.')
        postgres_cmd = "{0} -h ms1 -U {1} -d {2} -c".format(const.PSQL_PATH,
            db_user, db_name)
        cmd = "{0} - postgres -c \"{1} ".format(const.SU_PATH, postgres_cmd)
        cmd += r"'\q'"\
            "\" "
        self.run_command(self.ms_node, cmd, su_root=True,
            default_asserts=True)

        self.log('info', " 3. Find the {0} file's position at the end of"
            " the connection.".format(const.GEN_SYSTEM_LOG_PATH))
        pos_2 = self.get_file_len(
            self.ms_node, const.GEN_SYSTEM_LOG_PATH)

        self.log('info', ' 4. Retrieve the data between start & end of test'
            ' in the {0} file.'.format(const.GEN_SYSTEM_LOG_PATH))
        sed_cmd = self.sed_cmd_partial.format(const.SED_PATH, pos_1 + 1,
            pos_2, const.GEN_SYSTEM_LOG_PATH)
        std_out, _, _ = self.run_command(
                self.ms_node, sed_cmd, su_root=True, default_asserts=True)

        self.log('info', ' 5. Check that each line from the retrieved logs,'
            ' contains a validly formatted timestamp.')
        for line in std_out:
            self._test_line_for_valid_time(line)

        self.log('info', ' 6. Check that expected lines for connection &'\
            ' disconnection to the postgres DB are in the retrieved logs.')
        connection_auth_log_str = "LOG:  connection authorized: user={0} "\
            "database={1}".format(db_user, db_name)
        disconn_log_str_1 = "LOG:  disconnection:"
        disconn_log_str_2 = "user={0} database={1} host=ms1".format(
            db_user, db_name)
        self._assert_line_in_logs(self.conn_recieved_log_str, std_out)
        self._assert_line_in_logs(connection_auth_log_str, std_out)
        self._assert_line_in_logs(disconn_log_str_1, std_out)
        self._assert_line_in_logs(disconn_log_str_2, std_out)
        self._set_force_postgres_debug("false")

    @attr('all', 'revert', 'Story220241', 'Story220241_tc09')
    def test_09_p_postgres_conf_file_logging_settings(self):
        """
        @tms_id: TORF-220241_tc09
        @tms_requirements_id: TORF-220241
        @tms_title: Verify that the postgres conf file has the correct logging
            settings set.
        @tms_description: Verify that the postgres conf file has the
            following settings enabled 'log_destination=syslog',
            'log_connections=on', 'log_disconnections=on', 'log_hostname=on'.
        @tms_test_steps:
            @step:  Access MS file postgresql.conf
            @result:  The following settings are enabled
                'log_destination=syslog', 'log_connections=on',
                'log_disconnections=on', 'log_hostname=on'.
        @tms_test_precondition: None
        @tms_execution_type: Automated
        """
        self._set_force_postgres_debug("true")
        try:
            log_settings_list = [
                    'log_destination=syslog',
                    'log_connections=on',
                    'log_disconnections=on',
                    'log_hostname=on']
            postgres_conf_list = []

            self.log('info', ' 1. Grep lines in {0} excluding blank and lines'
                             ' beginning with hash.'.format(
                                const.PSQL_9_6_CONF_FILE))
            cmd = "{0} -vxE '[[:blank:]]*([#;].*)?' {1} ".format(
                const.GREP_PATH, const.PSQL_9_6_CONF_FILE)
            std_out, _, _ = self.run_command(self.ms_node, cmd, su_root=True,
                default_asserts=True)

            self.log('info', ' 2. Remove hashed comments from partially hashed'
                             ' lines. Remove spaces & tabs.')
            for line in std_out:
                new_line = line.split("#")[0]
                new_line = "".join(new_line.split())
                postgres_conf_list.extend([new_line])

            self.log('info', ' 3. Assert that the desired configuration'
                             ' settings are in the conf file contents.')
            for log_setting in log_settings_list:
                self.assertTrue(log_setting in postgres_conf_list, "The {0}"\
                    " file is not as expected.".format(
                    const.PSQL_9_6_CONF_FILE))
        finally:
            self._set_force_postgres_debug("false")
