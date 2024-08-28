#!/usr/bin/env python

'''
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     Feb 2016
@author:    Terry Farrell
@summary:   Wrong order when uninstalling package and umount directory
            ran on same plan because task ordering does not deconfigure
            in the opposite order to configure LITPCDS-13019
'''

import test_constants as consts
from litp_generic_test import GenericTest, attr
import litp_cli_utils


class Bug13019(GenericTest):

    '''
    Wrong order when uninstalling package and umount directory
    ran on same plan because task ordering does not deconfigure
    in the opposite order to configure LITPCDS-13019
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
        super(Bug13019, self).setUp()

        # 2. Set up variables used in the tests
        self.ms1 = self.get_management_node_filename()
        self.mn1, self.mn2 = self.get_managed_node_filenames()[:2]
        self.cli = litp_cli_utils.CLIUtils()

    def tearDown(self):
        """
        Description:
            Runs after every single test
        Actions:
            1. Ensure true is turned on after test run
            2. Call superclass teardown
        Results:
            Items used in the test are cleaned up and the
        """
        super(Bug13019, self).tearDown()

    @attr('all', 'revert', 'bug13019', 'bug13019_tc01')
    def test_01_p_remove_service_and_its_filesystem_same_plan(self):
        """
        @tms_id: litpcds_13019_tc01
        @tms_requirements_id: LITPCDS-12270
        @tms_title: Test removing a service & it's filesystem in the same
            plan.
        @tms_description:
            Verify that when a user removes a mysql package, while the
            mysqld service is running and the mount point is deleted
            from the file system which the service is using, so that no
            circular dependency occurs.
        @tms_test_steps:
         @step: Create mysql package item.
         @result: Item created successfully.
         @step: Inherit mysql package item on to node 1.
         @result: Item inherited successfully.
         @step: Create a source 'file-system' item type to mount mysql service.
         @result: Item created successfully.
         @step: Create and run the plan.
         @result: Plan run successfully.
         @step: Start mysql service on node1 as root.
         @result: Service starts without error.
         @step: Assert mysql service is using node1 mount point.
         @result: Mysql service is using node1 mount point.
         @step: Remove mysql package from node.
         @result: Mysql package removed successfully from node.
         @step: Remove mysql mount point on source item.
         @result: Mysql mount point removed successfully.
         @step: Create and run the plan.
         @result: Plan runs successfully.
         @step: Check mysql service no longer running and available on node 1.
         @result: Mysql service no longer running and available on node 1.
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        mysql_path = '/var/lib/mysql'
        node_one_url = self.find(self.ms1, '/deployments/', 'node',
                                 exact_match=True)[0]

        self.log('info', '1. Create mysql package item.')
        software_col_url = self.find(self.ms1, '/software',
                                     'collection-of-software-item')[0]
        software_mysql_url = '{0}/mysql_server'.format(software_col_url)
        package_props = 'name=mariadb-server'
        self.execute_cli_create_cmd(self.ms1, software_mysql_url,
                                    'package', package_props)

        self.log('info', '2. Inherit mysql package item on to node1.')
        node_item_url = self.find(self.ms1,
                                  node_one_url,
                                  'ref-collection-of-software-item',
                                  exact_match=True)[0]
        node_mysql_item = '{0}/mysql_server'.format(node_item_url)
        self.execute_cli_inherit_cmd(self.ms1,
                                     node_mysql_item,
                                     software_mysql_url)
        self.log('info',
            '3. Create a source file-system item type to mount mysql service.')
        source_fs_props = 'mount_point={0} size=200M'.format(mysql_path)
        source_fs_col_url = self.find(self.ms1,
                                    '/infrastructure',
                                    'collection-of-file-system')[0]
        source_fs_mysql_url = '{0}/mysql'.format(source_fs_col_url)
        self.execute_cli_create_cmd(self.ms1,
                                    source_fs_mysql_url,
                                    'file-system',
                                    source_fs_props)

        self.log('info', '4. Create and run the plan.')
        self.run_and_check_plan(self.ms1, consts.PLAN_COMPLETE, 10)

        self.log('info', '5. Start mysql service on node1 as root.')
        self.start_service(self.mn1, 'mariadb')

        self.log('info', '6. Assert mysql service is using node1 mount point.')
        std_out = self.run_command(self.mn1,
                                   "{0} | {1} mysql".format(
                                        consts.LSOF_PATH, consts.GREP_PATH),
                                   su_root=True,
                                   default_asserts=True)[0]
        self.assertTrue(self.is_text_in_list(mysql_path, std_out))

        self.log('info', '7. Remove mysql package from the node.')
        self.execute_cli_remove_cmd(self.ms1, node_mysql_item)

        self.log('info', '8. Remove mysql mount point on source item.')
        self.execute_cli_update_cmd(self.ms1,
                                    source_fs_mysql_url,
                                    'mount_point',
                                    action_del=True)

        self.log('info', '9. Create and run the plan')
        self.run_and_check_plan(self.ms1, consts.PLAN_COMPLETE, 10)

        self.log('info',
           '10. Check that mysql service is no longer running and available'\
           ' on node1.')
        stdout, _, _ = self.start_service(self.mn1,
                                          'mariadb',
                                          assert_success=False,
                                          su_root=True)
        self.assertEqual('Failed to start mariadb.service: Unit not found.',
                                          stdout[0])
