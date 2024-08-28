"""
COPYRIGHT Ericsson 2024
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     Feb 2024
@author:    James Goring
@summary:   TORF-693264
            LITP is being updated to be able to import from the
            RHEL AppStream.
            This test is to ensure that the litp import command
            does not modify the metadata of a AppStream Repo
            when it is imported.
"""

import os
from litp_generic_test import GenericTest, attr
from litp_cli_utils import CLIUtils
from redhat_cmd_utils import RHCmdUtils


class Story693264(GenericTest):
    """
    I want to ensure litp import does not modify
    the AppStream Repo metadata when importing a repo
    """

    def setUp(self):
        """ Runs before every single test """
        super(Story693264, self).setUp()
        self.ms1 = self.get_management_node_filename()
        self.cli = CLIUtils()
        self.rhcmd = RHCmdUtils()

        self.repo_remote_path = "/tmp/appstream_repo"
        self.repo_remote_path_repodata = self.repo_remote_path + \
                                                "/repodata/repomd.xml"

    def tearDown(self):
        """ Runs after every single test """
        super(Story693264, self).tearDown()

    @attr('all', 'revert', 'story693264', 'story693264_tc06')
    def test_06_verify_litp_import(self):
        """
        @tms_id:
            torf_693264_tc_06
        @tms_requirements_id:
            TORF-693264
        @tms_title:
            litp import to support repo containing AppStream modules
        @tms_description:
            litp import does not modify AppStream Repo metadata
        @tms_test_steps:
            @step: Obtain revision number from local AppStream Repo metadata
                                                        via grep "revision".
            @result: Revision number is stored for later comparison.

            @step: Create tar file of a local Dummy Repo
                                            containing AppStream metadata.
            @result: Tar file is created, available to be copied over to MS.

            @step: Copy tar file over to MS.
            @result: Tar file is available on MS to be unpacked.

            @step: unpack tar file on MS into new directory.
            @result: New directory created in /tmp/ directory to be imported

            @step: Run "litp import < New AppStream Repo directory >
                        /var/www/html/8.8/updates_AppStream/x86_64/Packages".
            @result: New directory containing repo is created in /var/www/...

            @step: Grep newly imported repo metadata for "revision"
                                and compare to local "revision" grep.
            @result: "revision" grep of local Repo metadata should
                     match newly imported Repo metadata "revision" grep.


        @tms_test_precondition: Dummy Repo exists locally
                                to be grepped and tarballed.

        @tms_execution_type: Automated
        """

        repo_local_pt = os.path.join(os.path.dirname(__file__), "693264_rpms/")
        tar_filename = "693264_rpms.gz.tar"

        litp_import_cmd = "litp import " + self.repo_remote_path + \
                                                 repo_local_pt + \
                        " /var/www/html/8.8/updates_AppStream/x86_64/Packages"

        grep_revision_cmd = "grep 'revision' " + self.repo_remote_path + \
                                        repo_local_pt + "repodata/repomd.xml"

        grep_local_revision_cmd = "grep 'revision' " + \
                             repo_local_pt + "repodata/repomd.xml"

        try:
            #1. Obtain the revision number from local repomd.xml
            #   and create directory on node
            local_revision_number, _, _ = self.run_command_local(
                                            grep_local_revision_cmd)

            local_tar_file = repo_local_pt + tar_filename

            self.create_dir_on_node(self.ms1, self.repo_remote_path)

            #2. Tar up local repo directory
            tar_cmd = self.rhcmd.get_tar_cmd("czvf",
                                             local_tar_file,
                                             repo_local_pt)

            cmd = "cd {0} ; ".format(repo_local_pt) + tar_cmd
            self.run_command_local(cmd)

            #3. Copy tar file to MS
            self.copy_file_to(self.ms1,
                            local_tar_file,
                            self.repo_remote_path,
                            root_copy=True)

            #4. Untar the tar file in /tmp
            dest_dir = "--directory={0}".format(self.repo_remote_path)
            untar_cmd = self.rhcmd.get_tar_cmd("xmzvf", self.repo_remote_path +
                                            "/" +
                                            tar_filename,
                                            dest=dest_dir)

            out, _, ret_code = self.run_command(self.ms1, untar_cmd)
            self.assertEqual(0, ret_code)
            self.assertNotEqual([], out)

        #Removes any local directories created even if a failure occurs.
        finally:
            #5. Remove local tar file
            cmd = "/bin/rm {0}".format(local_tar_file)
            self.run_command_local(cmd)

        try:
            # Run the LITP import command and
            # check that the revision hasn't changed due to import
            self.run_command(self.ms1, litp_import_cmd)
            stdout, _, _ = self.run_command(self.ms1, grep_revision_cmd)
            self.assertEqual(stdout[0].strip(), \
                              local_revision_number[0].strip())

        # Removes the new MS directory even if the test fails.
        finally:
            # Remove the /tmp/ files.
            removal_cmd = "rm -rf " + self.repo_remote_path + "/"
            _, _, return_code = self.run_command(self.ms1, removal_cmd)
            self.assertEqual(return_code, 0)
