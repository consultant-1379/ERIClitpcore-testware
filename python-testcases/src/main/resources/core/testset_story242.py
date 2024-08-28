"""
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     September 2013
@author:    Luke Murphy
@summary:   Integration test to test REST authentication
            STORY-242
"""
from litp_generic_test import GenericTest, attr
from litp_cli_utils import CLIUtils
from redhat_cmd_utils import RHCmdUtils
from rest_utils import RestUtils


class Story242(GenericTest):
    """
    As a LITP user I want to authenticate for access
    to the REST API (locally stored username/password)
    """

    def setUp(self):
        """run before every test"""
        super(Story242, self).setUp()
        self.cli = CLIUtils()
        self.test_ms = self.get_management_node_filename()
        self.rhcmd = RHCmdUtils()
        self.uname = "litp_{0}".format(self.__class__.__name__)
        self.pword = "litpc0b6lEr"

    def tearDown(self):
        """run after every test"""
        super(Story242, self).tearDown()

    @attr('all', 'revert')
    def test_01_p_authenticate_cli_args(self):
        """
        @tms_id: litpcds_242_tc01
        @tms_requirements_id: LITPCDS-242
        @tms_title: Authenticate via CLI when user owns no ~/.litprc file
        @tms_description: Given a valid POSIX user on the MS, verify that
            the user can run a LITP CLI command when
            passing valid 'username' and 'password' via CLI to
            REST interface authentication
        @tms_test_steps:
         @step: run a LITP show passing username + password as CLI params
         @result: command executed successfully
        @tms_test_precondition: test user created that doesn't own a
            ~/.litprc file
        @tms_execution_type: Automated
        """
        self.log('info', 'create a test user and don\'t create '
                         'a litprc file for them')
        self.assertTrue(
            self.create_posix_usr(self.test_ms, self.uname, self.pword)
        )

        self.log('info', 'prepare a LITP show command that will pass'
                         ' username and password as CLI args')
        show_cmd = self.cli.add_creds_to_litp_cmd(
            self.cli.get_show_cmd("/"), username=self.uname,
            password=self.pword
        )

        self.log('info', 'run command and assert success')
        std_out, std_err, rcode = self.run_command(
            self.test_ms, show_cmd, username=self.uname, password=self.pword
        )
        self.assertNotEqual([], std_out)
        self.assertEqual([], std_err)
        self.assertEqual(0, rcode)

    #attr('all', 'revert')
    def obsolete_02_p_authenticate_litprc(self):
        """
        #tms_id: litpcds_242_tc02
        #tms_requirements_id: LITPCDS-242
        #tms_title: Authenticate when user owns a ~/.litprc file
        #tms_description: Given a valid POSIX user on the MS, verify that
            the user can run a LITP CLI command using
            information from the ~/.litprc
        #tms_test_steps:
         #step: run a LITP show without passing username + password
            as CLI params
         #result: command executed successfully
        #tms_test_precondition: test user created that owns a valid
            .litprc file
        #tms_execution_type: Automated
        """
        pass

    @attr('all', 'revert')
    def test_03_n_username_missing_arg(self):
        """
        @tms_id: litpcds_242_tc03
        @tms_requirements_id: LITPCDS-242
        @tms_title: User mustn't authenticate when no username submitted
        @tms_description: Given a valid POSIX user on the MS, verify that
            when running a LITP CLI command and passing the
            '-u' and '-P' flags but with the username parameter
            missing, that the std_err will prompt for missing username.
        @tms_test_steps:
         @step: run a LITP show passing no username, but a correct password
         @result: "--username: expected one argument" posted
        @tms_test_precondition: test user created that doesn't own a valid
            .litprc file
        @tms_execution_type: Automated
        """
        self.log('info', 'create a test user and don\'t create '
                         'any .litprc file for them')
        self.assertTrue(
            self.create_posix_usr(self.test_ms, self.uname, self.pword)
        )

        self.log('info', 'run LITP show passing an empty username and valid '
                         'password as CLI args')
        show_cmd = self.cli.add_creds_to_litp_cmd(
            self.cli.get_show_cmd("/"), "", self.pword
        )
        std_out, std_err, rcode = self.run_command(self.test_ms, show_cmd)

        self.log('info', 'assert missing username reported as error')
        self.assertTrue(
            self.is_text_in_list(
                "--username: expected one argument", std_err
            )
        )
        self.assertEqual([], std_out)
        self.assertNotEqual(0, rcode)

    @attr('all', 'revert')
    def test_04_n_pword_missing_arg(self):
        """
        @tms_id: litpcds_242_tc04
        @tms_requirements_id: LITPCDS-242
        @tms_title: User mustn't authenticate when no password submitted
        @tms_description: Given a valid POSIX user on the MS, verify that
            when running a LITP CLI command and passing the
            '-u' and '-P' flags but with the password parameter
            missing, that the std_err will prompt for missing password.
        @tms_test_steps:
         @step: run a LITP show passing no password, but a correct username
         @result: "--password: expected one argument" posted
        @tms_test_precondition: test user created that doesn't own a valid
            .litprc file
        @tms_execution_type: Automated
        """
        self.log('info', 'create a test user and don\'t create '
                         'any .litprc file for them')
        self.assertTrue(
            self.create_posix_usr(self.test_ms, self.uname, self.pword)
        )

        self.log('info', 'run LITP show passing username + empty string '
                         'for password')
        show_cmd = self.cli.add_creds_to_litp_cmd(
            self.cli.get_show_cmd("/"), self.uname, "", user_first=False
        )
        std_out, std_err, rcode = self.run_command(self.test_ms, show_cmd)

        self.log('info', 'assert missing password reported as error')
        self.assertTrue(
            self.is_text_in_list(
                "--password: expected one argument", std_err
            )
        )
        self.assertEqual([], std_out)
        self.assertNotEqual(0, rcode)

    @attr('all', 'revert')
    def test_05_p_prompt_to_authenticate(self):
        """
        @tms_id: litpcds_242_tc05
        @tms_requirements_id: LITPCDS-242
        @tms_title: Authenticate by manually submitting username and password
        @tms_description: Given a valid POSIX user on the MS, verify that
            the user can run a LITP CLI command without passing the
            password / username via CLI + not having a ~/.litprc will
            be prompted for password and username and can still run
            a successful command
        @tms_test_steps:
         @step: run a LITP show without passing username + password
         @result: user prompted to enter credentials
        @tms_test_precondition: test user created that doesn't own a valid
            .litprc file
        @tms_execution_type: Automated
        """
        self.log('info', 'create a test user and don\'t create '
                         'any .litprc file for them')
        self.assertTrue(
            self.create_posix_usr(self.test_ms, self.uname, self.pword)
        )

        self.log('info', 'run LITP show')
        show_cmd = self.cli.get_show_cmd("/")
        expects_cmds = [
            self.get_expects_dict("Username:", self.uname),
            self.get_expects_dict("Password:", self.pword)
        ]

        self.log('info', 'run expects to enter username and password')
        std_out, std_err, rcode = self.run_expects_command(
            self.test_ms, show_cmd, expects_cmds,
            username=self.uname, password=self.pword
        )
        self.assertNotEqual([], std_out)
        self.assertEqual([], std_err)
        self.assertEqual(0, rcode)

    @attr('all', 'revert')
    def test_06_n_invalid_cli_args(self):
        """
        @tms_id: litpcds_242_tc06
        @tms_requirements_id: LITPCDS-242
        @tms_title: Default user mustn't authenticate with
            invalid username or password
        @tms_description: Verify that the default user cannot run a LITP CLI
            command when passing invalid params via CLI
            to REST interface authentication
        @tms_test_steps:
         @step: run litp show command with default user name and invalid pass
         @result: Error 401: Unauthorized access
         @step: run litp show command with default user pass and invalid name
         @result: Error 401: Unauthorized access
        @tms_test_precondition: username and password of
            a default user available
        @tms_execution_type: Automated
        """
        self.log('info', 'get default user credentials')
        default_user = self.get_node_att(self.test_ms, "username")
        default_pword = self.get_node_att(self.test_ms, "password")

        self.log('info', 'build a show command with invalid username')
        invalid_uname_cmd = self.cli.add_creds_to_litp_cmd(
            self.cli.get_show_cmd("/"), "INVALID", default_pword
        )

        self.log('info', 'build a show command with invalid password')
        invalid_pword_cmd = self.cli.add_creds_to_litp_cmd(
            self.cli.get_show_cmd("/"), default_user, "INVALID"
        )

        self.log('info', 'run previously created commands and assert '
                         'unauthorized access message posted')
        for show_cmd in [invalid_uname_cmd, invalid_pword_cmd]:
            std_out, std_err, rcode = self.run_command(self.test_ms, show_cmd)
            self.assertEqual([], std_out)
            self.assertNotEqual([], std_err)
            self.assertNotEqual(0, rcode)

            self.assertTrue(
                self.is_text_in_list(
                    "Error 401: Unauthorized access",
                    std_err
                )
            )

    #attr('all', 'revert', 'runme')
    def obsolete_07_n_invalid_litprc_details(self):
        """
        #tms_id: litpcds_242_tc07
        #tms_requirements_id: LITPCDS-242
        #tms_title: User mustn't authenticate with invalid login information
            in his .litprc file
        #tms_description: Given a valid POSIX user on the MS, verify that
            the user cannot run a LITP CLI command when
            invalid login information is contained in it's
            ~/.litprc
        #tms_test_steps:
         #step: run litp -show command
         #result: Error 401: Unauthorized access
        #tms_test_precondition: test user created that own a .litprc file
            with invalid credentials
        #tms_execution_type: Automated
        """
        pass

    #attr('all', 'revert')
    def obsolete_08_n_malformed_litprc(self):
        """
        #tms_id: litpcds_242_tc08
        #tms_requirements_id: LITPCDS-242
        #tms_title: User mustn't authenticate with invalid format .litprc file
        #tms_description: Having incorrect information contained in a .litprc
            is validated to not allow authentication when not
            passing login information via CLI
        #tms_test_steps:
         #step: run litp -show command
         #result: Error 401: Unauthorized access
        #tms_test_precondition: test user created that owns a .litprc file
            with an invalid format.
        #tms_execution_type: Automated
        """
        pass

    @attr('all', 'revert')
    def test_09_p_valid_user_get(self):
        """
        @tms_id: litpcds_242_tc09
        @tms_requirements_id: LITPCDS-242
        @tms_title: User can authenticate via REST
        @tms_description: A new user that doesn't own a .litprc file
            should be able to run a successful REST GET request if correct
            credentials passed with request.
        @tms_test_steps:
         @step: Perform GET request on base REST url with correct credentials
         @result: REST response is success
        @tms_test_precondition: test user created with no .litprc file owned.
        @tms_execution_type: Automated
        """
        self.log('info', 'get ms ip address')
        ms_ip = self.get_node_att(self.test_ms, 'ipv4')
        self.assertNotEqual('', ms_ip)

        self.log('info', 'create a test user and don\'t create '
                         'any .litprc file for them')
        self.assertTrue(
            self.create_posix_usr(self.test_ms, self.uname, self.pword)
        )

        self.log('info', 'init RestUtils')
        rest = RestUtils(
            ms_ip, username=self.uname, password=self.pword
        )

        self.log('info', 'execute GET on REST base url '
                         'with correct credentials')
        std_out, std_err, rcode = rest.get("/")
        std_out_json, errors = rest.get_json_response(std_out)

        self.log('info', 'assert no errors returned')
        self.assertNotEqual("", std_out)
        self.assertEqual("", std_err)
        self.assertNotEqual(None, std_out_json)
        self.assertEqual([], errors)
        self.assertTrue(rest.is_status_success(rcode))

    @attr('all', 'revert')
    def test_10_n_invalid_user_get(self):
        """
        @tms_id: litpcds_242_tc10
        @tms_requirements_id: LITPCDS-242
        @tms_title: User must not authenticate via REST with invalid
            credentials
        @tms_description: A new user that doesn't own a .litprc file
            should not be able to run a successful REST GET request if
            incorrect credentials passed with request.
        @tms_test_steps:
         @step: Perform GET request on base REST url with correct credentials
         @result: REST returns 401 HTTP code
        @tms_test_precondition: N/A
        @tms_execution_type: Automated
        """
        self.log('info', 'get ms ip address')
        ms_ip = self.get_node_att(self.test_ms, 'ipv4')
        self.assertNotEqual('', ms_ip)

        self.log('info', 'init RestUtils')
        rest = RestUtils(
            ms_ip, username="INVALID_USER", password="INVALID_PWORD"
        )

        self.log('info', 'do GET on REST base url with incorrect credentials')
        std_out, std_err, rcode = rest.get("/")
        self.assertNotEqual("", std_out)
        self.assertEqual("", std_err)

        self.log('info', 'assert returned code is 401')
        self.assertEqual(rcode,
                         401,
                         'return code should be 401, actual: {0}'.format(
                             rcode)
                         )
