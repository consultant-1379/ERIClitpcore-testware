"""
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     September 2015, Refactored May 2019
@author:    Jose Martinez, Jenny Schulze, Refactored by Yashi Sahu
@summary:   Integration test for story 9797:
            As a LITP Architect I want ERIClitpcore .conf files to be
            marked as %config so that edits to these config files
            won't get lost during a subsequent upgrade.
            Agile: STORY-9797
"""
from litp_generic_test import GenericTest, attr
import test_constants


class Story9797(GenericTest):
    """
    As a LITP Architect I want the ERIClitpcore .conf files to be
    marked as %config so that edits to these config files won't get lost
    during a subsequent upgrade.
    """

    def setUp(self):
        """ Runs before every test """
        super(Story9797, self).setUp()
        self.ms_node = self.get_management_node_filename()

    def tearDown(self):
        """ Runs after every test"""
        super(Story9797, self).tearDown()

    @attr('all', 'revert', 'story9797', 'story9797_tc01')
    def test_01_verify_config_noreplace_is_set_for_core(self):
        """
        @tms_id: litpcds_story9797_tc01
        @tms_requirements_id: LITPCDS-9797
        @tms_title: Write a test where ERIClitpcore .conf files
            will be marked as %config so that no upgrades can effect
            the changes in config files.
        @tms_description: This test will verify that the ERIClitpcore
            .conf files was build with the %config(noreplace) flag set for:
            /etc/litp_logging.conf cn
            /etc/litp_security.conf cn
        @tms_test_steps:
            @step: Run rpm ERIClitpcore_CXP9030418 on ms.
            @result: RPM ERIClitpcore_CXP9030418 executed successfully
                on ms.
            @step: Verify that %config(noreplace) is set for the files.
            @result: Proper values in maintenance item
                %config(noreplace) is  successfully set for files.
                /etc/litp_logging.conf
                /etc/litp_security.conf
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """

        core_package = "ERIClitpcore_CXP9030418"
        file_list = [test_constants.LITP_LOGGING_CONF,
                     test_constants.LITP_SEC_CONF_FILE]
        self.log("info", "1. Run rpm ERIClitpcore_CXP9030418 on ms. ")
        std_out = self.run_command(self.ms_node, "{0} -qi --queryformat" \
              " '[%{{FILENAMES}}__%{{FILEFLAGS:fflags}}\\n]'  {1} " \
              "| {2} 'cn' ".format(test_constants.RPM_PATH, core_package,
              test_constants.GREP_PATH),
              default_asserts=True)[0]
        self.assertNotEqual([], std_out, "RPM contents are not empty")

        self.log("info", "2. Verify that %config(noreplace) is set for "
                         " the files.")
        for config_file in file_list:
            verify_config_noreplace = "{0}__{1}".format(config_file, "cn")
            self.assertTrue(self.is_text_in_list(verify_config_noreplace,
            std_out),
            "%config(noreplace) not set for {0}".format(config_file))
