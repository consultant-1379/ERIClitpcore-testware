'''
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     Feb 2016
@author:    Jenny Schulze, Jose Martinez
@summary:   LITPCDS-13319:
            No login banner message visible when logging on to the nodes on the
            system
'''
from litp_generic_test import GenericTest, attr
from redhat_cmd_utils import RHCmdUtils
import test_constants as const


class Bug13319(GenericTest):
    """
    LITPCDS-13319:
        No login banner message visible when logging on to the nodes on the
        system
    """

    def setUp(self):
        """ Setup variables for every test """
        super(Bug13319, self).setUp()
        self.rhcmd = RHCmdUtils()
        self.ms_node = self.get_management_node_filename()
        self.mn_nodes = self.get_managed_node_filenames()
        self.all_nodes = [self.ms_node] + self.mn_nodes

    def tearDown(self):
        """ Runs for every test """
        super(Bug13319, self).tearDown()

    @attr('all', 'revert', 'bug13319', 'bug13319_tc01')
    def test_01_verify_banner(self):
        """
        @tms_id: LITPCDS-13319_tc01
        @tms_requirements_id:  LITPCDS-12672
        @tms_title: Verify banner.
        @tms_description: Verify that when we ssh the nodes and ms,
            we get the banner message.
        @tms_test_steps:
         @step: For each node, check '/etc/ssh/sshd_config' file.
         @result: File includes an entry "Banner" followed by the banner file
             path "/etc/issue.net".
         @step: For each node, get the banner content from the
             banner file '/etc/issue.net'.
         @result: Banner content retrieved successfully.
         @step: For each node, ssh to the node using root & litp-admin.
         @result: Verify that the contents of the banner file match the
             observed banner.
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        banner_file = "/etc/issue.net"
        enabled_option = "^ *Banner {0} *$".format(banner_file)
        ssh_options = "-o StrictHostKeyChecking=no -o " \
                      "UserKnownHostsFile=/dev/null"

        for node in self.all_nodes:
            self.log("info", "1.  Verify banner option in '{0}' file on the"\
                " '{1}' node.".format(const.SSH_CFG_FILE, node))
            grep_cmd = self.rhcmd.get_grep_file_cmd(const.SSH_CFG_FILE,
                                            enabled_option)
            self.run_command(node, grep_cmd,
                                        su_root=True,
                                        default_asserts=True)
            self.log("info", "2.  Get banner content from the banner file on"\
                " the '{0}' node.".format(node))
            banner_content = self.get_file_contents(node, banner_file)
            for user in ["litp-admin", "root"]:
                self.log("info", "3.  ssh {0}@{1}".format(user, node))
                output, _, _ = self.run_expects_command(node,
                            "{0} {1} {2}@{3}".format(const.SSH_PATH,
                                                     ssh_options,
                                                     user,
                                                     node),
                                                     [])
                self.log("info", "4.  Verify banner on ssh connection matches"\
                    " content of '{0}' on node '{1}' with user '{2}'.".format(
                    "/etc/issue.net", node, user))
                banner_cont_err_txt = "Banner output is not as expected for"\
                    " user {0} on the node '{1}'.".format(user, node)
                for banner_line in banner_content:
                    self.assertTrue(self.is_text_in_list(banner_line, output,
                        ), banner_cont_err_txt)
