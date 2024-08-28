"""
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     June 2016
@author:    Maurizio
@summary:   TORF-124055
            As a LITP User I want the litpd service to trust localhost
            unconditionally, so that I don't have to use a password when
            I am locally connected
"""
from litp_generic_test import GenericTest, attr
from litp_cli_utils import CLIUtils
from rest_utils import RestUtils
from redhat_cmd_utils import RHCmdUtils
import test_constants as const
from ConfigParser import SafeConfigParser, NoOptionError
import os


class Story124055(GenericTest):
    """
    TORF-124055
        As a LITP User I want the litpd service to trust localhost
        unconditionally, so that I don't have to use a password when
        I am locally connected
    """
    def setUp(self):
        """runs before every test to perform required setup"""
        super(Story124055, self).setUp()
        self.ms1 = self.get_management_node_filename()
        self.rest = RestUtils(self.get_node_att(self.ms1, 'ipv4'))
        self.cli = CLIUtils()
        self.rhcmd = RHCmdUtils()
        self.litp_socket_group = ''

        self.users = {}
        self.users['root'] = {
            'backup_dir': '/tmp/root',
            'pswd': '@dm1nS3rv3r'
        }
        self.users['litp-admin'] = {
            'backup_dir': '/tmp/litp-admin',
            'pswd': 'litp_admin'
        }
        self.users['story124055'] = {
            'backup_dir': '/tmp/story124055',
            'pswd': 'litp-user'
        }

    def tearDown(self):
        """runs after every test to perform required cleanup/teardown"""
        self.log('info',
        'CUSTOMISED CLEANUP: Close all SSH connections')
        self.disconnect_all_nodes()

        self.log('info',
        'CUSTOMISED CLEANUP: Restore backed up files')
        self.restore_backup_files(self.ms1)

        super(Story124055, self).tearDown()

    def _parse_litp_socket_config(self, force_download=False):
        """
        Description:
            Parse the '/etc/litpd.conf' file to determine the configuration
            of the litp unix socket
        Returns:
            str, str, str, litp_socket_file_group, litp_socket_file,
                           litp_socket_allowed_groups
        """
        local_filepath = '/tmp/litpd.conf'
        if not os.path.exists(local_filepath) or force_download:
            self.download_file_from_node(
                                    self.ms1,
                                    remote_filepath=const.LITPD_CONF_FILE,
                                    local_filepath=local_filepath,
                                    root_copy=True)
        options = {
                'litp_socket_file_group': '',
                'litp_socket_file': '',
                'litp_socket_allowed_groups': []
            }
        scp = SafeConfigParser()
        scp.read(local_filepath)
        for option in options:
            try:
                value = scp.get('global', option).strip('"')
            except NoOptionError:
                value = ''
            if option == 'litp_socket_allowed_groups':
                options[option] = value.split(',')
            else:
                options[option] = value
        return options

    def _get_user_groups(self, user):
        """
        Description:
            Get the list of groups a user belong to
        Args:
            user (str): The user to check groups for
        Return:
            list, The list of group a user belong to
        """
        cmd = '/usr/bin/groups {0}'.format(user)
        stdout = self.run_command(self.ms1, cmd, default_asserts=True)[0][0]
        user_groups = ((stdout.split(': '))[1]).split(' ')
        return user_groups

    def _is_user_in_litp_socket_group(self, user, litp_socket_group):
        """
        Description:
            Determine the groups that are in both user group list
        Args:
            user (str): Linux user
            litp_socket_group (list): List of user defined in litpd.conf
        Return:
            list, The groups that the user belong to that are in the litp user
                  groups
        """
        user_groups = self._get_user_groups(user)
        if litp_socket_group in user_groups:
            return True
        return False

    def _add_user_to_group(self, user, group):
        """
        Description:
            Add the given user to the specified group
        Args:
            user (str): User name
            group (str): Group to include the user in
        """
        groups = self._get_user_groups(user)
        if group not in groups:
            cmd = '/usr/sbin/usermod -a -G {0} {1}'.format(group, user)
            self.run_command(self.ms1, cmd, su_root=True, default_asserts=True)
            # Make sure that new user configuration is used
            self.disconnect_all_nodes()

    def _remove_user_from_group(self, user, group):
        """
        Description:
            Remove given user from specified group
        Args:
            user (str): The user name
            group (str): Group to remove
        """
        groups = self._get_user_groups(user)
        if group in groups:
            groups.remove(group)
        cmd = '/usr/sbin/usermod -G {0} {1}'.format(','.join(groups), user)
        self.run_command(self.ms1, cmd, su_root=True, default_asserts=True)

    @attr('all', 'revert', 'Story124055', 'Story124055_tc01')
    def test_01_p_authenticated_user_can_run_litp_commands(self):
        """
        @tms_id:
            torf_124055_tc_01
        @tms_requirements_id: TORF-120612
        @tms_title:
            Any authenticated user can run litp command
        @tms_description:
            Verify that any authenticated user can run litp command.
            The following two authentication methods are covered by this
            test:
            - Local Trust Authentication
            - username and password credentials passed as CLI options
            Also verify that the authentication method persists over a litpd
            service restart.
            NOTE: Also verifies bug TORF-119672, TORF-124303 & TORF-124055
        @tms_test_steps:
        @step: Add "litp-admin" user to "litp_socket_file_group"
        @result: User added to group
        @step: Run litp command as "root" passing credentials as CLI
               arguments
        @result: Command executed successfully
        @step: Run litp command as "litp-admin" passing credentials as CLI
               arguments
        @result: Command executed successfully
        @step: Run litp command as "root" without passing credentials as CLI
               arguments
        @result: Command executed successfully
        @step: Run litp command as "litp-admin" without passing credentials
               as CLI arguments
        @result: Command executed successfully
        @step: Create a new user without adding it to the
               "litp_socket_file_group" group
        @result: User created successfully
        @step: Run litp command as the new user passing credentials as CLI
               arguments
        @result: Command executed successfully
        @step: Run litp command as the new user without passing credentials
               as CLI arguments
        @result: User is prompted for credentials
        @step: Enter username and password
        @result: Command executed successfully
        @step: Add new user to the "litp_socket_group"
        @result: User added successfully
        @step: Run litp command as the new user without passing credentials
               as CLI arguments
        @result: Command executed successfully
        @step: Run a command for each user without passing credential
               as CLI argument
        @result: Commands executed successfully
        @step: Restart "litpd" service
        @result: "litpd" service restarted successfully
        @step: Run a command for each user without passing credential
               as CLI argument
        @result: Commands executed successfully
        @tms_test_precondition:
            - litpd.conf file includes configuration of "litp_socket_file" and
              "litp_socket_file_group"
            - "litp_socket_file" exists on MS
            - Each existing user is not part of the "litp_socket_file_group"
        @tms_execution_type: Automated
        """
        # NOTE: using "litp show" command throughout the test with
        # the "-r" flag to verify that recursive authentication are
        # handled correctly
        self.log('info',
        '1. Get value of relevant config options from litpd.conf file')
        litpd_conf = self._parse_litp_socket_config(force_download=True)

        self.log('info',
        '2. Verify that a user can run litp command with "Local Trust"'
        ' enabled')

        self.log('info',
        '2.1. Assert preconditions')

        self.log('info',
        '2.1.1. Relevant litpd.conf file options are set')
        self.assertNotEqual('', litpd_conf['litp_socket_file_group'])
        self.assertNotEqual('', litpd_conf['litp_socket_file'])
        self.assertNotEqual([], litpd_conf['litp_socket_allowed_groups'])
        self.litp_socket_group = litpd_conf['litp_socket_file_group']

        self.log('info',
        '2.1.2. Unix litp socket file exists')
        cmd = '/usr/bin/test -e {0}'.format(litpd_conf['litp_socket_file'])
        self.run_command(self.ms1, cmd, su_root=True, default_asserts=True)

        self.log('info',
        '3. Verify credentials passed via CLI arguments are accepted')
        cmd = '/usr/bin/litp -u {0} -P {1} show -p /deployments -r -n 3'. \
              format('litp-admin', self.users['litp-admin']['pswd'])
        self.run_command(self.ms1,
                         cmd,
                         username='root',
                         password=self.users['root']['pswd'],
                         default_asserts=True)

        cmd = '/usr/bin/litp -u {0} -P {1} show -p /deployments -r -n 3'. \
              format('litp-admin', self.users['litp-admin']['pswd'])
        self.run_command(self.ms1,
                         cmd,
                         username='litp-admin',
                         password=self.users['litp-admin']['pswd'],
                         default_asserts=True)

        self.log('info',
        '3.1. Verify that commands can be run without passing credentials '
             'via CLI arguments')
        self.execute_cli_show_cmd(self.ms1,
                                  '/deployments',
                                  username='root',
                                  password=self.users['root']['pswd'],
                                  args='-r -n 3')

        self.execute_cli_show_cmd(self.ms1,
                                  '/deployments',
                                  username='litp-admin',
                                  password=self.users['litp-admin']['pswd'],
                                  args='-r -n 3')

        self.log('info',
        '4. Verify that a new user with no automatic authentication mechanism '
            'enabled can run litp command providing credentials explicitly')

        self.log('info',
        '4.1 Create a new user without adding it to the "litp-access" group ')
        self.create_posix_usr(self.ms1,
                              'story124055',
                              password=self.users['story124055']['pswd'])

        self.log('info',
        '4.2. Verify credentials passed via CLI arguments are accepted')
        cmd = '/usr/bin/litp -u {0} -P {1} show -p /deployments -r -n 3'. \
              format('story124055', self.users['story124055']['pswd'])
        self.run_command(self.ms1,
                         cmd,
                         username='story124055',
                         password=self.users['story124055']['pswd'],
                         default_asserts=True)

        self.log('info',
        '4.3 verify that a litp command completes if correct username and '
            'password are provided when prompted')
        expects_list = list()
        expects_list.append(self.get_expects_dict("Username:",
                                                  'story124055'))
        expects_list.append(self.get_expects_dict(
                                        "Password:",
                                        self.users['story124055']['pswd']))

        cmd = self.cli.get_show_cmd('/deployments', args='-r -n 3')
        self.run_expects_command(self.ms1,
                                 cmd,
                                 expects_list=expects_list,
                                 username='story124055',
                                 password=self.users['story124055']['pswd'])

        self.log('info',
        '5. Verify that a new user with only "Local Trust" authentication '
            'mechanism enabled can run litp command without providing '
            'credentials explicitly')
        self._add_user_to_group('story124055', self.litp_socket_group)

        cmd = self.cli.get_show_cmd('/deployments', args='-r -n 3')
        self.run_expects_command(self.ms1,
                                 cmd,
                                 expects_list=expects_list,
                                 username='story124055',
                                 password=self.users['story124055']['pswd'])

        self.log('info',
        '6. Assert that user authentication configuration persists over '
           '"litpd" service restart')
        for user in self.users:
            self.execute_cli_show_cmd(self.ms1,
                                      '/deployments',
                                      username=user,
                                      password=self.users[user]['pswd'],
                                      args='-r -n 3')

        self.restart_litpd_service(self.ms1, debug_on=True)

        for user in self.users:
            self.execute_cli_show_cmd(self.ms1,
                                      '/deployments',
                                      username=user,
                                      password=self.users[user]['pswd'],
                                      args='-r -n 3')

    @attr('all', 'revert', 'Story124055', 'Story124055_tc02')
    def test_02_n_non_authenticated_user_cannot_run_litp_commands(self):
        """
        @tms_id:
            torf_124055_tc_02
        @tms_requirements_id: TORF-120612
        @tms_title:
            User not in "litp_socket_file_group" cannot run litp commands
        @tms_description:
            Verify that user with no ".litprc" file or that is not part of the
            "litp_socket_file_group" group cannot run litp commands
            NOTE: Also verifies bug TORF-119672 & TORF-124055
        @tms_test_steps:
        @step: Create a new user without ".litprc" file and without adding it
               to the "litp_socket_file_group"
        @result: user created successfully
        @step: Enter a "litp show" command
        @result: User is prompted for username and password
        @step: Enter a wrong password
        @result: The "Error 401: Unauthorized access" error is thrown
        @step: Enter "litp show" command passing username and wrong password as
               arguments
        @result: The "Error 401: Unauthorized access" error is thrown
        @tms_test_precondition:
            - litpd.conf file includes configuration of "litp_socket_file" and
              "litp_socket_file_group"
            - "litp_socket_file" exists on MS
        @tms_execution_type: Automated
        """
        self.log('info',
        '1. Get value of relevant config options from litpd.conf file')
        litpd_conf = self._parse_litp_socket_config(force_download=True)
        self.assertNotEqual('', litpd_conf['litp_socket_file_group'])
        self.assertNotEqual('', litpd_conf['litp_socket_file'])
        self.assertNotEqual([], litpd_conf['litp_socket_allowed_groups'])
        self.litp_socket_group = litpd_conf['litp_socket_file_group']

        self.log('info',
        '2. Assert that the unix litp socket file exists')
        cmd = '/usr/bin/test -e {0}'.format(litpd_conf['litp_socket_file'])
        self.run_command(self.ms1, cmd, su_root=True, default_asserts=True)

        self.log('info',
        '3. Create a new user')
        self.create_posix_usr(self.ms1,
                              'story124055',
                              password=self.users['story124055']['pswd'])

        self.log('info',
        '4. Enter the "litp show" command as the new user and supply wrong '
           'password when prompted')
        expects_list = list()
        expects_list.append(self.get_expects_dict("Username:",
                                                  'story124055'))
        expects_list.append(self.get_expects_dict("Password:",
                                                  'wrong_password'))

        cmd = self.cli.get_show_cmd('/deployments', args='-r -n 3')
        stdout, _, _ = self.run_expects_command(
                                self.ms1,
                                cmd,
                                expects_list=expects_list,
                                username='story124055',
                                password=self.users['story124055']['pswd'])

        expected_errors = ['Error 401: Unauthorized access']
        self.assertEqual(expected_errors, stdout)

        self.log('info',
        '5. Enter "litp show" command with -u and -P arguments as the '
           'new user')
        cmd = '/usr/bin/litp -u {0} -P {1} show -p /deployments -r -n 3'. \
              format('story124055', 'wrong_password')
        _, stderr, _ = self.run_command(
                            self.ms1,
                            cmd,
                            username='story124055',
                            password=self.users['story124055']['pswd'])

        expected_errors = ['Error 401: Unauthorized access']
        self.assertEqual(expected_errors, stderr)

    @attr('all', 'revert', 'Story124055', 'Story124055_tc03')
    def test_03_p_verify_unix_socket_is_used(self):
        """
        @tms_id:
            torf_124055_tc_03
        @tms_requirements_id: TORF-120612
        @tms_title:
            Unix socket authentication works when port TCP on 9999 is disabled
        @tms_description:
            Unix socket authentication works when port TCP on 9999 is disabled
            NOTE: Also verifies bug TORF-119672 & TORF-124055 TORF-120612
        @tms_test_steps:
        @step: Change the port used by "litpd" in the litpd.conf file
        @result: File edited successfully
        @step: Restart litpd to reload new configuration file
        @result: litpd restarted successfully
        @step: Run the litp show command as litp-admin
        @result: Command executed successfully
        @tms_test_precondition:
            - litpd.conf file includes configuration of "litp_socket_file" and
              "litp_socket_file_group"
            - "litp_socket_file" exists on MS
        @tms_execution_type: Automated
        """
        self.log('info',
        '1. Get value of relevant config options from litpd.conf file')
        litpd_conf = self._parse_litp_socket_config(force_download=True)

        self.assertNotEqual('', litpd_conf['litp_socket_file_group'])
        self.assertNotEqual('', litpd_conf['litp_socket_file'])
        self.assertNotEqual([], litpd_conf['litp_socket_allowed_groups'])
        self.litp_socket_group = litpd_conf['litp_socket_file_group']

        self.log('info',
        '2. Assert that the "litp_socket_file" exists')
        cmd = '/usr/bin/test -e {0}'.format(litpd_conf['litp_socket_file'])
        self.run_command(self.ms1, cmd, su_root=True, default_asserts=True)

        self.log('info',
        '3. Make sure "litp show" command works')
        self.execute_cli_show_cmd(self.ms1,
                                  '/deployments',
                                  username='litp-admin',
                                  password=self.users['litp-admin']['pswd'],
                                  args='-r -n 3',
                                  expect_positive=True)

        self._add_user_to_group('litp-admin', self.litp_socket_group)

        try:
            self.log('info',
            '4. Change the port used by "litpd"')
            cmd = self.rhcmd.get_replace_str_in_file_cmd(
                                                    '9999',
                                                    '9998',
                                                     const.LITPD_CONF_FILE,
                                                     sed_args='-i')
            self.run_command(self.ms1, cmd, default_asserts=True, su_root=True)

            self.restart_litpd_service(self.ms1, debug_on=True)

            self.disconnect_all_nodes()

            self.log('info',
            '5. Run the litp show command as litp-admin')
            self.execute_cli_show_cmd(
                            self.ms1,
                            '/deployments',
                            username='litp-admin',
                            password=self.users['litp-admin']['pswd'],
                            args='-r -n 3',
                            expect_positive=True)
        finally:
            self.log('info',
            'FINALLY: Ensure litpd listens on port 9999')
            cmd = self.rhcmd.get_replace_str_in_file_cmd(
                                                    '9998',
                                                    '9999',
                                                     const.LITPD_CONF_FILE,
                                                     sed_args='-i')
            self.run_command(self.ms1, cmd, su_root=True, default_asserts=True)

            self.restart_litpd_service(self.ms1, debug_on=True)

            self.disconnect_all_nodes()

    @attr('all', 'revert', 'Story124055', 'Story124055_tc04')
    def test_04_n_unix_socket_auth_with_litp_maintenance_enabled(self):
        """
        @tms_id:
            torf_124055_tc_04
        @tms_requirements_id: TORF-120612
        @tms_title:
            The presence of unix socket authentication method does not affect
            the litp maintenance mode
        @tms_description:
            The presence of unix socket authentication method does not affect
            the litp maintenance mode
        NOTE: Also verifies TORF-124055 TORF-120612
        @tms_test_steps:
        @step: Enable litp maintenance mode
        @result: Maintenance mode enabled successfully
        @step: Attempt to run a "litp show" command
        @result: A "ServerUnavailableError" error is thrown
        @tms_test_precondition:
            - litpd.conf file includes configuration of "litp_socket_file" and
              "litp_socket_file_group"
            - "litp_socket_file" exists on MS
        @tms_execution_type: Automated
        """
        self.log('info',
        '1. Get value of relevant config options from litpd.conf file')
        litpd_conf = self._parse_litp_socket_config(force_download=True)
        self.assertNotEqual('', litpd_conf['litp_socket_file_group'])
        self.assertNotEqual('', litpd_conf['litp_socket_file'])
        self.assertNotEqual([], litpd_conf['litp_socket_allowed_groups'])
        self.litp_socket_group = litpd_conf['litp_socket_file_group']

        self.log('info',
        '2. Assert that the "litp_socket_file" exists')
        cmd = '/usr/bin/test -e {0}'.format(litpd_conf['litp_socket_file'])
        self.run_command(self.ms1, cmd, su_root=True, default_asserts=True)

        self._add_user_to_group('litp-admin', self.litp_socket_group)

        try:
            self.log('info',
            '3. Enable litp maintenance mode')
            self.execute_cli_update_cmd(self.ms1,
                                        '/litp/maintenance',
                                        props='enabled=true')

            self.log('info',
            '4. Attempt to run a "litp show" command')
            _, stderr, _ = self.execute_cli_show_cmd(self.ms1,
                                                     '/deployments',
                                                     args='-r -n 3',
                                                     expect_positive=False)
            expected_error = {
                'error_type': 'ServerUnavailableError',
                'msg': '    LITP is in maintenance mode'
            }
            missing, extra = self.check_cli_errors([expected_error], stderr)
            self.assertEqual([], missing)
            self.assertEqual([], extra)

        finally:
            self.log('info',
            'FINALLY: disable litp maintenance mode')
            self.execute_cli_update_cmd(self.ms1,
                                        '/litp/maintenance',
                                        props='enabled=false')

    @attr('all', 'revert', 'Story124055', 'Story124055_tc05')
    def test_05_p_disable_unix_socket_authentication(self):
        """
        @tms_id:
            torf_124055_tc_05
        @tms_requirements_id: TORF-120612
        @tms_title:
            Verify that unix socket authentication method can be disabled
        @tms_description:
            Verify that if the line
                "litp_socket_file: "/var/run/litpd/litpd.sock"
            is commented out in the litp.conf file and the file
                "/var/run/litpd/litpd.sock"
            is manually removed the unix socket authentication method is
            disabled
        NOTE: Also verifies TORF-124055
        @tms_test_steps:
        @step: Edit file "litpd.conf" to disable unix socket, remove file
               "/var/run/litpd/litpd.sock" and restart litpd
        @result: unix socket removed from litpd.confg, unix file removed
                 and litpd restarted successfully
        @step: Attempt to run a command as litp-admin providing credentials
        @result: Command executed successfully
        @step: Run a "litp show" command using socket authentication (no
               credenitals provided)
        @result: Command fails
        @step: Restore litpd.conf
        @result: litpd.conf restored
        @tms_test_precondition:
            - litpd.conf file includes configuration of "litp_socket_file" and
              "litp_socket_file_group"
            - "litp_socket_file" exists on MS
        @tms_execution_type: Automated
        """
        self.log('info',
        '1. Get value of relevant config options from litpd.conf file')
        litpd_conf = self._parse_litp_socket_config(force_download=True)
        self.assertNotEqual('', litpd_conf['litp_socket_file_group'])
        self.assertNotEqual('', litpd_conf['litp_socket_file'])
        self.assertNotEqual([], litpd_conf['litp_socket_allowed_groups'])
        self.litp_socket_group = litpd_conf['litp_socket_file_group']

        self.log('info',
        '2. Assert that the "litp_socket_file" exists')
        cmd = '/usr/bin/test -e {0}'.format(litpd_conf['litp_socket_file'])
        self.run_command(self.ms1, cmd, su_root=True, default_asserts=True)

        self.litp_socket_group = litpd_conf['litp_socket_file_group']

        try:
            self.log('info',
            '3. Disable unix socket authentication mode')
            cmd = self.rhcmd.get_replace_str_in_file_cmd(
                                                    'litp_socket_file:',
                                                    '#litp_socket_file:',
                                                     const.LITPD_CONF_FILE,
                                                     sed_args='-i')
            self.run_command(self.ms1, cmd, default_asserts=True, su_root=True)

            self.remove_item(self.ms1,
                             litpd_conf['litp_socket_file'],
                             su_root=True)

            self.restart_litpd_service(self.ms1, debug_on=False)

            self.log('info',
            'Turn on litp-debug and assert that user can still authenticate '
            'by passing credentials')

            cmd = '/usr/bin/litp -u {0} -P {1} ' \
                  'update -p /litp/logging -o force_debug=true'. \
                  format('litp-admin', self.users['litp-admin']['pswd'])
            self.run_command(self.ms1,
                             cmd,
                             username='litp-admin',
                             password=self.users['litp-admin']['pswd'],
                             default_asserts=True)

            self.log('info',
            '4. Assert that unix socket authentication does not work')
            _, _, rc = self.execute_cli_show_cmd(self.ms1,
                                                 '/deployments',
                                                 args='-r -n 3',
                                                 expect_positive=False)
            self.assertEqual(1, rc)

        finally:
            self.log('info',
            'FINALLY. Restore litpd.conf file of litp-admin')
            cmd = self.rhcmd.get_replace_str_in_file_cmd(
                                                    '#litp_socket_file:',
                                                    'litp_socket_file:',
                                                     const.LITPD_CONF_FILE,
                                                     sed_args='-i')
            self.run_command(self.ms1, cmd, default_asserts=True, su_root=True)

            self.restart_litpd_service(self.ms1, debug_on=True)
