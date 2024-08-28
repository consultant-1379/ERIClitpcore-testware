'''
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     Sept 2014
@author:    Adrian / Padraic
@summary:   Integration test for litp version commands
            Agile: LITPCDS-5295
'''
import re
from litp_generic_test import GenericTest, attr
import litp_cli_utils
import redhat_cmd_utils
import test_constants as const

LITP_GROUP = "LITP2"


class Story5295(GenericTest):
    '''
    As a LITP Architect I want the ERIClitpcore version used for versioning
    of the product so LITP core can have a separate development
    lifecycle to plugins.
    '''
    def setUp(self):
        """
        Description:
            Runs before every single test
        Actions:
            1. Call the super class setup method
            2. Set up variables used in the tests
        Results:
            The super class prints out diagnostics and variables
            common to all tests are available.
        """
        # 1. Call super class setup
        super(Story5295, self).setUp()
        self.ms_node = self.get_management_node_filename()
        self.cli = litp_cli_utils.CLIUtils()
        self.rhcmd = redhat_cmd_utils.RHCmdUtils()

    def tearDown(self):
        """run after every test"""
        super(Story5295, self).tearDown()

    def _run_cmd(self, cmd, add_to_cleanup=True, su_root=False,
                 expect_positive=True):
        """
        Run a command asserting success or error (returns: stdout / stderr)
        """
        stdout, stderr, exit_code = self.run_command(
            self.ms_node, cmd, add_to_cleanup=add_to_cleanup, su_root=su_root)
        if expect_positive:
            self.assertNotEqual([], stdout)
            self.assertEqual([], stderr)
            self.assertEqual(0, exit_code)
            result = '\n'.join(stdout)
        else:
            self.assertEqual([], stdout)
            self.assertNotEqual([], stderr)
            self.assertNotEqual(0, exit_code)
            result = '\n'.join(stderr)
        return result

    def _get_litp_packages(self):
        """
        Method to get list of installed LITP packages
        """
        litp_pkgs_cmd = self.rhcmd.get_yum_cmd("info 'ERIC*' 'EXTR*'")
        packages_strings = self._run_cmd(litp_pkgs_cmd).split('\n')
        # LITPCDS-8019 and LITPCDS-8103 fixes
        # the fixed bug was litp version -a returning all available LITP
        # packages, including those that haven't been installed. This was the
        # result of the core code also using the yum info command above. This
        # has been fixed so now litp version -a returns only installed LITP
        # packages. By getting the packages information, and only getting any
        # lines up to and before Available Packages string, we not can assert
        # that litp version -a packages are equal to installed LITP packages.
        not_installed_pkgs = -1
        for line in packages_strings:
            if 'Available Packages' in line:
                not_installed_pkgs = packages_strings.index(line)
        if not_installed_pkgs != -1:
            packages_strings = packages_strings[0:not_installed_pkgs - 1]
        # rest of test should remain the same
        package_list = list()
        for line in packages_strings:
            # initialise temporary variables for each new line
            package = list()
            pkg = ''
            vers = ''
            # if package name in output
            if 'Name        :' in line:
                line_indx = packages_strings.index(line)
                pkg = line.split(':')[-1].split('_CXP')[0].strip()
                # if version information two lines further
                if 'Version     :' in packages_strings[line_indx + 2]:
                    vers = \
                        packages_strings[line_indx + 2].split(':')[-1].strip()
            # if we have both the package name and version information
            if pkg and vers:
                package.append(pkg)
                package.append(vers)
            if package:
                package_list.append(package)

        return package_list

    def _get_litp_version(self):
        """
        Method to get litp installed version.
        """
        cmd = self.cli.get_litp_version_cmd()
        version_string = self._run_cmd(cmd).strip()
        parts = version_string.split()
        cannonical_version = parts[1]
        cxp_version = parts[2]
        return cannonical_version, cxp_version

    def _get_show_root(self):
        """
        Method to get version info from 'litp show -p /' command.
        """
        ver_str, err, ret_code = self.execute_cli_show_cmd(self.ms_node,
                                                       "/",
                                                       "| /bin/grep version")
        self.assertNotEqual([], ver_str)
        self.assertEqual([], err)
        self.assertEqual(0, ret_code)
        parts = ver_str[0].split()
        cannonical_version = parts[1]
        cxp_version = parts[2]

        return cannonical_version, cxp_version

    def _get_packages_version(self):
        """
        Method to get the version of all litp packages.
        """
        litp_version_cmd = self.cli.get_litp_version_cmd(args='-a')
        version_string = self._run_cmd(litp_version_cmd)
        parts = version_string.split('\n')
        packages = parts[2:]
        package_list = []
        for pkg in packages:
            package = pkg.strip().replace(':', '').split()
            package_list.append([package[0], package[1]])
        return package_list

    @attr('all', 'revert', 'story5295', 'story5295_tc01')
    def test_01_p_litp_version_yum(self):
        """
        @tms_id: litpcds_5295_tc01
        @tms_requirements_id: LITPCDS-5295
        @tms_title: litp version command shows correct ERIClitpcore version.
        @tms_description: This test will verify that when a user runs
            'litp version', the version which is displayed is the
            ERIClitpcore version.
        @tms_test_steps:
         @step: run litp version command and compare with version of litp core
            returned by yum info command
         @result: version is the same
        @tms_test_precondition: N/A
        @tms_execution_type: Automated
        """
        # 1. Get the version info from the litp version command
        version = self._get_litp_version()

        # 2. Get the installed version of ERICliptcore.
        installed_pkg = self._get_litp_packages()
        core_version = None
        for pkg in installed_pkg:
            if pkg[0] == 'ERIClitpcore':
                core_version = pkg[1]
                break

        # 3. Verify that the versions are the same.
        self.assertEqual(version[0], core_version)

    @attr('all', 'revert', 'story5295', 'story5295_tc02')
    def test_02_p_litp_all_cli_yum(self):
        """
        @tms_id: litpcds_5295_tc02
        @tms_requirements_id: LITPCDS-5295
        @tms_title: litp version -a command shows correct versions of all
            litp rpms
        @tms_description: This test will verify that when a user runs
            'litp version -a', the versions which are displayed are the
            correct versions of litp rpms.
        @tms_test_steps:
         @step: run litp version -a command and compare output with versions
            of litp related rpms (ERIC, EXTR) returned by yum info command
         @result: versions are the same
        @tms_test_precondition: N/A
        @tms_execution_type: Automated
        """

        # 1. Get the installed version of the litp packages using rpm.
        installed_pkg = self._get_litp_packages()

        # 2. Get the version info from the 'litp version -a' command.
        litp_version_all = self._get_packages_version()

        # 3. Verify that the versions are the same.
        self.assertEqual(sorted(installed_pkg), sorted(litp_version_all),
                         "rpm versions returned by litp version -a should be "
                         "identical as returned by yum info"
                         )

    @attr('all', 'revert', 'story5295', 'story5295_tc03')
    def test_03_p_litp_show_cli_yum(self):
        """
        @tms_id: litpcds_5295_tc03
        @tms_requirements_id: LITPCDS-5295
        @tms_title: litp root has "version" property containing core version
        @tms_description: This test will verify that when a user runs
            'litp show -p /' the version of ERIClitpcore is displayed.
        @tms_test_steps:
         @step: compare litp core version as returned by rpm command with
            "version" property from "litp show -p /" command
         @result: version is the same
        @tms_test_precondition: N/A
        @tms_execution_type: Automated
        """
        # 1. Get the version info of the installed core rpm.
        cmd = "{0} -qa ERIClitpcore*".format(const.RPM_PATH)
        out, _, _ = self.run_command(self.ms_node, cmd, su_root=True,
            default_asserts=True)
        installed_core_ver = out[0]

        # 2. Create expected string in model from installed core version.
        _, cxp_string, version, _ = re.split('[_-]', installed_core_ver)
        expected_ver_format = (version, cxp_string)

        # 3. Get the version information from the model root item.
        litp_show = self._get_show_root()

        # 4. Verify that the versions are the same.
        self.assertEqual(expected_ver_format, litp_show)

    @attr('all', 'revert', 'story5295', 'story5295_tc04')
    def test_04_p_no_show_install_info_property(self):
        """
        @tms_id: litpcds_5295_tc04
        @tms_requirements_id: LITPCDS-5295
        @tms_title: litp root has no "install info" property
        @tms_description: This test will verify that the "install info"
            property is not present when one runs litp show -p / -j command.
        @tms_test_steps:
         @step: run litp show -p / command
         @result: no "install info" property in output
         @step: run litp show -p / -j command
         @result: no "install info" property in json output
        @tms_test_precondition: N/A
        @tms_execution_type: Automated
        Result:
        """
        # 1. Verify that no install-info in output.
        out, err, ret_code = self.execute_cli_show_cmd(self.ms_node, "/")
        self.assertNotEqual([], out)
        self.assertEqual([], err)
        self.assertEqual(0, ret_code)
        self.assertFalse(self.is_text_in_list("install-info", out))

        # 2. Verify that no install-info in json output.
        out, err, ret_code = self.execute_cli_show_cmd(self.ms_node,
                                                       "/",
                                                       "-j",
                                                       load_json=False)
        self.assertNotEqual([], out)
        self.assertEqual([], err)
        self.assertEqual(0, ret_code)
        self.assertFalse(self.is_text_in_list("install-info", out))
