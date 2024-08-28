'''
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     July 2014
@author:    Ares
@summary:   Integration test for LITPCDS-5277
            Agile:
                Epic: N/A
                Story: LITPCDS-5277
                Sub-Task:
'''

import os
from litp_generic_test import GenericTest
from redhat_cmd_utils import RHCmdUtils


class Story5277(GenericTest):
    """
    LITPCDS-5277:
    As a LITP user, I want the ability to define runtime services under nodes
    in the model.
    """

    def setUp(self):
        """
        Description:
            Runs before every test to perform required setup
        """
        # call super class setup
        super(Story5277, self).setUp()
        self.management_node = self.get_management_node_filename()
        self.rhc = RHCmdUtils()
        self.plugin_id = 'story5277'
        self.filepath = '/tmp'

    def tearDown(self):
        """
        Description:
            Runs after every test to perform required cleanup/teardown
        """

        # call super class teardown
        super(Story5277, self).tearDown()

    @staticmethod
    def get_local_rpm_paths(path, rpm_substring):
        """
        given a path (which should contain some RPMs) and a substring
        which is present in the RPM names you want, return a list of
        absolute paths to the RPMS that are local to your test
        """
        # get all RPMs in 'path' that contain 'rpm_substring' in their name
        rpm_names = [rpm for rpm in os.listdir(path) if rpm_substring in rpm]

        if not rpm_names:
            return None

        # return a list of absolute paths to the RPMs found in 'rpm_names'
        return [
            os.path.join(rpath, rpm)
            for rpath, rpm in
            zip([os.path.abspath(path)] * len(rpm_names), rpm_names)
        ]

    def _install_item_extension(self):
        """
        check if a plugin/extension rpm is installed and if not, install it
        """

        # since the copy_and_install_rpms method in the framework, doesn't
        # check if the package is already installed, we must check if the
        # package does indeed need to be installed - if we don't, and the
        # package is installed, the test will fail
        _, _, rcode = self.run_command(
            self.management_node,
            self.rhc.check_pkg_installed([self.plugin_id]),
            su_root=True
        )

        if rcode == 1:
            # copy over and install RPMs
            local_rpm_paths = self.get_local_rpm_paths(
                os.path.abspath(os.path.dirname(__file__)), self.plugin_id
            )

            self.assertTrue(
                self.copy_and_install_rpms(
                    self.management_node, local_rpm_paths
                )
            )

    def _copy_xml_files(self, xml_files):
        """copy the XML file required for test to the test node"""

        # locate given XML file in test file directory and copy it to the
        # management server to be used by the test
        for filename in xml_files:
            self.assertTrue(
                self.copy_file_to(
                    self.management_node,
                    os.path.join(
                        os.path.abspath(os.path.dirname(__file__)), filename
                    ),
                    self.filepath
                )
            )

    def obsolete_01_p_services_collection_exists(self):
        """
        Obsolete - replaced by an AT:
            ERIClitpcore/ats/testset_story5277/
                test_01_p_services_collection_exists.at
        Description:
        Given a LITP deployment, when a user creates a new node and lists its
        children, the services collection must exist.

        Pre-Requisites:
            1. A running litpd service

        Risks:
            N/A

        Pre-Test Steps:
            N/A

        Steps:
            1.  Execute the CLI commands required to create a new node in the
                model
            2.  Execute the CLI show command on the created node
            3.  Check ../services collection is a child of the node
            4.  Execute the CLI show command on the /software item
            5.  Check ../services collection is a child of /software
            6.  Execute the CLI create command to create an invalid item under
                the ../services collection
            7.  Check for error message
            8.  Execute the CLI remove command to attempt to remove the
                ../services collection items
            9.  Check for error message

        Restore Steps:
            1. Execute the CLI remove command to remove the created node

        Result:
        The services collection must exist as a child of the node.
        """

        # create a test node
        ret = self.run_commands(
            [self.management_node],
            self.get_create_node_deploy_cmds(
                self.management_node, self.plugin_id
            )
        )
        self.assertEqual([], self.get_errors(ret))
        self.assertTrue(self.is_std_out_empty(ret))

        # get created cluster
        for cluster_url in self.find(
            self.management_node, '/deployments', 'cluster'):
            if 'tmp' in cluster_url:
                cluster = cluster_url

        # get the service-base collection url under the cluster and check its
        # expected type
        cluster_service_base_url = self.find_children_of_collect(
            self.management_node, cluster, 'clustered-service', True
        )[0]
        self.assertEqual(
            'collection-of-clustered-service',
            self.execute_show_data_cmd(
                self.management_node, cluster_service_base_url, 'type'
            )
        )

        # get created node
        node = self.find(self.management_node, cluster, 'node', False)[0]

        # get the service-base collection url under the node and check its
        # expected type
        node_service_base_url = self.find_children_of_collect(
            self.management_node, node, 'service-base', True
        )[0]
        self.assertEqual(
            'ref-collection-of-service-base',
            self.execute_show_data_cmd(
                self.management_node, node_service_base_url, 'type'
            )
        )

        # construct the filepath
        filepath = os.path.join(
            self.filepath, '{0}_export.xml'.format(self.plugin_id)
        )

        # export service-base ref to xml file
        self.execute_cli_export_cmd(
            self.management_node, node_service_base_url, filepath
        )

        # check the xml file
        stdout, stderr, rcode = self.run_command(
            self.management_node,
            self.rhc.get_grep_file_cmd(
                filepath, ['litp:node-services-collection']
            )
        )
        self.assertEqual(0, rcode)
        self.assertNotEqual([], stdout)
        self.assertEqual([], stderr)

        # get the ms
        ms_ = self.find(self.management_node, '/ms', 'ms')[0]

        # get the service-base collection url under the ms and check it
        # doesn't exist since services are only created on the nodes
        ms_service_base_url = self.find_children_of_collect(
            self.management_node, ms_, 'service-base', True
        )
        self.assertNotEqual([], ms_service_base_url)

        # get the service-base collection url under software and check its
        # expected type
        software_service_base_url = self.find_children_of_collect(
            self.management_node, '/software', 'service-base', True
        )[0]
        self.assertEqual(
            'collection-of-service-base',
            self.execute_show_data_cmd(
                self.management_node, software_service_base_url, 'type'
            )
        )

        # export service-base collection to xml file
        self.execute_cli_export_cmd(
            self.management_node, software_service_base_url, filepath
        )

        # check the xml file
        stdout, stderr, rcode = self.run_command(
            self.management_node,
            self.rhc.get_grep_file_cmd(
                filepath, ['litp:software-services-collection']
            )
        )
        self.assertEqual(0, rcode)
        self.assertNotEqual([], stdout)
        self.assertEqual([], stderr)

        # try to create an invalid item under /software/services
        self.execute_cli_create_cmd(
            self.management_node,
            os.path.join(
                software_service_base_url, '{0}_invalid'.format(self.plugin_id)
            ),
            'package', 'name=\'{0}_invalid\''.format(self.plugin_id),
            expect_positive=False
        )

        # try to remove the /software/services item
        self.execute_cli_remove_cmd(
            self.management_node, software_service_base_url,
            expect_positive=False
        )

    def obsolete_02_p_add_service_item_node_cli(self):
        """
        Obsolete - covered partially (CLI) by AT that replaced test_01 and xml
        side by other AT and UT
            ERIClitpcore/ats/testset_story5277/\
                test_01_p_services_collection_exists.at
        Description:
        Given a LITP deployment, when a user creates a valid service item in
        the LITP model with valid configuration parameters, the service item
        will be created in the model tree for the given node.

        Pre-Requisites:
            1.  A running litpd service

        Risks:
            1.  Once a plugin/extension package is installed, it cannot be
                removed

        Pre-Test Steps:
            1.  Create a new dummy extension as described in the LITP 2 SDK
            2.  Edit the extension to extend service-base and be a child of
                services collection with a few properties
            3.  Build and install the extension package

        Steps:
            1.  Execute the CLI create command to create the service item in
                the LITP model
            2.  Execute the CLI export command and check the item is
                successfully exported to an XML file
            3.  Execute the CLI inherit command to subclass the service item to
                the node
            4.  Execute the CLI export command and check the inherited item is
                also successfully exported to an XML file

        Restore Steps:
            1.  Execute the CLI remove command to remove the inherited service
                item from the node
            2.  Execute the CLI remove command to remove the service item from
                /software/services
            3.  Check items no longer exist in the model

        Result:
            Creating the dummy service item, through the use of the extension
            type, must be successful.
        """

        # install the service item type extension package
        self._install_item_extension()

        # get the service-base collection from /software
        service_base_collection = self.find(
            self.management_node, '/software', 'service-base', False
        )[0]

        # construct the service item url to be created
        service_item = os.path.join(service_base_collection, self.plugin_id)

        # execute the create cmd
        self.execute_cli_create_cmd(
            self.management_node, service_item, self.plugin_id,
            'name=\'{0}\''.format(self.plugin_id)
        )

        # execute the show command
        self.execute_cli_show_cmd(self.management_node, service_item)

        # construct the filepath
        filepath = os.path.join(
            self.filepath, '{0}_export.xml'.format(self.plugin_id)
        )

        # export service item extension to xml file
        self.execute_cli_export_cmd(
            self.management_node, service_item, filepath
        )

        # check the xml file
        stdout, stderr, rcode = self.run_command(
            self.management_node,
            self.rhc.get_grep_file_cmd(
                filepath, ['litp:{0}'.format(self.plugin_id)]
            )
        )
        self.assertEqual(0, rcode)
        self.assertNotEqual([], stdout)
        self.assertEqual([], stderr)

        # get a node from the model
        node = self.find(self.management_node, '/deployments', 'node')[0]

        # get the service-base ref collection
        service_base_ref_collection = self.find(
            self.management_node, node, 'service-base', False
        )[0]

        # construct the service item url to be created
        service_item_ref = os.path.join(
            service_base_ref_collection, self.plugin_id
        )

        # execute the inherit command to create a reference of the service item
        # to the node
        self.execute_cli_inherit_cmd(
            self.management_node, service_item_ref, service_item
        )

        # execute the show command
        self.execute_cli_show_cmd(self.management_node, service_item_ref)

        # export service item extension to xml file
        self.execute_cli_export_cmd(
            self.management_node, service_item_ref, filepath
        )

        # check the xml file
        stdout, stderr, rcode = self.run_command(
            self.management_node,
            self.rhc.get_grep_file_cmd(
                filepath, ['litp:{0}-inherit'.format(self.plugin_id)]
            )
        )
        self.assertEqual(0, rcode)
        self.assertNotEqual([], stdout)
        self.assertEqual([], stderr)

    def obsolete_03_p_add_service_item_node_xml(self):
        """
        Obsolete - covered partially (CLI) by AT that replaced test_01 and xml
        side by other AT and UT
            ERIClitpcore/ats/testset_story5277/\
                test_01_p_services_collection_exists.at
        Description:
        Given a LITP deployment, when a user loads a valid XML file, that
        defines a valid service item, in the LITP model with valid
        configuration parameters, the service item will be create in the model
        for the given node.

        Pre-Requisites:
            1.  A running litpd service

        Risks:
            1.  Once a plugin/extension package is installed, it cannot be
                removed

        Pre-Test Steps:
            1.  Create a new dummy extension as described in the LITP 2 SDK
            2.  Edit the extension to extend service-base and be a child of
                services collection with a few properties
            3.  Build and install the extension package

        Steps:
            1.  Execute the CLI load command to create the service item in the
                LITP model
            2.  Execute the CLI load command to subclass the service item to
                the node

        Restore Steps:
            1.  Remove the XML files from the test node
            2.  Execute the CLI remove command to remove the inherited service
                item from the node
            3.  Execute the CLI remove command to remove the service item from
                /software/services
            4.  Check items no longer exist in the mode

        Result:
        Creating the dummy service item, through the use of the dummy extension
        and XML files, must be successful.
        """

        # install the service item type extension package
        self._install_item_extension()

        # copy required test xml files
        self._copy_xml_files(
            [
                '{0}_service_item.xml'.format(self.plugin_id),
                '{0}_service_ref.xml'.format(self.plugin_id)]
        )

        # get the service-base collection from /software
        service_base_collection = self.find(
            self.management_node, '/software', 'service-base', False
        )[0]

        # construct the filepath
        filepath = os.path.join(
            self.filepath, '{0}_service_item.xml'.format(self.plugin_id)
        )

        # execute the load command
        self.execute_cli_load_cmd(
            self.management_node, service_base_collection, filepath
        )

        # execute the show command
        self.execute_cli_show_cmd(
            self.management_node,
            os.path.join(service_base_collection, self.plugin_id)
        )

        # get a node from the model
        node = self.find(self.management_node, '/deployments', 'node')[0]

        # get the service-base ref collection
        service_base_ref_collection = self.find(
            self.management_node, node, 'service-base', False
        )[0]

        # construct the filepath
        filepath = os.path.join(
            self.filepath, '{0}_service_ref.xml'.format(self.plugin_id)
        )

        # execute the load command
        self.execute_cli_load_cmd(
            self.management_node, service_base_ref_collection, filepath
        )

        # execute the show command
        self.execute_cli_show_cmd(
            self.management_node,
            os.path.join(service_base_collection, self.plugin_id)
        )
