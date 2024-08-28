'''
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     Septembre 2015
@author:    Jose Martinez & Jenny Schulze
@summary:   Integration test for story 7136: POODLE: SSLv3 vulnerability
            (CVE-2014-3566)
            Agile: STORY-7136
'''

from litp_generic_test import GenericTest, attr
from redhat_cmd_utils import RHCmdUtils
import os


class Story7136(GenericTest):
    """
        POODLE: SSLv3 vulnerability (CVE-2014-3566)
    """

    def setUp(self):
        """run before every test"""
        super(Story7136, self).setUp()
        self.ms_node = self.get_management_node_filename()
        self.mn_nodes = self.get_managed_node_filenames()
        self.rhcmd = RHCmdUtils()

    def tearDown(self):
        """run after every test"""
        super(Story7136, self).tearDown()

    @attr('all', 'revert', 'story7136', 'story7136_tc01')
    def test_01_p_check_ssl_vulnerabilities(self):
        """
        Description:
            Test to verify that there is no SSLv3 vulnerability
        Actions
            1. Get list of ports
            2. Verify that ports are not vulnerable
        Result:
            Verify that there is no SSLv3 vulnerability
        """

        local_base_path = os.path.dirname(os.path.abspath(__file__))
        story_files = "7136_files"
        poodle_script = "poodle.sh"

        ms_tmp_dir = "/tmp/"

        bash_cmd = "/bin/bash "

        outlist = list()
        netstat_cmd = "/bin/netstat -tuwanp"
        filters = " | awk '{print $4}' | rev | grep \":\" | cut -d':' -f1 "\
                  "| rev | sort -n | uniq"

        for node in self.mn_nodes + [self.ms_node]:
            self.log('info', '1. Get list of ports')
            ports, _, _ = self.run_command(node,
                                           netstat_cmd + filters,
                                           default_asserts=True,
                                           su_root=True)

            self.log('info', '2. Verify that ports are not vulnerable')
            self.copy_file_to(node,
                              os.path.join(local_base_path,
                                           story_files,
                                           poodle_script),
                              ms_tmp_dir,
                              root_copy=True)
            for port in ports:
                out, _, _ = self.run_command(node,
                    "{0}{1}{2} localhost {3}".format(bash_cmd, ms_tmp_dir,
                        poodle_script, port))
                if self.is_text_in_list("Vulnerable!", out):
                    outlist.append((node, port))

        for node, port in outlist:
            self.log('error',
                    "Port {0} on node {1} is SSLv3 vulnerable".format(
                port, node))

        self.assertEqual([], outlist)
