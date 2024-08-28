"""
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     Oct 2019
@author:    Laurence Canny
@summary:   Check processes that are using java are using the java version
            that is running. In previous java uplifts, some processes
            running in the jvm were running on the older java version.
"""

import test_constants as const
from litp_generic_test import GenericTest, attr


class Bug377425(GenericTest):
    """
    Bug TORF-377426
        puppetdb and puppetserver not restarted after Java uplift
    """

    def setUp(self):
        """ Runs before every single test """
        super(Bug377425, self).setUp()
        self.ms_node = self.get_management_node_filename()
        self.peer_nodes = self.get_managed_node_filenames()

    def tearDown(self):
        """ Runs after every single test """
        super(Bug377425, self).tearDown()

    def _get_ms_java_version(self):
        """
        Description:
            Get the running java version on ms
        Results:
            String, Java version
        """
        cmd = "{0} -version 2>&1 | head -n 1 | {1} -F '\"' " \
              "'{{ print $2 }}'".format(const.JAVA_PATH, const.AWK_PATH)

        running_java_version = self.run_command(
            self.ms_node, cmd, default_asserts=True)[0]
        java_version = ''.join(running_java_version)

        return java_version

    @attr('pre-reg', 'revert', 'bug377425', 'bug377425_tc01')
    def test_01_p_check_java_version(self):
        """
        #tms_id: TORF_377425_tc01
        #tms_requirements_id: TORF-377425
        #tms_title: Check java version against package version
        #tms_description: Verifies that the java version running on ms is
            consistent with what's in EXTRserverjre in the repo
        #tms_test_steps:
            #step: Determine if EXTRserverjre is installed
            #result: EXTRserverjre installed
            #step: Get the java version from EXTRserverjre rpm
            #result: java version returned
            #step: Get the java version running on MS
            #result: Java version on MS returned
            #step: Compare Java version running on MS to expected Java
            version found in EXTR
            #result: Java versions are matching
        #tms_test_precondition: NA
        #tms_execution_type: Automated
        """
        package = "EXTRserverjre_CXP9035480"
        self.assertTrue(self.check_pkgs_installed(self.ms_node, [package]),
                        "package {0} not installed on {1}"
                        .format(package, self.ms_node))

        self.log("info", "# 1. Determine package version from the "
                             "repo")

        cmd = "{0} {1}/{2}* | tail -1"\
            .format(const.LS_PATH, const.PP_PKG_REPO_DIR, package)
        server_jre_version = self.run_command(
            self.ms_node, cmd, default_asserts=True)[0]
        server_jre_version = ''.join(server_jre_version)

        self.log("info", "# 2. Get java version from package")

        cmd = "{0} -qlp {1} | {2} -F'/' '{{print $4}}' | " \
              "head -n 1 | {3} 's/[a-z]*//'"\
            .format(const.RPM_PATH, server_jre_version,
                    const.AWK_PATH, const.SED_PATH)

        package_java_version = self.run_command(
            self.ms_node, cmd, default_asserts=True)[0]
        package_java_version = ''.join(package_java_version)

        ms_java_version = self._get_ms_java_version()
        self.assertEquals(ms_java_version, package_java_version,
                          "Java version {0} does not match package "
                          "version {1}".format(ms_java_version,
                                               package_java_version))

    @attr('pre-reg', 'revert', 'bug377425', 'bug377425_tc02')
    def test_02_p_check_java_version(self):
        """
        #tms_id: TORF_377425_tc02
        #tms_requirements_id: TORF-377425
        #tms_title: Verify java version on nodes
        #tms_description: Verifies that the java version running on nodes
            is consistent with what's running on ms
        #tms_test_steps:
            #step: Get the currently running java version on ms
            #result: MS java version
            #step: Get the currently running java version on each node
            #step: Compare java versions
            #result: Java versions match
        #tms_test_precondition: NA
        #tms_execution_type: Automated
        """
        cmd = "{0} -version 2>&1 | head -n 1 | {1} -F '\"' " \
              "'{{ print $2 }}'".format(const.JAVA_PATH, const.AWK_PATH)
        ms_java_version = self._get_ms_java_version()

        for node in self.peer_nodes:
            node_java_version = self.run_command(node, cmd,
                                                 default_asserts=True)[0]

            node_java_version = ''.join(node_java_version)

            self.assertEquals(node_java_version,
                              ms_java_version, "Java version {0} does not "
                                               "match {1}".format
                              (node_java_version, ms_java_version))

    @attr('pre-reg', 'revert', 'bug377425', 'bug377425_tc03')
    def test_03_p_verify_process(self):
        """
        #tms_id: TORF_377425_tc03
        #tms_requirements_id: TORF-377425
        #tms_title: Check the jvm processes
        #tms_description: Verifies that the processes running in the jvm
            are running on the latest java version
        #tms_test_steps:
            #step: Get the java version currently running on ms
            #result: MS java version
            #step: Get the process ids for the services
            #result: pids returned
            #step: Check the java version that the pids are running against
            #step: Compare the java version with the ms java version
            #result: Java versions match
        #tms_test_precondition: NA
        #tms_execution_type: Automated
        """
        services = ["puppetdb", "puppetserver"]
        ms_java_version = self._get_ms_java_version()

        for service in services:
            self.log("info",
                     "# 1. Determine pid for processes running in jvm")

            cmd = "{0} -ef | {1} {2} | {1} -v postgres | head -n 1 " \
                  "| {3} '{{ print $2 }}'".format(const.PS_PATH,
                                                  const.GREP_PATH, service,
                                                  const.AWK_PATH)
            service_pid, _, _ = self.run_command(
                self.ms_node, cmd, default_asserts=True)
            service_pid = ''.join(service_pid)

            self.log("info", "# 2. Determine java version that pid is"
                             " associated with")
            cmd = "{0} -p {1} | {2} jdk | {3} '{{ print $9 }}' | head -n 1"\
                .format(const.LSOF_PATH, service_pid, const.GREP_PATH,
                        const.AWK_PATH)

            service_java_path, _, _ = self.run_command(
                self.ms_node, cmd, default_asserts=True, su_root=True)

            self.assertTrue((self.is_text_in_list(ms_java_version,
                                                 service_java_path),
                            "Java versions match"), "Java version {0} does" \
                                                    "not match {1}".format(
                service_java_path, ms_java_version))
