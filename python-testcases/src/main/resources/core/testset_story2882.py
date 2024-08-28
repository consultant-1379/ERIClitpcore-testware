'''
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     March 2014
@author:    Jacek Spera
@summary:   Integration test for story 2882: As a LITP Developer I want include
            MCollective SimpleRPC agents with my plug-in so they can be
            registered and made available for plug-ins to use.
            Agile: STORY-2882
'''
from litp_generic_test import GenericTest, attr
from litp_cli_utils import CLIUtils
import os
from redhat_cmd_utils import RHCmdUtils
from test_constants import LITP_PKG_REPO_DIR
# from test_constants import  PLAN_FAILED, MCO_LOG_FILE

NODE_MCO_AGENT_PATH = "/opt/mcollective/mcollective/agent/"


class Story2882(GenericTest):
    """
    Description:
            I want include MCollective SimpleRPC agents with my plug-in so they
            can be registered and made available for plug-ins to use.
    Prerequisites:
        Plugin rpm containing mco agent exists in a path known by this test
        1+ nodes deployment is in place
    """

    def setUp(self):
        """ Setup variables for every test """
        super(Story2882, self).setUp()
        self.ms_node = self.get_management_node_filename()
        self.mn_nodes = self.get_managed_node_filenames()
        self.cli = CLIUtils()
        self.rhcmd = RHCmdUtils()

        self.rpm_pkg_name = "ERIClitpmcoagenttest_CXP1234567"

        self.rpm_file_names = {
            "standard": ("ERIClitpmcoagenttest_CXP1234567-1.0.1"
                         "-SNAPSHOT202106291723.noarch.rpm"),
            "update": ("ERIClitpmcoagenttest_CXP1234567-1.0.1-"
                       "SNAPSHOT202106301623.noarch.rpm"),
            "broken": ("ERIClitpmcoagenttest_CXP1234567-1.0.1"
                       "-SNAPSHOT202010201242.noarch.rpm"),
        }

        self.rpm_local_paths = {
            "standard": os.path.join(os.path.dirname(__file__),
                                     self.rpm_file_names["standard"]),
            "update": os.path.join(os.path.dirname(__file__),
                                   self.rpm_file_names["update"]),
            "broken": os.path.join(os.path.dirname(__file__),
                                   self.rpm_file_names["broken"])
        }

        self.litp_config_path = '/var/lib/litp/core/model/LAST_KNOWN_CONFIG'
        self.mco_agent_name = 'helloworld'
        self.mco_agent_filexts = ('rb', 'ddl', 'py')
        self.mco_agent_not_filexts = ('pyc', 'pyo')

    def tearDown(self):
        """ Called after every test """
        super(Story2882, self).tearDown()

    def _remove_package_from_litp_repo(self):
        """ Delete test rpms from repo; revert to pre-test state """
        for fname in self.rpm_file_names.values():
            self.remove_item(self.ms_node,
                             os.path.join(LITP_PKG_REPO_DIR, fname),
                             su_root=True)
        self.run_command(self.ms_node,
                         self.rhcmd.get_createrepo_cmd(LITP_PKG_REPO_DIR),
                         su_root=True)

    def _remove_mco_agent_files_from_nodes(self):
        """ Delete mco agent files copied to nodes """
        node = self.get_managed_node_filenames()[0]
        path = os.path.join(NODE_MCO_AGENT_PATH,
                            self.mco_agent_name + '.*')
        self.remove_item(node, path, su_root=True)
        self.remove_item(self.ms_node, path, su_root=True)

    def _mco_agent_files_available_on_nodes(self, search_string=""):
        """ Check if mco agent file names are present on managed nodes """
        cmds = []
        for ext in self.mco_agent_filexts:
            cmds.append(self.rhcmd.get_find_files_in_dir_cmd(
                "{0} -name {1}.{2}".format(NODE_MCO_AGENT_PATH,
                                           self.mco_agent_name, ext),
                [search_string], "-l"))

        for node in self.mn_nodes:
            for cmd in cmds:
                self.assertTrue(self.wait_for_puppet_action(
                    self.ms_node, node, cmd, 0, su_root=True))
            for ext in self.mco_agent_not_filexts:
                path = "{0}/{1}.{2}".format(NODE_MCO_AGENT_PATH,
                        self.mco_agent_name, ext)
                self.assertFalse(self.remote_path_exists(node, path,
                                 su_root=True), path)
        return True

    def _mco_agent_updates_available_on_nodes(
            self, search_string="comment in updated file"):
        """ Tests if updated mco agent files are available on nodes """
        return self._mco_agent_files_available_on_nodes(search_string)

    def _restore_litp_config(self, node, path):
        """ Restores backed up litp config file """
        for i, backup in enumerate(self.backup_filelist):
            if backup["NODE"] == node and backup["TARGET_PATH"] == path:
                self.mv_file_on_node(backup["NODE"],
                                     backup["SOURCE_PATH"],
                                     backup["TARGET_PATH"],
                                     su_root=True,
                                     add_to_cleanup=False)
                # safe to modify list here as return stmt follows
                del self.backup_filelist[i]
                return

    def _uninstall_plugin(self):
        """ Clean up function overriding current limitation where plugins
        cannot be uninstalled """
        cmd = self.rhcmd.get_service_stop_cmd("litpd")
        self.run_command(self.ms_node, cmd, su_root=True)
        self._restore_litp_config(self.ms_node, self.litp_config_path)
        cmd = self.rhcmd.get_yum_cmd("remove -y {0}".format(self.rpm_pkg_name))
        # will restart litp
        self.run_command(self.ms_node, cmd, su_root=True)
        # restart litp again to turn debug on
        self.restart_litpd_service(self.ms_node)

    @attr('all', 'revert', 'story2882', 'story2882_tc1')
    def test_01_p_mco_agents_on_nodes_after_plugin_install_or_update(self):
        """
        Description:
            Verifies that mco agents contained in plugin rpms get distributed
            to nodes when plugins are installed or upgraded

            #TORF-108837: Verify that pyc, pyo files are ignored
        Actions:
            1. Create dummy pyo, pyc file
            2. Install plugin package on ms
            3. Verify on nodes that mco agent can be found in the expected path
            4. Verify that pyo/pyc files have not been copied
            5. Verify that existing pyo/pyc have not been deleted
            6. Update plugin package on ms
            7. Verify that mco agent files got updated on managed nodes
        Results:
            Mco agent files can be found on all nodes
            After update updated files on all nodes
            Pyo/Pyc files are ignored
        """
        node = self.mn_nodes[0]
        dummy_pyxpaths = [
                os.path.join(NODE_MCO_AGENT_PATH, "dummy.pyc"),
                os.path.join(NODE_MCO_AGENT_PATH, "dummy.pyo")
                ]

        for path in dummy_pyxpaths:
            self.assertTrue(
                    self.create_file_on_node(node, path, [],
                        empty_file=True, su_root=True))

        self.copy_and_install_rpms(self.ms_node,
                                   [self.rpm_local_paths['standard']])

        self.assertTrue(self._mco_agent_files_available_on_nodes())

        # verify that pyo, pyc files have not been deleted during the
        # puppet run
        for path in dummy_pyxpaths:
            self.assertTrue(self.remote_path_exists(node, path, su_root=True))
        self.copy_and_install_rpms(self.ms_node,
                                   [self.rpm_local_paths['update']])
        self.assertTrue(self._mco_agent_updates_available_on_nodes())

