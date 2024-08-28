"""
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     March 2015 , Refactored on May 2019
@author:    eslakal , Yashi Sahu
@summary:   As a LITP User I want to write a test
            where Symantec DMP is to be the only multipather
            used in a node and that is member of an sfha cluster.
            Agile: STORY LITPCDS-416
"""
from litp_generic_test import GenericTest, attr
import test_constants as const


class Story4016(GenericTest):
    """
    LITPCDS-4016:
        As a LITP User, I want Symantec DMP to be the only multipather
        used in a node that is member of an sfha cluster
    """

    def setUp(self):
        """Run before every test """
        super(Story4016, self).setUp()
        self.mn_nodes = self.get_managed_node_filenames()
        self.ms_node = self.get_management_node_filename()
        self.vcs_cluster_ms = self.find(self.ms_node,
                                        '/deployments', 'vcs-cluster')
        self.phys_devs = self.find(self.ms_node, '/deployments',
                                   'physical-device')

    def tearDown(self):
        """Run after every test"""
        super(Story4016, self).tearDown()

    @attr('all', 'revert', 'story4016', 'story4016_tc01')
    def test_01_p_verify_disk_facts(self):
        """
        @tms_id: Story4016_tc01
        @tms_requirements_id: LITPCDS-4016
        @tms_title: Write a test where Symantec DMP is to be the
                   only multipather used in a node and that
                   is member of an sfha cluster.
        @tms_description: Verify that facter provides facts
                  for physical devices with paths under
                  control of dmp.
        @tms_test_steps:
            @step: Get the cluster type of ms.
            @result: Cluster type of ms
                   successfully obtained.
            @step: Get the device name "sda" from
                   peer nodes.
            @result: Device name "sda" successfully obtained
                   for peer nodes.
            @step: Query facter for paths to sda device
            @result: Facter provides facts about all physical devices
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        for node in self.vcs_cluster_ms:
            self.log('info', '1. Get the cluster type of ms')
            cluster_type = self.get_props_from_url(self.ms_node, node,
                                               filter_prop="cluster_type")
            self.log('info',
                     '2. Cluster type of ms is : {0}'.format(cluster_type))

        for dev_url, node in zip(self.phys_devs, self.mn_nodes):

            self.log('info', '3. Get the device name of peer nodes')
            dev_name = self.get_props_from_url(self.ms_node, dev_url,
                                               'device_name')
            self.log('info',
                     '4. Device name of peer node is : {0}'.format(dev_name))

            self.log('info', '5. Query facter for paths to sda device')
            facter_cmd = '{0} -p disk_{1}'.format(const.FACTER_PATH, dev_name)
            path = self.run_command(node, facter_cmd, su_root=True,
                                    default_asserts=True)[0]

            self.log('info', '6. Assertion confirmed that facter provides'
                             'facts to all physical devices')
            self.assertTrue('/dev/vx/dmp/' in ''.join(path), "facter does not "
            "provide path to all"
            "physical devices")
