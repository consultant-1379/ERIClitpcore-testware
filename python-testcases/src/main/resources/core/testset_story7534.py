'''
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     October 2015
@author:    Maurizio / Marco Gibboni
@summary:   Integration test for LITPCDS-7534
            Agile:
                Epic: N/A
                Story: LITPCDS-7534:
                       As a LITP User, I want the XSD validation to allow
                       for property annotation, so that I can use external
                       tools to extract semantic information about
                       these properties.
                Sub-Task: N/A
'''

import os
import re
from litp_generic_test import GenericTest, attr
from xml_utils import XMLUtils


class Story7534(GenericTest):
    """
    LITPCDS-7534:
    As a LITP User, I want the XSD validation to allow for property annotation,
    so that I can use external tools to extract semantic information about
    these properties.
    """

    def setUp(self):
        """runs before every test to perform required setup"""
        # call super class setup
        super(Story7534, self).setUp()
        self.ms_node = self.get_management_node_filename()
        self.item_type = 'story7534'
        self.xml_utils = XMLUtils()
        self.original_xml = '/tmp/exported.xml'
        self.annotated_xml = '/tmp/edited.xml'
        self.processed_xml = '/tmp/exported2.xml'
        self.errors = []
        self.xml_path = "/tmp/xml_path/"
        self.xml_test = 'test.xml'
        self.xml_validator_prgm = '/opt/ericsson/nms/litp/bin/xmlvalidator.py'
        self.xsd_schema = '/opt/ericsson/nms/litp/share/xsd/litp.xsd'
        self.xsd_validation_cmd = '{0} {1} {2}'\
                                        .format(self.xml_validator_prgm,\
                                                self.xml_path + self.xml_test,\
                                                self.xsd_schema)
        self.common_valid_values = ['%%VALUE_01%%',
                                    '%%VALUE%%',
                                    '%%VALUE.01%%',
                                    '%%VALUE-01%%']
        self.common_invalid_values = ['%%V+V%%',
                                    '%%STR_%%VALUE%%',
                                    '%%%%',
                                    'bond.%%VAL%%',
                                    '%%VAL1%%VAL2%%']

        # Items to check
        self.items = {'alias': {'properties': [{'name': 'address',
                                                    'valid': [],
                                                    'invalid': []
                                                    }]
                                },
                        'dns-client': {'properties': [{'name': 'search',
                                                    'valid': [],
                                                    'invalid': []
                                                    }]
                                },
                        'route': {'properties': [{'name': 'subnet',
                                                    'valid': [],
                                                    'invalid': []
                                                    },
                                                    {'name': 'gateway',
                                                    'valid': [],
                                                    'invalid': []
                                                    }],
                                },
                        'bond': {'properties': [{'name': 'ipaddress',
                                                    'valid': [],
                                                    'invalid': []
                                                    }]
                                },
                        'ms': {'properties': [{'name': 'hostname',
                                                    'valid': ['MS1'],
                                                    'invalid': []
                                                    }]
                                },
                        'node': {'properties': [{'name': 'hostname',
                                                    'valid': [],
                                                    'invalid': []
                                                    }]
                                },
                        'eth': {'properties': [{'name': 'ipaddress',
                                                    'valid': ['10.10.11.233'],
                                                    'invalid': []
                                                    },
                                                    {'name': 'device_name',
                                                    'valid': [],
                                                    'invalid': []
                                                    },
                                                    {'name': 'macaddress',
                                                    'valid': [],
                                                    'invalid': []
                                                    }]
                                },
                        'bridge': {'properties': [{'name': 'ipv6address',
                                                    'valid': ['2001:1b70:' +\
                                                        '82a1:0103::43/64'],
                                                    'invalid': []
                                                    },
                                                    {'name': 'ipaddress',
                                                    'valid': ['192.168.0.43'],
                                                    'invalid': []
                                                    },
                                                    {'name': 'device_name',
                                                    'valid': [],
                                                    'invalid': []
                                                    }]
                                },
                        'network': {'properties': [{'name': 'subnet',
                                                    'valid': [],
                                                    'invalid': []
                                                    }]
                                },
                        'disk': {'properties': [{'name': 'uuid',
                                                    'valid': [],
                                                    'invalid': []
                                                    }]
                                },
                        'blade': {'properties': [{'name': 'system_name',
                                                    'valid': ['SYS1'],
                                                    'invalid': []
                                                    }]
                                },
                        'bmc': {'properties': [{'name': 'ipaddress',
                                                    'valid': ['10.10.11.233'],
                                                    'invalid': []
                                                    }]
                                }
                    }

    def tearDown(self):
        """runs after every test to perform required cleanup/teardown"""
        # call super class teardown
        super(Story7534, self).tearDown()

    def find_paths(self, search_path_root, item_type, properties):
        '''
        Description:
            Parse litp model tree starting from given search path root
            and find all paths of the given type that has required
            properties
        Args:
            search_path_root (str): search starting point
            item_type (str): litp item type to search for
            properties (list): properties that a path must have
        Actions:
            1. Get list of path of the given type
            2. for each type
               2.1 Add to list of found paths if all required property are
                   defined for that item
        Results:
            Return list of paths that where found
        '''

        properties_set = set(properties)
        paths = []
        items = self.find(self.ms_node, search_path_root, item_type)
        for item in items:
            item_props = self.get_props_from_url(self.ms_node, item)
            if set(properties_set).issubset(set(item_props.keys())):
                paths.append(item)
        self.assertNotEqual(len(paths), 0,
            'No path found for item type {0}'.format(item_type))

        return paths

    def assert_load_xml(self, path, flag, expected_error_type,
                        unwanted_error_type=None):
        '''
        Description:
            Load xml file with annotated properties value into model
            and verify that expected error are thrown
        Args:
            path (str): path to load
            flag (str): the litp load command flag(--merge or --replace)
            error_type (st): the expected error
        Actions:
            1. Get parent path
            2. Execute litp load command
            3. Check that expected ValidationError are thrown
            4. Check that path is included on error message
            5. Check that unwanted XMLValidationError is not present
            5. Check the amount of errors found matches what expected
        Results:
        '''

        parent_path = self.get_parent_path(path)
        _, stderr, _ = self.execute_cli_load_cmd(self.ms_node,
                                 parent_path,
                                 self.annotated_xml,
                                 flag,
                                 expect_positive=False)

        # Verify correct error type is thrown
        self.assertTrue(self.is_text_in_list(expected_error_type, stderr),
            'Unexpected error type found')
        # Verify path is included on error message
        self.assertTrue(self.is_text_in_list(path, stderr),
            'Path not found on error')
        # Verify unwanted error type is not present
        if unwanted_error_type != None:
            self.assertFalse(self.is_text_in_list(unwanted_error_type, stderr),
                'Unwanted error type found')
        self.assertTrue(len(stderr) in [2, 4, 6],
            'Unexpected number of lines found on error output')

    def assert_model_change(self, path):
        '''
        Description:
            Verify that attempt to load xml file with annotated property
            values did not cause changes to current litp model
        Args:
            path (str): path to load
        Actions:
            1. Export path to xml file
            2. Compare new and original xml file
            3. Check that they are equal
        Results:
        '''

        self.execute_cli_export_cmd(self.ms_node, path, self.processed_xml)
        cmd = '/usr/bin/diff {0} {1}'.format(self.original_xml,
                                             self.processed_xml)
        stdout, _, _ = self.run_command(self.ms_node, cmd)
        self.assertEqual([], stdout)

    def _find_any_value_properties(self, item):
        '''
        Description:
            Retrieve item type info from litp model and return a list
            that contain all the properties that accept any value
        '''
        properties_anyvalue = []
        cmd = "/usr/bin/litp show -p /item-types/" + item
        std_out, _, _ = self.run_command(self.ms_node, cmd,\
                                                        default_asserts=True)
        pick_next_prop_name = False
        for detail in reversed(std_out):
            if "regex:" in detail:
                if '^.*$' in detail:
                    pick_next_prop_name = True
            if "name:" in detail and pick_next_prop_name:
                pick_next_prop_name = False
                properties_anyvalue.append(detail.split("name: ")[1])
        return properties_anyvalue

    def _change_xml_values(self, item, prop_name, new_value, litp_path):
        '''
        Description:
            Modify xml values with passed values and copy new file to MS.
            The path of new file will always be '/tmp/test.xml' and it will
            overwrite the previous file created.
        '''
        changed = False
        local_xml = "/tmp/test.xml"
        xml = self.get_file_contents(self.ms_node,\
                                                self.xml_path + item + '.xml')
        with open(local_xml, 'w') as test_xml:
            for line in xml:
                if re.search(prop_name, line):
                    changed = True
                    original_line = '<{0}>.*</{0}>'.format(prop_name)
                    new_line = '<{0}>{1}</{0}>'.format(prop_name, new_value)
                    line = re.sub(original_line, new_line, line)
                test_xml.write(line)
            test_xml.write('<!-- {0} -->\n'.format(litp_path))
        self.copy_file_to(self.ms_node, local_xml, self.xml_path,\
                                        root_copy=True, add_to_cleanup=False)
        return changed

    def _xml_validation(self, item, props_to_check, item_url,\
                                                        expect_valid=True):
        '''
        Description:
            Run xml validator script passing
            xml with new values and xsd schema.
            If the new value is valid the script must return an empty list,
            otherwise it must return a list with the error log.
        '''
        if expect_valid:
            checklist = props_to_check['valid']
        else:
            checklist = props_to_check['invalid']
        for value in checklist:
            # Modify item xml, with valid value, always
            # starting fromthe one previously exported
            changed = self._change_xml_values(item, props_to_check['name'],\
                                            value, item_url)
            # If xml has changed then run xml validator script with
            # new xml to check valid/invalid value
            if changed:
                self.get_file_contents(self.ms_node,\
                                    self.xml_path + self.xml_test)
                std_out, std_err, rcode =\
                            self.run_command(self.ms_node,\
                                        self.xsd_validation_cmd,\
                                        su_root=True)
                if expect_valid:
                    if std_out:
                        self.errors.append({'item': item,
                                        'valid_value': value,
                                        'property': props_to_check['name'],
                                        'error_description':\
                                                    'Unexpected error found'})
                else:
                    if not std_out:
                        self.errors.append({'item': item,
                                        'invalid_value': value,
                                        'property': props_to_check['name'],
                                        'error_description':\
                                                'Expected error not found'})
                self.assertEqual([], std_err)
                self.assertEqual(0, rcode)
            else:
                self.log('info', "Property '{0}' hasn't been found on '{1}'"\
                                 .format(props_to_check['name'], item))

    def _print_summary(self):
        '''
        Description:
        Build and return error list for test_01
        '''
        summary = []
        if self.errors:
            for error in self.errors:
                summary.append("-" * 40)
                for key, val in error.iteritems():
                    summary.append("{0}: {1}".format(key, val))
        return summary

    @attr('manual-test', 'revert', 'story7534', 'story7534_tc01')
    def test_01_p_offline_validation(self):
        '''
        Description:
            Assert that item property values in xml
                are correctly valid or invalid
            This test covers the following test cases specified in the
                story:
                test_01_p_offline_validation_on_annotation_enabled_properties
                test_02_p_offline_validation_on_annotation_enabled_properties
                test_03_n_offline_validation_on_annotation_disabled_properties
                test_04_n_offline_validation_invalid_characters_used_
                                                            within_wild_cards
                test_05_n_offline_validation_empty_annotation
                test_06_n_offline_validation_annotation_is_only_part_of_
                                                                    the_value
                test_09_n_load_annotated_value_with_accept_all_regex
        Actions:
            1. Check that xml path doesn't exist
            1b. and if xml path already exists then delete the folder
            2. Create xml path
            3. Loop through the items to check
            4. Find litp items by item type
            5. Pick the element on the list with more properties
               required in this test
            5b. and export xml for that item(url)
            6. Loop through item properties to check
               Skip properties that accept any value (regex: ^.*$)
            7. Add both common valid and invalid values to check
               against property
            8. Assert that there aren't errors otherwise show them
        '''
        path_exists = self.remote_path_exists(self.ms_node,\
                                            self.xml_path, expect_file=False)
        # 1. Check that xml path doesn't exist
        if path_exists:
            # 1b. and if xml path already exists then delete the folder
            self.remove_item(self.ms_node,\
                                            self.xml_path, su_root=True)
        # 2. Create xml path
        self.create_dir_on_node(self.ms_node, self.xml_path)
        # 3. Loop through the items to check
        for item in self.items:
            # 4. Find litp items by item type
            item_urls = self.find(self.ms_node, "/", item)
            if not item_urls:
                self.log('info', "There isn't an item '{0}'".format(item) +\
                                    "in this environment")
            else:
                # 5. Pick the element on the list with more properties
                #    required in this test
                props_to_check = len(self.items[item]['properties'])
                best_props_found = 0
                item_to_check = item_urls[0]
                for item_url_found in item_urls:
                    props_found = 0
                    item_props = self.get_props_from_url(self.ms_node,\
                                                            item_url_found)
                    for prop in self.items[item]['properties']:
                        if prop['name'] in item_props:
                            props_found = props_found + 1
                        if props_found > best_props_found:
                            item_to_check = item_url_found
                            best_props_found = props_found
                    if best_props_found == props_to_check:
                        break
                # 5b. and export xml for that item(url)
                exp_cmd = self.cli.get_xml_export_cmd(item_to_check,\
                                file_path=self.xml_path + item + '.xml')
                self.run_command(self.ms_node, exp_cmd, su_root=True,\
                                                    default_asserts=True)
                self.log('info', "Checking xml values for item type '" +\
                                 "{0}'".format(item))
                # 6. Loop through item properties to check
                #    Skip properties that accept any value (regex: ^.*$)
                properties_anyvalue = self._find_any_value_properties(item)
                for prop in self.items[item]['properties']:
                    if prop['name'] in properties_anyvalue:
                        self.log('info', "All values are allowed. " +\
                                "Skipping property '{0}' for item type '{1}'"\
                                .format(prop['name'], item))
                        continue
                    # 7. Add both common valid and invalid values to check
                    #       against property
                    prop['valid'].extend(self.common_valid_values)
                    prop['invalid'].extend(self.common_invalid_values)
                    self._xml_validation(item, prop, item_to_check)
                    self.log('info', "Xml valid values have been checked " +\
                                "against property '{0}' for item type '{1}'"\
                                .format(prop['name'], item))
                    self._xml_validation(item, prop, item_to_check,\
                                                expect_valid=False)
                    self.log('info', "Xml invalid values have been checked " +\
                                "against property '{0}' for item type '{1}'"\
                                .format(prop['name'], item))
                self.log('info', "Xml values for item type '" +\
                                 "{0}' completed".format(item))
        # 8. Assert that there aren't errors otherwise show them
        self.assertEqual([], self.errors, '\n'.join(self._print_summary()))

    @attr('all', 'revert', 'story7534', 'story7534_tc07')
    def test_07_n_load_xml_with_annotated_values(self):
        """
        Description:
            Verify that when an xml file that contains site specific properties
            with valid annotated values is loaded by LITP, validation error
            instead of XML error are returned and no changes to LITP
            model are applied
        Actions:
            1. Define list of properties to test and the appropriate litp item
               type available on current LITP model
            2. For each property
             2.0  Backup current path
             2.1. Export XML file for the corresponding item type
             2.2  Verify that no "%%" is present on any property value
             2.3  Edit XML file by setting valid property value using
                  annotation
                  (That is using "%%" wild cards to delimit annotated values)
             2.4  Load XML file into LITP using the --merge flag
             2.5  Load XML file into LITP using the --replace flag
             2.6  Load XML file into LITP with neither --merge or --replace
        Result:
            1. Verify that LITP fails with a ValidationError
            2  verify that only 1 error is thrown
            3. Verify that no changes were applied to current LITP model
        """
        paths_to_test = dict()

        # Defining paths, properties and values to test
        nic_paths = self.find_children_of_collect(self.ms_node,
                                                  '/deployments',
                                                  "network-interface")
        props = dict()
        for mypath in nic_paths:
            path_props = self.get_props_from_url(self.ms_node, mypath)
            if 'ipaddress' in path_props.keys():
                props['ipaddress'] = ['%%IP01%%', '%%IP_01%%',
                                      '%%IP-01%%', '%%IP.01%%']
                paths_to_test[mypath] = props
                break
        self.assertNotEqual(len(props.keys()), 0, 'Path not found')

        props = dict()
        for mypath in nic_paths:
            path_props = self.get_props_from_url(self.ms_node, mypath)
            if 'ipv6address' in path_props.keys():
                props['ipv6address'] = ['%%IP01%%']
                paths_to_test[mypath] = props
                break
        self.assertNotEqual(len(props.keys()), 0, 'Path not found')

        nic_paths = self.find_children_of_collect(self.ms_node,
                                                  '/infrastructure',
                                                  "network")
        props = dict()
        for mypath in nic_paths:
            path_props = self.get_props_from_url(self.ms_node, mypath)
            if 'subnet' in path_props.keys():
                props['subnet'] = ['%%Subnet_01%%']
                paths_to_test[mypath] = props
                break
        self.assertNotEqual(len(props.keys()), 0, 'Path not found')

        path = self.find_paths('/infrastructure', 'disk',
                               ['uuid'])[0]
        self.assertTrue(self.backup_path_props(self.ms_node, path))
        props = dict()
        props['uuid'] = ['%%DISK_01%%']
        paths_to_test[path] = props

        path = self.find_paths('/infrastructure', 'blade',
                               ['system_name'])[0]
        self.backup_path_props(self.ms_node, path)
        props = dict()
        props['system_name'] = ['%%SYS_01%%']
        paths_to_test[path] = props

        path = '/ms'
        self.backup_path_props(self.ms_node, path)
        props = dict()
        props['hostname'] = ['%%HOST_01%%']
        paths_to_test[path] = props

        # Looping through list of items to test
        for each_path, test_param in paths_to_test.iteritems():
            # Exporting initial path to XML
            self.execute_cli_export_cmd(self.ms_node,
                    each_path, self.original_xml)
            contents = self.get_file_contents(self.ms_node, self.original_xml)

            # Looping through properties for each path
            for each_prop, values in test_param.iteritems():
                # Replacing property values
                for value in values:
                    # Reloading initial xml_obj
                    xml_obj = self.xml_utils.load_xml_dataobject(contents)
                    for child in xml_obj:
                        if child.tag == each_prop:
                            self.log('info', 'Path {0}'.format(each_path))
                            self.log('info', 'Property {0}'.format(each_prop))
                            self.log('info', 'Replacing {0} with {1}'.format(
                                                child.text, value))
                            child.text = value

                            # Save modified XML tree into XML file and
                            self.assertTrue(self.remove_item(self.ms_node,
                                self.annotated_xml), "Could not delete file")

                            xml_string = self.xml_utils.output_xml_dataobject(
                                                                    xml_obj)
                            self.assertTrue(
                                self.create_file_on_node(self.ms_node,
                                            self.annotated_xml,
                                            xml_string.split("\n")))

                            # Verify load with merge
                            self.assert_load_xml(each_path, '--merge',
                                                 'ValidationError',
                                                 'InvalidXMLError')
                            self.assert_model_change(each_path)

                            # Verify load with replace
                            self.assert_load_xml(each_path, '--replace',
                                                 'ValidationError',
                                                 'InvalidXMLError')
                            self.assert_model_change(each_path)

    @attr('all', 'revert', 'story7534', 'story7534_tc08')
    def test_08_n_load_xml_with_invalid_annotated_values(self):
        """
        Description:
            Verify that when an xml file that contains site specific
            properties with invalid annotated values is loaded by LITP
            XML validation error are returned and no changes to LITP model
            are applied
        Actions:
            1. Define list of properties to test and the appropriate litp item
               type available on current LITP model
            2. For each property
             2.1. Export XML file for the corresponding item type
             2.2  Verify that no "%%" is present on any property value
             2.3  Edit XML file by setting invalid property value within
                  annotation wild cards
             2.4  Load XML file into LITP using the --merge flag
             2.5  Load XML file into LITP using the --replace flag
             2.6  Load XML file into LITP with neither --merge or --replace
        Result:
            1. Verify that LITP fails with a InvalidXMLError
            2  verify that only 1 error is thrown
            3. Verify that no changes were applied to current LITP model
        """
        paths_to_test = dict()

        nic_paths = self.find_children_of_collect(self.ms_node,
                                                  '/deployments',
                                                  "network-interface")
        props = dict()
        for mypath in nic_paths:
            path_props = self.get_props_from_url(self.ms_node, mypath)
            if 'ipaddress' in path_props.keys():
                props['ipaddress'] = ['%%IP+01%%', 'ip.%%01%%', '%%ip%%01%%']
                paths_to_test[mypath] = props
                break
        self.assertNotEqual(len(props.keys()), 0, 'Path not found')

        path = self.find_paths('/deployments', 'node',
                               ['hostname'])[0]
        self.assertTrue(self.backup_path_props(self.ms_node, path))
        props = dict()
        props['hostname'] = ['node_%%node1_IP%%']
        paths_to_test[path] = props

        # Looping through list of items to test
        for each_path, test_param in paths_to_test.iteritems():
            # Exporting initial path to XML
            self.execute_cli_export_cmd(self.ms_node,
                    each_path, self.original_xml)
            contents = self.get_file_contents(self.ms_node, self.original_xml)

            # Looping through properties for each path
            for each_prop, values in test_param.iteritems():
                # Replacing property values
                for value in values:
                    # Reloading initial xml_obj
                    xml_obj = self.xml_utils.load_xml_dataobject(contents)
                    for child in xml_obj:
                        if child.tag == each_prop:
                            self.log('info', 'Path {0}'.format(each_path))
                            self.log('info', 'Property {0}'.format(each_prop))
                            self.log('info', 'Replacing {0} with {1}'.format(
                                                child.text, value))
                            child.text = value

                            # Save modified XML tree into XML file and
                            self.assertTrue(self.remove_item(self.ms_node,
                                self.annotated_xml), "Could not delete file")

                            xml_string = self.xml_utils.output_xml_dataobject(
                                                                    xml_obj)
                            self.assertTrue(
                                self.create_file_on_node(self.ms_node,
                                            self.annotated_xml,
                                            xml_string.split("\n")))

                            # Verify load with merge
                            self.assert_load_xml(each_path, '--merge',
                                                 'InvalidXMLError')
                            self.assert_model_change(each_path)

                            # Verify load with replace
                            self.assert_load_xml(each_path, '--replace',
                                                 'InvalidXMLError')
                            self.assert_model_change(each_path)

    @attr('all', 'revert', 'story7534', 'story7534_tc10')
    def test_10_p_load_xml_with_multiple_annotated_values(self):
        """
        Description:
            Verify that when multiple site-specific properties are set using
            annotated values only Validation errors are thrown
        Actions:
            1. Export current litp model from root
            2. Load story7534_site_specific_properties_root.xml file
                with --merge
            3. Check errors
            4. Load story7534_site_specific_properties_root.xml file
                with --replace
            5. Check errors
            6. Load initial litp model back in
        Result:
            1. Verify that LITP fails predefined set of ValidationErrors
        """

        self.log('info', '1. Backing up current litp model')
        initial_root_xml = '/tmp/root.xml.initial'
        self.execute_cli_export_cmd(self.ms_node, '/', initial_root_xml)

        root_xml_filename = 'story7534_site_specific_properties_root.xml'
        local_filepath = os.path.dirname(__file__)
        local_root_xml = local_filepath + '/xml_files/' + root_xml_filename
        ms_root_xml = '/tmp/' + root_xml_filename

        self.assertTrue(
            self.copy_file_to(self.ms_node, local_root_xml, ms_root_xml),
            'Failed to copy {0} to ms'.format(local_root_xml))

        try:
            self.log('info', '2. Loading root with --merge')
            _, stderr, _ = self.execute_cli_load_cmd(self.ms_node,
                                             '/',
                                             ms_root_xml,
                                             "--merge",
                                             expect_positive=False)

            # 3. Checking that correct number of ValidationError are present
            error_validation_count = 0
            error_request_count = 0
            expected_validation_error_count = 8
            expected_request_error_count = 5
            for line in stderr:
                if re.match(r'ValidationError[a-zA-Z0-9 ":\'_]+%%', line):
                    error_validation_count += 1
                if re.match(r'InvalidRequestError[a-zA-Z0-9 ":\'_]+', line):
                    error_request_count += 1
            self.assertEqual(
                error_validation_count, expected_validation_error_count,
                'Expected {0} ValidationErrors, found {1}'.
                 format(
                    expected_validation_error_count, error_validation_count
                )
            )
            self.assertEqual(
                error_request_count, expected_request_error_count,
                'Expected {0} InvalidRequestErrors, found {1}'.
                 format(
                    expected_request_error_count, error_request_count
                )
            )
            self.assertEqual(len(stderr), 26)

            # 3a Verify unwanted error type is not present
            self.assertFalse(self.is_text_in_list('InvalidXMLError', stderr),
                'Unwanted InvalidXMLError found')

            self.log('info', '3. Loading root with --replace')
            _, stderr, _ = self.execute_cli_load_cmd(self.ms_node,
                                         '/',
                                         ms_root_xml,
                                         '--replace',
                                         expect_positive=False)

            # 5. Checking that correct number of ValidationError are present
            error_validation_count = 0
            error_request_count = 0
            expected_validation_error_count = 8
            expected_request_error_count = 5
            for line in stderr:
                if re.match(r'ValidationError[a-zA-Z0-9 ":\'_]+%%', line) or \
                   re.match('ValidationError[a-zA-Z0-9 ":\'_]+readonly', line):
                    error_validation_count += 1
                if re.match(r'InvalidRequestError[a-zA-Z0-9 ":\'_]+', line):
                    error_request_count += 1
            self.assertEqual(
                error_validation_count, expected_validation_error_count,
                'Expected {0} ValidationErrors, found {1}'.
                 format(
                    expected_validation_error_count, error_validation_count
                )
            )
            self.assertEqual(
                error_request_count, expected_request_error_count,
                'Expected {0} InvalidRequestErrors, found {1}'.
                 format(
                    expected_request_error_count, error_request_count
                )
            )

            # 5a. Verify unwanted error type is not present
            self.assertFalse(self.is_text_in_list('InvalidXMLError', stderr),
                                'Unwanted InvalidXMLError found')

        finally:
            self.log('info', '*** 4. Restoring initial litp model ***')
            self.execute_cli_load_cmd(self.ms_node, '/', initial_root_xml,
                                      '--replace')