#   Test involves installing destructive plugin so can only be added to CI
#   after deconfigure plugin story delivered.
#
#   def test_02_p_invalid_mco_agent_doesnt_break_others_errors_logged(self):
#       """
#       Description:
#           Verifies that installation of a plugin containing invalid mco agent
#           does not break other plugins and enough logging is done to track
#           down the issue
#           Plugin has to generate RemoteExecutionTask that uses invalid mco
#           agent
#       Actions:
#           1. Import rpm to litp repo via litp import
#           2. Install plugin package on ms
#           3. Kick puppet (mco puppet runonce) to speed up test
#           4. Edit the source of mco agent on ms introducing syntax error
#              (simulates installation of a package with broken agent)
#           5. Modify model to enable plan creation
#           6. Create a plan
#           7. Run plan
#           8. Expect plan fails at the task using broken mco agent and not for
#              any other task before it
#           9. Verify on nodes that /var/log/mcollective.log contains entry
#              describing the error
#       Results:
#           Plan will fail at the task that uses broken mco agent but other
#           remote execution tasks run before will succeed.
#           Mcollective will log the error on each node.
#       """
#       try:
#           self.backup_file(self.ms_node, self.litp_config_path)
#           self.copy_and_install_rpms(
#               self.ms_node, [self.rpm_local_paths['broken']])
#           self.assertTrue(self._mco_agent_files_available_on_nodes())

#           self.execute_cli_create_cmd(self.ms_node, '/software/items/vim',
#                                       'package', 'name="vim"',
#                                       add_to_cleanup=False)
#           self.execute_cli_link_cmd(self.ms_node, '/ms/items/vim',
#                                     'package', 'name="vim"',
#                                     add_to_cleanup=False)
#           self.execute_cli_createplan_cmd(self.ms_node)
#           self.execute_cli_runplan_cmd(self.ms_node)

#           self.assertTrue(self.wait_for_plan_state(self.ms_node,
#                                                    PLAN_FAILED))

#           node = self.get_managed_node_filenames()[0]
#           cmd = self.rhcmd.get_grep_file_cmd(
#               MCO_LOG_FILE,
#               "Loading agent {0} failed".format(self.mco_agent_name))
#           stdout, stderr, returnc = self.run_command(node, cmd, su_root=True)
#           self.assertEqual(0, returnc)
#           self.assertEqual([], stderr)
#           self.assertNotEqual([], stdout)
#       finally:
#           node = self.get_managed_node_filenames()[0]
#           # clean up mcollective.log
#           cmd = "sed -i '/{0}/d' {1}".format(self.mco_agent_name,
#                                              MCO_LOG_FILE)
#           self.run_command(node, cmd, su_root=True, add_to_cleanup=False)
#           self.execute_cli_removeplan_cmd(self.ms_node)
#           self._remove_package_from_litp_repo()
#           self._uninstall_plugin()
#           self._remove_mco_agent_files_from_nodes()
