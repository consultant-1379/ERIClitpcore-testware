'''
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     October 2013
@author:    Ares
@summary:   Integration test for LITPCDS-4026
            Agile:
                Epic: N/A
                Story: LITPCDS-4026
                Sub-Task: N/A
'''

import os
from litp_generic_test import GenericTest, attr
from rest_utils import RestUtils
from json_utils import JSONUtils


class Story4026(GenericTest):
    """As a LITP Developer I want subclass model items so that I can more
       efficiency create populated items but with their own configurable
       properties"""

    def setUp(self):
        """Runs before every test to perform required setup"""
        super(Story4026, self).setUp()
        self.management_node = self.get_management_node_filename()
        self.ms_ip = self.get_node_att(self.management_node, 'ipv4')
        self.rest = RestUtils(self.ms_ip)
        self.item = 'story4026'

    def tearDown(self):
        """Runs after every test to perform required cleanup/teardown"""
        super(Story4026, self).tearDown()

    @staticmethod
    def _stringify_dict(props_dict):
        """takes:    {'a':1, 'b':2, 'c':3} <type dict>
           returns:  "{'a':'1', 'b':'2', 'c':'3'}" <type str>
        """
        return ",".join([
            """ "{0}": "{1}" """.format(key, str(val))
            for key, val in props_dict.iteritems()
        ])

    def execute_rest_remove_req(self, path, expect_positive=True,
                                invalid_request=False):
        """execute a REST DELETE to remove a model item
        """
        stdout, stderr, status = self.rest.delete(path)

        # attempt to retrieve payload from REST interface
        payload = JSONUtils().load_json(stdout)

        # assert return values
        if expect_positive:
            self.assertNotEqual(None, payload)
            self.assertFalse('messages' in payload)
        if not expect_positive:
            if invalid_request:
                self.assertEqual(None, payload)
            else:
                self.assertNotEqual(None, payload)
                self.assertTrue('messages' in payload)

        return stdout, stderr, status

    def execute_rest_inherit_req(self, path, source_path, props=None,
                                 expect_positive=True, invalid_request=False):
        """execute a REST POST to inherit a model item from source path
        """
        split_path, path_id = path.rsplit("/", 1)

        if props is None:
            props = {}

        # build REST create JSON
        if props:
            msg_data = """{{
                "id": "{0}",
                "inherit": "{1}",
                "properties": {{ {2} }}
            }}""".format(path_id, source_path, self._stringify_dict(props))
        else:
            msg_data = """{{
                "id": "{0}",
                "inherit": "{1}"
            }}""".format(path_id, source_path)

        stdout, stderr, status = self.rest.post(
            split_path, self.rest.HEADER_JSON, msg_data
        )

        # attempt to retrieve payload from REST interface
        payload = JSONUtils().load_json(stdout)

        # assert return values
        if expect_positive:
            self.assertNotEqual(None, payload)
            self.assertFalse('messages' in payload)
        if not expect_positive:
            if invalid_request:
                self.assertEqual(None, payload)
            else:
                self.assertNotEqual(None, payload)
                self.assertTrue('messages' in payload)

        return stdout, stderr, status

    def execute_rest_update_req(self, path, props,
                                expect_positive=True, invalid_request=False):
        """execute a REST PUT request to update a model item
        """
        # build REST update JSON
        msg_data = """{{
            "properties": {{ {0} }}
        }}""".format(self._stringify_dict(props))

        stdout, stderr, status = self.rest.put(
            path, self.rest.HEADER_JSON, msg_data
        )

        # attempt to retrieve payload from REST interface
        payload = JSONUtils().load_json(stdout)

        # assert return values
        if expect_positive:
            self.assertNotEqual(None, payload)
            self.assertFalse('messages' in payload)
        if not expect_positive:
            if invalid_request:
                self.assertEqual(None, payload)
            else:
                self.assertNotEqual(None, payload)
                self.assertTrue('messages' in payload)

        return stdout, stderr, status

    def add_package_model_item(self):
        """create a package-list/package in the software model"""

        # software-item collection path
        software_items = self.find(
            self.management_node, '/software', 'software-item', False
        )[0]

        # package-list create path
        package_list = os.path.join(
            software_items, '{0}_packages'.format(self.item)
        )

        # create package-list
        self.execute_cli_create_cmd(
            self.management_node, package_list, 'package-list',
            'name=\'{0}_packages\''.format(self.item)
        )

        # package create path
        package = os.path.join(
            package_list, 'packages/{0}'.format(self.item)
        )

        # create package
        self.execute_cli_create_cmd(
            self.management_node, package, 'package', 'name=\'finger\''
        )

        return package_list, package

    @attr('cdb_priority2', 'all', 'story4026', 'story4026_tc05')
    def test_05_p_rest_inherit_command(self):
        """
        Description:
            We test the inherit command over the REST interface
        Steps:
            1. create a new package under /software
            2. use inherit over REST interface
            3. update a property under an inherit
            4. remove the inherit path over REST
        Result:
            We assert that the inherit command functions correctly
            directly over the REST interface
        """
        # build paths for test
        finger_path = self.find(
            self.management_node, "/software", "software-item", False
        )[0]
        ms_item_path = self.find(
            self.management_node, "/ms", "software-item", False, find_refs=True
        )[0]
        base_finger_path = os.path.join(finger_path, "finger")
        ms_finger_path = os.path.join(ms_item_path, "finger")

        # 1. create a new package
        self.execute_cli_create_cmd(
            self.management_node, base_finger_path,
            "package", "name=finger"
        )

        # 2. run inherit using REST interface
        self.execute_rest_inherit_req(ms_finger_path, base_finger_path)

        # 3. update a property using REST interface
        self.execute_rest_update_req(ms_finger_path, {'name': 'finger3'})

        # 4. run remove inherit using REST interface
        self.execute_rest_remove_req(ms_finger_path)

    @attr('cdb_priority2', 'all', 'story4026', 'story4026_tc10')
    def test_10_p_inherit_cmd_update_model_item_property_rest(self):
        """
        Description:
            After creating a reference to a created model item, using the new
            CLI inherit command, if the property of a model item is updated
            using a REST PUT, then that update will be reflected on the
            reference also.

        Steps:
            1.  Execute the cli create command for a package-list in the model
            2.  Execute the cli create command for a package item child of the
                created package-list
            3.  Execute the new cli inherit command for the package-list to
                create a reference item on a node
            4.  Execute a REST PUT command on a property of the package-list
                model item
            5.  Execute the cli show command and check the property is also
                changed on the reference item

        Result:
            The property that is updated on the model item must also reflect
            the update
        """

        # create package-list/package
        package_list, package = self.add_package_model_item()

        # get a node from model
        node = self.find(self.management_node, '/deployments', 'node')[0]

        # path to be inherited
        inherited_path = os.path.join(
            node, 'items/{0}_packages'.format(self.item)
        )

        # execute the cli inherit command to create the inherited reference
        self.execute_cli_inherit_cmd(
            self.management_node, inherited_path, package_list
        )
        self.assertEqual(
            package_list,
            self.execute_show_data_cmd(
                self.management_node, inherited_path, 'inherited from'
            )
        )

        # update property using REST interface
        self.execute_rest_update_req(package, {'name': 'firefox'})

        # package name property value for inherited reference path must remain
        # unchanged, after original path value is updated
        inherited_path_child = os.path.join(
                inherited_path, 'packages/{0}'.format(self.item)
        )
        self.assertEqual(
            self.execute_show_data_cmd(
                self.management_node, package, 'name'
            ),
            self.execute_show_data_cmd(
                self.management_node, inherited_path_child, 'name'
            ).strip(' [*]')
        )

    @attr('cdb_priority2', 'all', 'story4026', 'story4026_tc11')
    def test_11_p_inherit_cmd_update_reference_item_property_rest(self):
        """
        Description:
            After creating a reference to a created model item, using the new
            CLI inherit command, if the property of the reference item is
            updated with REST PUT, then that update will not be reflected on
            the model item and the property value will remain unchanged.
            If the property on the original model item is then updated, then
            the reference item property will retain the user specified value
            from the previous update however, any references that were not
            updated previously, will reflect the model item change still.

        Steps:
            1.  Execute the cli create command for a package-list in the model
            2.  Execute the cli create command for a package item child of the
                created package-list
            3.  Execute the new cli inherit command for the package-list to
                create a reference item on a node
            4.  Execute the new cli inherit command for the package-list to
                create a reference item on a second node
            5.  Execute a REST PUT update command on a property of the
                package-list reference item
            6.  Execute the cli show command on the original package-list model
                item and check the same property has not been changed
            7.  Execute a REST PUT update command on the same property on the
                original package-list model item
            8.  Execute the cli show command on the referenced item again and
                check the property value hasn't changed
            9.  Execute the cli show command on the second node's referenced
                item again and check the property value has changed

        Result:
            The property that is updated on a referenced item must not be
            propagated back to the original model item and, if that same
            property is updated on the model item, since the property on the
            reference was changed previously, the value for the reference
            remains unchanged. Any reference on another node, that was not
            previously updated, will reflect the update still.
        """

        # create package-list/package
        package_list, package = self.add_package_model_item()

        # get nodes from model
        nodes = self.find(self.management_node, '/deployments', 'node')

        # list of inherited reference paths
        inherited_paths = list()

        # for each node inherit from package-list path, creating reference
        for node in nodes:
            # path to be inherited
            inherited_path = os.path.join(
                node, 'items/{0}_packages'.format(self.item)
            )
            # save the inherited reference paths for later use
            inherited_paths.append(inherited_path)
            # execute the cli inherit command to create the inherited reference
            self.execute_cli_inherit_cmd(
                self.management_node, inherited_path, package_list
            )
            # check path referenced, no properties overwritten
            stdout_dict, _, _ = self.execute_cli_show_cmd(
                self.management_node, inherited_path, '-j'
            )
            self.assertEqual(
                package_list,
                self.execute_show_data_cmd(
                    self.management_node, inherited_path, 'inherited from'
                )
            )

        # reference path to be updated via REST
        update_path = os.path.join(
            inherited_paths[0], 'packages/{0}'.format(self.item)
        )

        # update property using REST interface
        self.execute_rest_update_req(update_path, {'name': 'firefox'})

        # get json dict for updated reference path
        stdout_dict, _, _ = self.execute_cli_show_cmd(
            self.management_node, update_path, '-j'
        )
        # check property name is overwritten
        # properties overwritten list must not be empty
        self.assertNotEqual([], stdout_dict['properties-overwritten'])
        self.assertEqual(
            'firefox',
            self.execute_show_data_cmd(
                self.management_node, update_path, 'name'
            )
        )
        # package name property value of unchanged inherited reference paths
        # must not match updated reference path and must be equal to original
        # path inherited from
        for inherited_path in inherited_paths:
            inherited_path_child = os.path.join(
                inherited_path, 'packages/{0}'.format(self.item)
            )
            if inherited_path_child == update_path:
                self.assertNotEqual(
                    self.execute_show_data_cmd(
                        self.management_node, update_path, 'name'
                    ).strip(' [*]'),
                    self.execute_show_data_cmd(
                        self.management_node, package, 'name'
                    )
                )
            else:
                self.assertEqual(
                    self.execute_show_data_cmd(
                        self.management_node, package, 'name'
                    ),
                    self.execute_show_data_cmd(
                        self.management_node, inherited_path_child, 'name'
                    ).strip(' [*]')
                )

        # update property using REST interface
        self.execute_rest_update_req(package, {'name': 'tftp'})

        # package name property value of inherited reference paths not
        # overwritten must change to the updated value of original path but
        # updated reference path that was overwritten previously will not
        for inherited_path in inherited_paths:
            inherited_path_child = os.path.join(
                inherited_path, 'packages/{0}'.format(self.item)
            )
            if inherited_path_child != update_path:
                self.assertEqual(
                    self.execute_show_data_cmd(
                        self.management_node, package, 'name'
                    ),
                    self.execute_show_data_cmd(
                        self.management_node, inherited_path_child, 'name'
                    ).strip(' [*]')
                )
                self.assertNotEqual(
                    self.execute_show_data_cmd(
                        self.management_node, update_path, 'name'
                    ),
                    self.execute_show_data_cmd(
                        self.management_node, inherited_path_child, 'name'
                    ).strip(' [*]')
                )
