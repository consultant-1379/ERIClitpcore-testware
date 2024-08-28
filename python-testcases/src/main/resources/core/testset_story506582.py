"""
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     May 2021
@author:    Philip Daly
@summary:   As an LITP User,
            I want to update the version of Server JRE8 in
            LITP to the latest version (N)
"""
from litp_generic_test import GenericTest, attr
from litp_cli_utils import CLIUtils
from redhat_cmd_utils import RHCmdUtils
from pkg_resources import parse_version
import test_constants
import re
import time

"""
This code currently needs to be executed against a LITP HW environment due to
the JRE version not being upgraded on the nodes on a LITP Vapp.

The LITP iso's need to be placed on the MS in the following directory:
/software/LITP

THe required LITP iso files are listed in the file:
README_for_TORF-506582.txt

"""


class Story506582(GenericTest):
    """
    As an LITP User, I want to update the version
    of Server JRE8 in LITP to the latest version (N)
    """
    def setUp(self):
        """
        Description:
            Runs before every single test
        Actions:
            Determine
                management server,
                primary vcs node(first node in array
                                 returned from test framework)
                list of all managed nodes
        Results:
            Class variables that are required to execute tests
        """
        # 1. Call super class setup
        super(Story506582, self).setUp()

        self.cli = CLIUtils()
        self.rh_os = RHCmdUtils()
        self.management_server = self.get_management_node_filename()
        self.managed_nodes = self.get_managed_node_filenames()
        self.all_nodes = []
        self.all_nodes.extend(self.managed_nodes)
        self.all_nodes.append(self.management_server)
        self.java_version_cmd = test_constants.JAVA_PATH + " -version"
        self.litp_software_dir = "/software/LITP"
        self.mount_path = "/mnt"
        self.iso_mount_path = "{0}/litp".format(self.mount_path)
        self.litp_iso_name_format = "ERIClitp_CXP9024296-{0}.iso"
        self.deployment_url = self.find(self.management_server,
                                         '/deployments', 'deployment')[-1]

        # THESE VALUES SHOULD BE UPDATED TO REFLECT THE LATEST VERSION
        self.litp_iso_to_version = "2.133.2"
        self.java_to_version = "1.8.0_291"

    def tearDown(self):
        """
        Description:
            Runs after every single test
            This function just calls the super class function
        Actions:
            -
        Results:
            The super class prints out diagnostics and variables
        """
        super(Story506582, self).tearDown()

    def get_java_version(self, node):
        """
        Description:
            Retrieve the java version from the node.

        Args:
            node (str): name of the node on which to
                        retrieve java.

        Returns:
            list. stdout
        """
        stdout, _, _ =\
            self.run_command(node, self.java_version_cmd, su_root=True)
        return stdout

    def get_java_process_status(self, node):
        """
        Description:
            Retrieve the status of a java process on the node.

        Args:
            node (str): name of the node on which to
                        retrieve the java process status.

        Returns:
            list, list, int. Results of whether the Java process
                             was found in the ps -ef output,
                             any errors which were reported,
                             and the return code from the cmd execution.
        """
        ps_java_cmd = \
            self.rh_os.get_ps_cmd(
            '-ef | {0} java | {0} -v {0}'.format(self.rh_os.grep_path)
                                 )

        return self.run_command(node,
                             ps_java_cmd,
                             su_root=True)

    def verify_java_process(self, node_list):
        """
        Description:
            Verify the java process is running on the ms and nodes.

        Args:
            node_list (list): list of the node on which to
                              verify the java version.
        """
        no_process_nodes = []
        for node in node_list:
            _, _, rcode = \
                self.get_java_process_status(node)
            if rcode:
                no_process_nodes.append(node)
        self.assertEqual([], no_process_nodes,
                         "The java process was found to not " \
                         "be running on these nodes: {0}".format(
                         " ".join(no_process_nodes)
                                                                 )
                        )

    def verify_java_version(self, node_list, version):
        """
        Description:
            Verify the java version installed on the node is the expected.

        Args:
            node_list (list): list of the node on which to
                              verify the java version.
            version (str): version of java expected.
        """
        incorrect_version_nodes = {}
        for node in node_list:
            stdout = \
                self.get_java_version(node)
            if "java version \"{0}\"".format(version) not in stdout:
                if "-bash: {0}: No such file or " \
                   "directory".format(test_constants.JAVA_PATH) in stdout:
                    incorrect_version_nodes[node] = None
                else:
                    version_string = \
                        [line for line in stdout
                         if 'java version' in line][0].split("\"")[1]
                    incorrect_version_nodes[node] = version_string
        self.assertEqual({}, incorrect_version_nodes)

    def get_litp_software_dir_contents(self):
        """
        Description:
            Retrieve the contents of the LITP software
            directory from the MS.
        Returns:
            list. Contents of the LITP software directory
        """
        stdout, _, _ = \
        self.run_command(self.management_server,
                         "{0} {1}".format(test_constants.LS_PATH,
                                          self.litp_software_dir),
                         default_asserts=True, su_root=True)
        return stdout

    def verify_litp_software_in_dir(self, litp_iso_version):
        """
        Description:
            Verify that the specified LITP iso is present in the
            LITP software directory.

        Args:
            litp_iso_version (str): Name of the LITP iso expected
                                    to reside in the directory.
        """
        specific_litp_iso = \
            self.litp_iso_name_format.format(litp_iso_version)
        stdout = \
            self.get_litp_software_dir_contents()
        stdout = [element for entry in stdout for element in entry.split()]
        self.assertTrue(specific_litp_iso in stdout,
                        "The required LITP iso {0} was " \
                        "not found in {1}".format(
                        specific_litp_iso, self.litp_software_dir)
                                                 )

    def get_litp_version_installed(self):
        """
        Description:
            Retrieve RSTATE of the version of LITP installed.
        Returns:
            str. The RSTATE of the LITP version installed.
        """
        version_cmd = self.cli.get_litp_version_cmd()
        stdout, _, _ = \
            self.run_command(self.management_server,
                             version_cmd,
                             default_asserts=True, su_root=True)
        return stdout[0].strip().split(' ')[3]

    def compare_litp_versions(self, litp_version_installed,
                              expected_litp_version):
        """
        Description:
            Compare the RSTATE of the installed LITP version
            with that of the expected RSTATE.

        Args:
            litp_version_installed (str): Installed LITP
                                          version info.
            expected_litp_version (str): Expected LITP
                                         version info.

        Returns:
            str. int. Explanation, return code.
        """
        inst_rstate_chars = \
            re.split(r'(\d+)', litp_version_installed)
        exptd_rstate_chars = \
            re.split(r'(\d+)', expected_litp_version)

        if int(inst_rstate_chars[1]) > int(exptd_rstate_chars[1]):
            return "Later version of LITP installed than expected.", 1
        elif int(inst_rstate_chars[1]) == int(exptd_rstate_chars[1]):
            if inst_rstate_chars[2] != exptd_rstate_chars[2]:
                inst_rstate_chars = \
                    self.rstate_chars_to_nums(inst_rstate_chars[2])

                exptd_rstate_nums = \
                    self.rstate_chars_to_nums(exptd_rstate_chars[2])

                if inst_rstate_chars > exptd_rstate_nums:
                    return "Later version of LITP installed than expected.", 1
                elif inst_rstate_chars < exptd_rstate_nums:
                    return "Earlier version of LITP installed than expected", 2
                else:
                    if int(inst_rstate_chars[3]) < int(exptd_rstate_chars[3]):
                        return "Earlier version of LITP " \
                               "installed than expected", 2
                    else:
                        return "Later version of LITP " \
                               "installed than expected.", 1
        else:
            return "Earlier version of LITP " \
                   "installed than expected", 2

    def rstate_chars_to_nums(self, rstate_alpha_characters):
        """
        Description:
            Convert the RSTATE characters to numeric values
            for comparison.

        Args:
            rstate_alpha_characters (str): Alpha chars from
                                           the RSTATE.

        Returns:
            float. Numeric value of the RSTATE.
        """
        alpha_to_numeric_dict = \
        {"A": "01",
         "B": "02",
         "C": "03",
         "D": "04",
         "E": "05",
         "F": "06",
         "G": "07",
         "H": "08",
         "I": "09",
         "J": "10",
         "K": "11",
         "L": "12",
         "M": "13",
         "N": "14",
         "O": "15",
         "P": "16",
         "Q": "17",
         "R": "18",
         "S": "19",
         "T": "20",
         "U": "21",
         "V": "22",
         "W": "23",
         "X": "24",
         "Y": "25",
         "Z": "26"}

        if len(rstate_alpha_characters) == 1:
            return alpha_to_numeric_dict[rstate_alpha_characters]
        else:
            self.assertFalse(len(rstate_alpha_characters) > 2,
                             "The subsequent casting to a float will " \
                             "break if more that three " \
                             "letters are in the RSTATE.")
            long_version = ""
            for element in rstate_alpha_characters:
                if long_version == "":
                    long_version = alpha_to_numeric_dict[element]
                else:
                    long_version = \
                        "{0}.{1}".format(long_version,
                                         alpha_to_numeric_dict[element])
            return float(long_version)

    def verify_litp_version_installed(self, expected_litp_version):
        """
        Description:
            Verify that the LITP version installed is the expected.

        Args:
            expected_litp_version (str): LITP version expected to be
                                         installed.

        Returns:
            str. int. Check report and return code.
        """
        litp_version_installed = \
            self.get_litp_version_installed()
        if litp_version_installed == expected_litp_version:
            return "LITP version is as expected.", 0
        else:
            return self.compare_litp_versions(litp_version_installed,
                                              expected_litp_version)

    def upgrade_litp(self, litp_iso):
        """
        Description:
            Upgrade LITP and reboot the MS post upgrade.

        Args:
            litp_iso (str): The To-state LITP version.
        """
        # Check for existence of mount directory, if not found create it.
        stdout, _, _ = \
            self.run_command(self.management_server,
                             "{0} {1}".format(test_constants.LS_PATH,
                                              self.mount_path),
                                              su_root=True)
        if 'litp' in stdout:
            # check mount
            stdout, _, _ = \
            self.run_command(self.management_server,
                             "{0} {1}".format(test_constants.MOUNT_PATH,
                                 self.iso_mount_path),
                             default_asserts=False, su_root=True)
            if re.search(r'already mounted', stdout[0]):
                self.run_command(self.management_server,
                                 "{0} {1}".format(test_constants.UMOUNT_PATH,
                                     self.iso_mount_path
                                                 ),
                                 default_asserts=True, su_root=True
                                 )

            self.run_command(self.management_server,
                             "{0} {1} {2}".format(
                                 test_constants.MOUNT_PATH,
                                 " -o loop {0}/{1}".format(
                                     self.litp_software_dir,
                                     self.litp_iso_name_format.format(litp_iso)
                                                          ),
                                 self.iso_mount_path),
                             default_asserts=True, su_root=True)
        else:
            # make directory
            self.create_dir_on_node(self.management_server,
                                    self.iso_mount_path, su_root=True)
            # Mount the desired iso at this path.
            self.run_command(self.management_server,
                             "{0} {1} {2}".format(
                                 test_constants.MOUNT_PATH,
                                 " -o loop {0}/{1}".format(
                                      self.litp_software_dir,
                                      self.litp_iso_name_format.format(
                                          litp_iso
                                                                      )
                                                          ),
                                 self.iso_mount_path
                                                 ),
                             default_asserts=True, su_root=True)

        self.execute_cli_import_iso_cmd(self.management_server,
                                        self.iso_mount_path)
        # Loop until LITP has completed importing all
        # of the iso packages and exited maintenance mode.
        litp_in_mmode = True
        counter = 40
        while litp_in_mmode:
            time.sleep(30)
            litp_in_mmode = self._litp_in_mmode()
            counter = counter - 1
            if counter == 0:
                self.assertTrue(False,
                                "Maintenance mode counter has expired.")

        # Wait for LITP to restart
        litp_in_mmode = True
        counter = 10
        while litp_in_mmode:
            time.sleep(30)
            litp_in_mmode = self._litp_in_mmode(False)
            counter = counter - 1
            if counter == 0:
                self.assertTrue(False, "Maintenance mode counter has expired.")

        # Upgrade the LITP Deployment
        self.execute_cli_upgrade_cmd(self.management_server,
                                     self.deployment_url)
        # Tasks may or may not be generated.
        create_plan_cmd = self.cli.get_create_plan_cmd()
        _, stderr, _ = \
            self.run_command(self.management_server,
                             create_plan_cmd,
                             default_asserts=False
                            )
        if "DoNothingPlanError    Create plan failed: " \
           "no tasks were generated" not in stderr:
            self.execute_cli_runplan_cmd(self.management_server)
            self.assertTrue(self.wait_for_plan_state(
                                self.management_server,
                                test_constants.PLAN_COMPLETE,
                                timeout_mins=30)
                           )

        # Restart the MS so that the key services will
        # update to use the latest JRE.
        # In ENM Server JRE updates are delivered with OS Patch updates
        # so an MS reboot will take place for that reason.
        # Here we need to manually reboot.
        self.log('info', 'Reboot MS so key services will use latest JRE.')
        self.run_command(self.management_server,
                         test_constants.REBOOT_PATH,
                         su_root=True)

        # Wait for the MS node to become unreachable
        ms_ip = self.get_node_att(self.management_server, 'ipv4')
        self.assertTrue(self.wait_for_ping(ms_ip, False, 40),
                        "Node has not gone down")

        self.log('info', 'MS has gone down')
        # Wipe active SSH connections to force a reconnect
        self.disconnect_all_nodes()

        # Wait for MS to be reachable again after reboot
        self.assertTrue(self.wait_for_node_up(self.management_server,
                                              wait_for_litp=True))

        # Turn on debug logging.
        self.turn_on_litp_debug(self.management_server)

    def _litp_in_mmode(self, mmode_expected=True):
        """
        Description:
            Determine if litp is in maintenance mode.
        Args:
            mmode_expected (bool): Whether maintenance mode is expected.
        Returns:
            int. return code.
        """
        show_cmd = self.cli.get_show_cmd("/")
        _, err, rcode = self.run_command(self.management_server, show_cmd)
        exp_err = ["ServerUnavailableError    LITP is in maintenance mode"]
        if mmode_expected:
            return err == exp_err
        else:
            return rcode

    def verify_java_installed_from_repo(self):
        """
        Description:
            Ensures that the Server JRE installed derived from the
            packages located in the repository.
        """
        package = "EXTRserverjre_CXP9035480-"
        self.assertTrue(self.check_pkgs_installed(self.management_server,
                        [package]),
                        "package {0} not installed on {1}"
                        .format(package, self.management_server))

        self.log("info", "# 1. Determine package version from the "
                             "repo")

        cmd = "{0} {1}/{2}*"\
            .format(test_constants.LS_PATH,
                    test_constants.PP_PKG_REPO_DIR,
                    package)
        rpms_in_repo, _, _ = \
            self.run_command(self.management_server,
                             cmd,
                             default_asserts=True)
        # Determine latest RPM. Linux does not list in order
        # ie Linux ordered 1.16.3 before 1.5.7.
        # [:-4] is there to trim '.rpm' from the name as
        # not all rpm's have trailing '-' characters after the
        # version number.
        versions = \
        [version[:-4].split('-')[1] for version in rpms_in_repo]
        parsed_versions = \
        [parse_version(version) for version in versions]
        version_dict = {}

        iterator = 0
        counter = len(parsed_versions)
        while iterator < counter:
            version_dict[parsed_versions[iterator]] = versions[iterator]
            iterator += 1
        parsed_versions.sort()
        latest_version = version_dict[parsed_versions[-1]]
        cmd = "{0} {1}/{2}*"\
            .format(test_constants.LS_PATH,
                    test_constants.PP_PKG_REPO_DIR,
                    package + latest_version)
        rpm_in_repo, _, _ = \
            self.run_command(self.management_server,
                             cmd,
                             default_asserts=True)

        self.log("info", "# 2. Get java version from package")

        cmd = "{0} -qlp {1} | {2} -F'/' '{{print $4}}' | " \
              "head -n 1 | {3} 's/[a-z]*//'"\
            .format(test_constants.RPM_PATH,
                    rpm_in_repo[0],
                    test_constants.AWK_PATH,
                    test_constants.SED_PATH)

        package_java_version, _, _ = \
            self.run_command(self.management_server,
                             cmd,
                             default_asserts=True)
        package_java_version = ''.join(package_java_version)

        # Some versions have appended suffixes in their
        # package name which are not reflected in the
        # java version reported, so need to be trimmed
        # eg. 1.8.0_212_tz in package vs just
        # 1.8.0_212 returned by java -version command.
        split_pkg = package_java_version.split('_')
        package_java_version = \
            "{0}_{1}".format(split_pkg[0], split_pkg[1])
        ms_java_version = self._get_ms_java_version()
        self.assertEquals(ms_java_version, package_java_version,
                          "Java version {0} does not match package "
                          "version {1}".format(ms_java_version,
                                               package_java_version))

    def verify_key_services_have_updated_to_use_latest_jre(self,
                                 exclude_puppetserver=False
                                                           ):
        """
        Description:
            Ensures that the key services have updated to
            use the latests JRE version.

        Args:
            exclude_puppetserver (bool): Flag on whether to check if
                                         puppetserver is using latest
                                         java. In earlier versions of
                                         LITP the PID for puppetserver
                                         changes too frequently for it
                                         to be checked.
        """
        services = ["puppetdb"]
        if not exclude_puppetserver:
            services.append("puppetserver")
        ms_java_version = self._get_ms_java_version()

        for service in services:
            self.log("info",
                     "# 1. Determine pid for processes running in jvm")

            # The PID changes so frequently that it needs to be identified
            # and checked within one command.
            cmd = "pid=$({0} -ef | {1} {2} | {1} -v postgres | head -n 1 " \
                  "| {3} '{{ print $2 }}'); {4} -p $pid | {1} jdk | {3} " \
                  "'{{ print $9 }}' | head -n 1".format(test_constants.PS_PATH,
                                                  test_constants.GREP_PATH,
                                                  service,
                                                  test_constants.AWK_PATH,
                                                  test_constants.LSOF_PATH)

            service_java_path, _, _ = \
                self.run_command(self.management_server,
                                 cmd,
                                 default_asserts=True,
                                 su_root=True)
            self.assertNotEqual(service_java_path, [],
                                "No path found")
            self.assertTrue(self.is_text_in_list(ms_java_version,
                                                 service_java_path),
                            "Java version {0} does" \
                            "not match {1}".format(
                                                   service_java_path,
                                                   ms_java_version)
                           )

    def _get_ms_java_version(self):
        """
        Description:
            Get the running java version on ms
        Returns:
            String, Java version
        """
        cmd = "{0} -version 2>&1 | head -n 1 | {1} -F '\"' " \
              "'{{ print $2 }}'".format(test_constants.JAVA_PATH,
                                        test_constants.AWK_PATH)

        running_java_version, _, _ = \
            self.run_command(self.management_server,
                             cmd,
                             default_asserts=True)
        java_version = ''.join(running_java_version)

        return java_version

    @attr('manual-test')
    def test_01_p_upgrade_8u202_to_latest_jre(self):
        """
        @tms_id: TORF-506582_tc1
        @tms_requirements_id: TORF-506582
        @tms_title: Upgrade LITP for serverJRE upgrade from 8u202 to latest.
        @tms_description:
         To ensure that the upgrade of LITP from serverJRE version 8u202
         to a LITP version containing the laster serverJRE
         version is successful.
        @tms_test_steps:
        @step: Verify that the LITP From & To state iso's are present.
        @result: The iso's are present.
        @step: Verify that the LITP installed version is as expected.
               If not then upgrade LITP and reboot the MS.
        @result: LITP is, or is upgraded to, the expected From-state.
        @step: Verify the Server JRE version.
        @result: The JRE version is verified.
        @step: Verify the Server JRE version installed on the MS
               was derived from the repository.
        @result: The JRE version is verified as being from the repo.
        @step: Verify the java process is running
        @result: The java process is running
        @step: Verify key services are using the latest installed JRE.
        @result: The key services are verified.
        @step: A snapshot is created and LITP is upgrade to the To-state.
        @result: LITP is upgraded to the To-state.
        @step: Verify the Server JRE version.
        @result: The JRE version is verified.
        @step: Verify the Server JRE version installed on the MS
               was derived from the repository.
        @result: The JRE version is verified as being from the repo.
        @step: Verify the java process is running
        @result: The java process is running
        @step: Verify key services are using the latest installed JRE.
        @result: The key services are verified.
        @step: Restore the snapshot.
        @result: The snapshot is restored.
        @step: Verify the Server JRE version.
        @result: The JRE version is verified.
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        expected_litp_version = "R1DF04"
        litp_iso_from_version = "2.99.3"
        java_from_version = "1.8.0_202"
        self.execute_java_upgrade_procedure(expected_litp_version,
                                            litp_iso_from_version,
                                            java_from_version,
                                            exclude_puppetserver=True)

    @attr('manual-test')
    def test_02_p_upgrade_8u212_to_latest_jre(self):
        """
        @tms_id: TORF-506582_tc2
        @tms_requirements_id: TORF-506582
        @tms_title: Upgrade LITP for serverJRE upgrade from 8u212 to latest.
        @tms_description:
         To ensure that the upgrade of LITP from serverJRE version 8u212
         to a LITP version containing the laster serverJRE
         version is successful.
        @tms_test_steps:
        @step: Verify that the LITP From & To state iso's are present.
        @result: The iso's are present.
        @step: Verify that the LITP installed version is as expected.
               If not then upgrade LITP and reboot the MS.
        @result: LITP is, or is upgraded to, the expected From-state.
        @step: Verify the Server JRE version.
        @result: The JRE version is verified.
        @step: Verify the Server JRE version installed on the MS
               was derived from the repository.
        @result: The JRE version is verified as being from the repo.
        @step: Verify the java process is running
        @result: The java process is running
        @step: Verify key services are using the latest installed JRE.
        @result: The key services are verified.
        @step: A snapshot is created and LITP is upgrade to the To-state.
        @result: LITP is upgraded to the To-state.
        @step: Verify the Server JRE version.
        @result: The JRE version is verified.
        @step: Verify the Server JRE version installed on the MS
               was derived from the repository.
        @result: The JRE version is verified as being from the repo.
        @step: Verify the java process is running
        @result: The java process is running
        @step: Verify key services are using the latest installed JRE.
        @result: The key services are verified.
        @step: Restore the snapshot.
        @result: The snapshot is restored.
        @step: Verify the Server JRE version.
        @result: The JRE version is verified.
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        expected_litp_version = "R1DG01"
        litp_iso_from_version = "2.100.5"
        java_from_version = "1.8.0_212"
        self.execute_java_upgrade_procedure(expected_litp_version,
                                            litp_iso_from_version,
                                            java_from_version,
                                            exclude_puppetserver=True)

    @attr('manual-test')
    def test_03_p_upgrade_8u212tz_to_latest_jre(self):
        """
        @tms_id: TORF-506582_tc3
        @tms_requirements_id: TORF-506582
        @tms_title: Upgrade LITP for serverJRE upgrade from 8u212tz to latest.
        @tms_description:
         To ensure that the upgrade of LITP from serverJRE version 8u212tz
         to a LITP version containing the laster serverJRE
         version is successful.
        @tms_test_steps:
        @step: Verify that the LITP From & To state iso's are present.
        @result: The iso's are present.
        @step: Verify that the LITP installed version is as expected.
               If not then upgrade LITP and reboot the MS.
        @result: LITP is, or is upgraded to, the expected From-state.
        @step: Verify the Server JRE version.
        @result: The JRE version is verified.
        @step: Verify the Server JRE version installed on the MS
               was derived from the repository.
        @result: The JRE version is verified as being from the repo.
        @step: Verify the java process is running
        @result: The java process is running
        @step: Verify key services are using the latest installed JRE.
        @result: The key services are verified.
        @step: A snapshot is created and LITP is upgrade to the To-state.
        @result: LITP is upgraded to the To-state.
        @step: Verify the Server JRE version.
        @result: The JRE version is verified.
        @step: Verify the Server JRE version installed on the MS
               was derived from the repository.
        @result: The JRE version is verified as being from the repo.
        @step: Verify the java process is running
        @result: The java process is running
        @step: Verify key services are using the latest installed JRE.
        @result: The key services are verified.
        @step: Restore the snapshot.
        @result: The snapshot is restored.
        @step: Verify the Server JRE version.
        @result: The JRE version is verified.
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        expected_litp_version = "R1DH05"
        litp_iso_from_version = "2.102.7"
        java_from_version = "1.8.0_212"
        self.execute_java_upgrade_procedure(expected_litp_version,
                                            litp_iso_from_version,
                                            java_from_version,
                                            exclude_puppetserver=True)

    @attr('manual-test')
    def test_04_p_upgrade_8u221_to_latest_jre(self):
        """
        @tms_id: TORF-506582_tc4
        @tms_requirements_id: TORF-506582
        @tms_title: Upgrade LITP for serverJRE upgrade from 8u221 to latest.
        @tms_description:
         To ensure that the upgrade of LITP from serverJRE version 8u221
         to a LITP version containing the laster serverJRE
         version is successful.
        @tms_test_steps:
        @step: Verify that the LITP From & To state iso's are present.
        @result: The iso's are present.
        @step: Verify that the LITP installed version is as expected.
               If not then upgrade LITP and reboot the MS.
        @result: LITP is, or is upgraded to, the expected From-state.
        @step: Verify the Server JRE version.
        @result: The JRE version is verified.
        @step: Verify the Server JRE version installed on the MS
               was derived from the repository.
        @result: The JRE version is verified as being from the repo.
        @step: Verify the java process is running
        @result: The java process is running
        @step: Verify key services are using the latest installed JRE.
        @result: The key services are verified.
        @step: A snapshot is created and LITP is upgrade to the To-state.
        @result: LITP is upgraded to the To-state.
        @step: Verify the Server JRE version.
        @result: The JRE version is verified.
        @step: Verify the Server JRE version installed on the MS
               was derived from the repository.
        @result: The JRE version is verified as being from the repo.
        @step: Verify the java process is running
        @result: The java process is running
        @step: Verify key services are using the latest installed JRE.
        @result: The key services are verified.
        @step: Restore the snapshot.
        @result: The snapshot is restored.
        @step: Verify the Server JRE version.
        @result: The JRE version is verified.
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        expected_litp_version = "R1DJ03"
        litp_iso_from_version = "2.104.12"
        java_from_version = "1.8.0_221"
        self.execute_java_upgrade_procedure(expected_litp_version,
                                            litp_iso_from_version,
                                            java_from_version,
                                            exclude_puppetserver=True)

    @attr('manual-test')
    def test_05_p_upgrade_8u231_to_latest_jre(self):
        """
        @tms_id: TORF-506582_tc5
        @tms_requirements_id: TORF-506582
        @tms_title: Upgrade LITP for serverJRE upgrade from 8u231 to latest.
        @tms_description:
         To ensure that the upgrade of LITP from serverJRE version 8u231
         to a LITP version containing the laster serverJRE
         version is successful.
        @tms_test_steps:
        @step: Verify that the LITP From & To state iso's are present.
        @result: The iso's are present.
        @step: Verify that the LITP installed version is as expected.
               If not then upgrade LITP and reboot the MS.
        @result: LITP is, or is upgraded to, the expected From-state.
        @step: Verify the Server JRE version.
        @result: The JRE version is verified.
        @step: Verify the Server JRE version installed on the MS
               was derived from the repository.
        @result: The JRE version is verified as being from the repo.
        @step: Verify the java process is running
        @result: The java process is running
        @step: Verify key services are using the latest installed JRE.
        @result: The key services are verified.
        @step: A snapshot is created and LITP is upgrade to the To-state.
        @result: LITP is upgraded to the To-state.
        @step: Verify the Server JRE version.
        @result: The JRE version is verified.
        @step: Verify the Server JRE version installed on the MS
               was derived from the repository.
        @result: The JRE version is verified as being from the repo.
        @step: Verify the java process is running
        @result: The java process is running
        @step: Verify key services are using the latest installed JRE.
        @result: The key services are verified.
        @step: Restore the snapshot.
        @result: The snapshot is restored.
        @step: Verify the Server JRE version.
        @result: The JRE version is verified.
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        expected_litp_version = "R1DS02"
        litp_iso_from_version = "2.109.9"
        java_from_version = "1.8.0_231"
        self.execute_java_upgrade_procedure(expected_litp_version,
                                            litp_iso_from_version,
                                            java_from_version,
                                            exclude_puppetserver=True)

    @attr('manual-test')
    def test_06_p_upgrade_8u241_to_latest_jre(self):
        """
        @tms_id: TORF-506582_tc6
        @tms_requirements_id: TORF-506582
        @tms_title: Upgrade LITP for serverJRE upgrade from 8u241 to latest.
        @tms_description:
         To ensure that the upgrade of LITP from serverJRE version 8u241
         to a LITP version containing the laster serverJRE
         version is successful.
        @tms_test_steps:
        @step: Verify that the LITP From & To state iso's are present.
        @result: The iso's are present.
        @step: Verify that the LITP installed version is as expected.
               If not then upgrade LITP and reboot the MS.
        @result: LITP is, or is upgraded to, the expected From-state.
        @step: Verify the Server JRE version.
        @result: The JRE version is verified.
        @step: Verify the Server JRE version installed on the MS
               was derived from the repository.
        @result: The JRE version is verified as being from the repo.
        @step: Verify the java process is running
        @result: The java process is running
        @step: Verify key services are using the latest installed JRE.
        @result: The key services are verified.
        @step: A snapshot is created and LITP is upgrade to the To-state.
        @result: LITP is upgraded to the To-state.
        @step: Verify the Server JRE version.
        @result: The JRE version is verified.
        @step: Verify the Server JRE version installed on the MS
               was derived from the repository.
        @result: The JRE version is verified as being from the repo.
        @step: Verify the java process is running
        @result: The java process is running
        @step: Verify key services are using the latest installed JRE.
        @result: The key services are verified.
        @step: Restore the snapshot.
        @result: The snapshot is restored.
        @step: Verify the Server JRE version.
        @result: The JRE version is verified.
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        expected_litp_version = "R1DS02"
        litp_iso_from_version = "2.113.5"
        java_from_version = "1.8.0_241"
        self.execute_java_upgrade_procedure(expected_litp_version,
                                            litp_iso_from_version,
                                            java_from_version,
                                            force_litp_upgrade=True)

    @attr('manual-test')
    def test_07_p_upgrade_8u251_to_latest_jre(self):
        """
        @tms_id: TORF-506582_tc7
        @tms_requirements_id: TORF-506582
        @tms_title: Upgrade LITP for serverJRE upgrade from 8u251 to latest.
        @tms_description:
         To ensure that the upgrade of LITP from serverJRE version 8u251
         to a LITP version containing the laster serverJRE
         version is successful.
        @tms_test_steps:
        @step: Verify that the LITP From & To state iso's are present.
        @result: The iso's are present.
        @step: Verify that the LITP installed version is as expected.
               If not then upgrade LITP and reboot the MS.
        @result: LITP is, or is upgraded to, the expected From-state.
        @step: Verify the Server JRE version.
        @result: The JRE version is verified.
        @step: Verify the Server JRE version installed on the MS
               was derived from the repository.
        @result: The JRE version is verified as being from the repo.
        @step: Verify the java process is running
        @result: The java process is running
        @step: Verify key services are using the latest installed JRE.
        @result: The key services are verified.
        @step: A snapshot is created and LITP is upgrade to the To-state.
        @result: LITP is upgraded to the To-state.
        @step: Verify the Server JRE version.
        @result: The JRE version is verified.
        @step: Verify the Server JRE version installed on the MS
               was derived from the repository.
        @result: The JRE version is verified as being from the repo.
        @step: Verify the java process is running
        @result: The java process is running
        @step: Verify key services are using the latest installed JRE.
        @result: The key services are verified.
        @step: Restore the snapshot.
        @result: The snapshot is restored.
        @step: Verify the Server JRE version.
        @result: The JRE version is verified.
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        expected_litp_version = "R1DU01"
        litp_iso_from_version = "2.117.5"
        java_from_version = "1.8.0_251"
        self.execute_java_upgrade_procedure(expected_litp_version,
                                            litp_iso_from_version,
                                            java_from_version)

    @attr('manual-test')
    def test_08_p_upgrade_8u261_to_latest_jre(self):
        """
        @tms_id: TORF-506582_tc8
        @tms_requirements_id: TORF-506582
        @tms_title: Upgrade LITP for serverJRE upgrade from 8u261 to latest.
        @tms_description:
         To ensure that the upgrade of LITP from serverJRE version 8u261
         to a LITP version containing the laster serverJRE
         version is successful.
        @tms_test_steps:
        @step: Verify that the LITP From & To state iso's are present.
        @result: The iso's are present.
        @step: Verify that the LITP installed version is as expected.
               If not then upgrade LITP and reboot the MS.
        @result: LITP is, or is upgraded to, the expected From-state.
        @step: Verify the Server JRE version.
        @result: The JRE version is verified.
        @step: Verify the Server JRE version installed on the MS
               was derived from the repository.
        @result: The JRE version is verified as being from the repo.
        @step: Verify the java process is running
        @result: The java process is running
        @step: Verify key services are using the latest installed JRE.
        @result: The key services are verified.
        @step: A snapshot is created and LITP is upgrade to the To-state.
        @result: LITP is upgraded to the To-state.
        @step: Verify the Server JRE version.
        @result: The JRE version is verified.
        @step: Verify the Server JRE version installed on the MS
               was derived from the repository.
        @result: The JRE version is verified as being from the repo.
        @step: Verify the java process is running
        @result: The java process is running
        @step: Verify key services are using the latest installed JRE.
        @result: The key services are verified.
        @step: Restore the snapshot.
        @result: The snapshot is restored.
        @step: Verify the Server JRE version.
        @result: The JRE version is verified.
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        expected_litp_version = "R1DV01"
        litp_iso_from_version = "2.121.3"
        java_from_version = "1.8.0_261"
        self.execute_java_upgrade_procedure(expected_litp_version,
                                            litp_iso_from_version,
                                            java_from_version)

    @attr('manual-test')
    def test_09_p_upgrade_8u281_to_latest_jre(self):
        """
        @tms_id: TORF-506582_tc9
        @tms_requirements_id: TORF-506582
        @tms_title: Upgrade LITP for serverJRE upgrade from 8u281 to latest.
        @tms_description:
         To ensure that the upgrade of LITP from serverJRE version 8u281
         to a LITP version containing the laster serverJRE
         version is successful.
        @tms_test_steps:
        @step: Verify that the LITP From & To state iso's are present.
        @result: The iso's are present.
        @step: Verify that the LITP installed version is as expected.
               If not then upgrade LITP and reboot the MS.
        @result: LITP is, or is upgraded to, the expected From-state.
        @step: Verify the Server JRE version.
        @result: The JRE version is verified.
        @step: Verify the Server JRE version installed on the MS
               was derived from the repository.
        @result: The JRE version is verified as being from the repo.
        @step: Verify the java process is running
        @result: The java process is running
        @step: Verify key services are using the latest installed JRE.
        @result: The key services are verified.
        @step: A snapshot is created and LITP is upgrade to the To-state.
        @result: LITP is upgraded to the To-state.
        @step: Verify the Server JRE version.
        @result: The JRE version is verified.
        @step: Verify the Server JRE version installed on the MS
               was derived from the repository.
        @result: The JRE version is verified as being from the repo.
        @step: Verify the java process is running
        @result: The java process is running
        @step: Verify key services are using the latest installed JRE.
        @result: The key services are verified.
        @step: Restore the snapshot.
        @result: The snapshot is restored.
        @step: Verify the Server JRE version.
        @result: The JRE version is verified.
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        expected_litp_version = "R1DZ02"
        litp_iso_from_version = "2.128.4"
        java_from_version = "1.8.0_281"
        self.execute_java_upgrade_procedure(expected_litp_version,
                                            litp_iso_from_version,
                                            java_from_version)

    def execute_java_upgrade_procedure(self, expected_litp_version,
                                       litp_iso_from_version,
                                       java_from_version,
                                       force_litp_upgrade=False,
                                       exclude_puppetserver=False):
        """
        Description:
            Executes an upgrade from the expected LITP From-state
            to the desired LITP To-state. Before and after the
            upgrade the code ensures that the JRE version is
            the expected and that the process is running.
        Args:
            expected_litp_version (str): RSTATE of the expected
                                         LITP version.
            litp_iso_from_version (str): Version number of
                                         the LITP From-state iso
            java_from_version (str): Version of the From-state JRE.
            force_litp_upgrade (bool): Flag to force a LITP
                                       upgrade. Required due to
                                       ERIClitpcore version not
                                       changing between LITP
                                       isos which contain
                                       different ServerJRE
                                       versions.
            exclude_puppetserver (bool) : Flag on whether to
                                          check the puppetserver
                                          is using the latest
                                          java.
        """
        # Verify LITP iso is located in specified location.
        self.log('info',
                 "1. Verify LITP From & To state iso's " \
                 "are located in specified location.")
        self.verify_litp_software_in_dir(litp_iso_from_version)
        self.verify_litp_software_in_dir(self.litp_iso_to_version)

        # verify LITP version currently installed
        self.log('info',
                 "2a. Verify that the LITP version " \
                 "currently installed is the expected.")
        stdout, rcode = \
            self.verify_litp_version_installed(expected_litp_version)
        self.assertNotEqual(rcode, 1, stdout)

        # The version of ERIClitpcore didn't change between a number of sprints
        # so in some cases, while the version of core hasn't changed
        # we know that the rest of the plugins do need updating
        # so we force the upgrage to the later LITP iso to be executed.
        if rcode == 0 and force_litp_upgrade:
            rcode = 2

        try:
            # If LITP version installed is older than
            # required version then upgrade LITP.
            if rcode == 2:
                self.log('info',
                         "2b. Upgrade the deployment " \
                         "to the expected LITP version.")
                # Create snapshots of the deployment
                self.execute_and_wait_createsnapshot(self.management_server)

                # Upgrade LITP
                self.upgrade_litp(litp_iso_from_version)
                self.log('info',
                         "2c. Verify that the LITP version " \
                         "currently installed is the expected.")
                stdout, rcode = \
                    self.verify_litp_version_installed(expected_litp_version)
                self.assertEqual(rcode, 0,
                                 "After upgrade LITP version " \
                                 "is not the expected.s")

            # Verify java versions currently installed are the expected.
            self.log('info',
                     "3. Verify the Java version " \
                     "installed is the expected From-state.")
            self.verify_java_version(self.all_nodes,
                                     java_from_version)

            # Verify Java installed is derived from reporitory RPM.
            self.verify_java_installed_from_repo()

            # verify java process is running
            self.log('info', "4. Verify the Java process is running.")
            self.verify_java_process([self.management_server])

            # Verify key services are using the correct JRE.
            self.verify_key_services_have_updated_to_use_latest_jre(
                                                exclude_puppetserver)

            # Create snapshots of the deployment
            self.log('info',
                     "5. Upgrade LITP to the version " \
                     "with the latest Java version under test.")
            self.execute_and_wait_createsnapshot(self.management_server)

            # Upgrade LITP to the later version
            self.upgrade_litp(self.litp_iso_to_version)

            # Verify java versions now installed are the expected.
            self.log('info',
                     "6. Verify the Java version " \
                     "installed is the expected To-state.")
            self.verify_java_version(self.all_nodes,
                                     self.java_to_version)

            # Verify Java installed is derived from reporitory RPM.
            self.verify_java_installed_from_repo()

            # verify java process is running
            self.log('info', "7. Verify the Java process is running.")
            self.verify_java_process([self.management_server])

            # Verify key services are using the correct JRE.
            self.verify_key_services_have_updated_to_use_latest_jre()

        finally:
            # Restore the Pre Upgrade snapshots
            self.log('info', "8. Restore the deployment to the last snapshot.")
            self.execute_and_wait_restore_snapshot(self.management_server)

            # Remove the snapshots
            self.execute_and_wait_removesnapshot(self.management_server)

            # verify java versions currently installed are the expected.
            self.log('info',
                     "9. Verify the Java version installed " \
                     "is the expected From-state.")
            self.verify_java_version(self.all_nodes,
                                     java_from_version)
