'''
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     September 2013
@author:    Luke Murphy
@summary:   Integration test for item discovery from the REST interface
            Agile: EPIC-183, STORY-262, Sub-Task: STORY-333
'''
from litp_generic_test import GenericTest, attr
from rest_utils import RestUtils
import test_constants
import os


class Story262(GenericTest):
    """As a REST Client developer I want to get an item type specified by URL
       so that the server can tell me what the format
       of items for the type is"""

    # Allowing nose to output longer assertion error messages
    # http://goo.gl/wV2wg6
    maxDiff = None

    def setUp(self):
        """run before every test"""
        super(Story262, self).setUp()
        self.test_ms = self.get_management_node_filename()

        # init RestUtils
        self.ms_ip = self.get_node_att(self.test_ms, 'ipv4')
        self.rest = RestUtils(self.ms_ip)

    def tearDown(self):
        """run after every test"""
        super(Story262, self).tearDown()

    @staticmethod
    def get_litp_docs_resource_path(resource, item='index'):
        """
        Description:
        Validate correct LITP docs resource is used.
        Return Nexus URL to LITP docs specified.

        Args:
        resource (str):  Type of documentation resource e.g. item types
        item (str): Documentation on a specific item under a resource
                    Default 'index' (all types) for the specified resource
        """
        resource = resource.lower()

        if resource not in ['item_types', 'property_types', 'extensions',
                            'plugins']:
            raise ValueError('resource must be "item_types", '
                             '"property_types", "extensions" or "plugins"')

        return '{0}/content/sites/litp2/ERIClitpdocs/latest/{1}/{2}.html'\
               .format(test_constants.NEXUS_LINK, resource,
                       item.replace('-', '_'))

    def get_litp_docs_data(self, resource, item='index'):
        """
        Description:
        Retrieve Sphinx documentation for which item/property types
        docs are available. If index specified we parse the index file
        and retrieve all specified types. If an item is specified other
        than index we return all document data for that item. LITP
        documentation data is retrieved from Nexus.

        Args:
        resource (str): Type of documentation resource e.g. item types
        item (str): Documentation on a specific item under a resource
                    Default 'index' (all types) for the specified resource
        """

        resource_path = self.get_litp_docs_resource_path(resource, item)

        if item == 'index':
            grep_cmd = '{0} -s {1} | {2} "reference internal" | ' \
                           '{2} "&#8217;"' \
                           .format(test_constants.CURL_PATH, resource_path,
                                   test_constants.GREP_PATH)
        else:
            grep_cmd = '{0} -s {1}'.format(test_constants.CURL_PATH,
                                           resource_path)

        std_out, std_err, rcode = self.run_command_local(grep_cmd)

        self.assertNotEqual([], std_out, 'There was no output from '
                                         'the command')
        self.assertEqual([], std_err, 'The following error was encountered: '
                                      '{0}'.format(std_err))
        self.assertEqual(0, rcode,
                         'Non-zero status code returned: {0}'.format(rcode))

        if item == 'index':
            litp_type_list = []
            for line in std_out:
                litp_type_list.append(line.split("&#8216;")[1]
                                      .split("&#8217;")[0])
            return litp_type_list

        return std_out

    def get_item_type_dicts(self):
        """Get list of item types from HAL compliant JSON
           Returns: list of item type dictionaries"""
        # list of item types dicts from HAL compliant JSON
        item_type_dicts = []

        # run GET request
        std_out, std_err, rcode = self.rest.get(self.rest.item_type_path)

        # error checking
        self.assertNotEqual('', std_out, 'There was no output from '
                                         'the command')
        self.assertEqual('', std_err, 'The following error was encountered: '
                                      '{0}'.format(std_err))
        self.assertTrue(self.rest.is_status_success(rcode),
                        'Returned status code was {0}'.format(rcode))

        hal_json, errors = self.rest.get_json_response(std_out)
        self.assertTrue(hal_json, 'No JSON output returned')
        self.assertEqual([], errors, 'Errors returned in JSON response: {0}'
                         .format(errors))
        try:
            # grab list of dictionaries which contain information about
            # each item type
            item_type_dicts = hal_json['_embedded']['item-type']
        except KeyError as key_err:
            self.log(
                "error", "Failed to retrieve {0} from {1}".format(
                    key_err, hal_json))

        self.assertNotEqual([], item_type_dicts)
        return item_type_dicts

    def rest_request_by_type(self, item_type):
        """REST payload for item type 'item_type'"""
        # when getting an item type from the documentation
        # underscores are used - hyphons are used in the REST interface
        rest_path_id = item_type.replace("_", "-")
        rest_path = os.path.join(self.rest.item_type_path, rest_path_id)

        std_out, std_err, rcode = self.rest.get(rest_path)

        self.assertNotEqual('', std_out, 'There was no output from '
                                         'the command')
        self.assertEqual('', std_err, 'The following error was encountered: '
                                      '{0}'.format(std_err))
        self.assertTrue(self.rest.is_status_success(rcode),
                        'Returned status code was {0}'.format(rcode))

        hal_json, errors = self.rest.get_json_response(std_out)
        self.assertTrue(hal_json, 'No JSON output returned')
        self.assertEqual([], errors, 'Errors returned in JSON response: {0}'
                         .format(errors))

        return hal_json

    def item_types_from_rest(self):
        """List of item types returned from the REST interface payload"""
        all_item_types = []
        try:
            all_item_types_from_rest = self.get_item_type_dicts()
            for item_type_dict in self.get_item_type_dicts():
                all_item_types.append(item_type_dict['id'])
        except KeyError as key_err:
            self.log(
                "error", "Failed to retrieve {0} from {1}".format(
                    key_err, all_item_types_from_rest))
            self.assertNotEqual([], all_item_types, 'No item types returned')

        return all_item_types

    @attr('pre-reg', 'revert', 'cdb_priority1', 'cdb-only', 'story262',
          'story262_tc01')
    def test_01_p_all_item_types_present(self):
        """
        @tms_id: litpcds-262_tc01
        @tms_requirements_id: LITPCDS-262
        @tms_title: Test all item types are present between REST API and Docs
        @tms_description:  Verify that the fixed REST url is returning all
                registered item types There is a fixed REST url that a user
                can perform a GET request on and retrieve a list of all item
                types. We are checking that the REST interface serves ALL item
                types by comparing the list returned to the list of types
                in standard documentation on every MS.
        @tms_test_steps:
         @step: Get list of item types from REST + docs
         @result: Two lists are returned containing REST and Docs item types
         @step: Check if there is a different
         @result: No diff between REST item types and Docs item types
         @step: Log mismatch + location if there is a diff
         @result: Log of mismatch returned
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        errors = []

        # 1. get lists of item types
        self.log('info', 'Getting list of item types')
        types_from_docs = self.get_litp_docs_data(resource='item_types')
        types_from_rest = self.item_types_from_rest()

        # 2. get difference between docs + rest interface
        self.log('info', 'Get difference between docs and rest interface')
        rest_missing = set(types_from_docs).difference(set(types_from_rest))
        docs_missing = set(types_from_rest).difference(set(types_from_docs))

        # 3. log where item type is missing if there is a mismatch
        self.log('info', 'Checking for item type mismatch')
        if rest_missing:
            self.log('error', 'Item type(s) {0} in REST payload missing'
                     .format(rest_missing))
            errors.append(
                "Item type(s) {0} in documentation not found in REST payload"
                .format(list(rest_missing))
            )
        elif docs_missing:
            self.log('error', 'Item type(s) {0} in Docs missing'
                     .format(docs_missing))
            errors.append(
                "Item type(s) {0} in REST payload not found in documentation"
                .format(list(docs_missing))
            )
        self.assertEqual([], errors, 'The following error was encountered: {0}'
                         .format(errors))

    @attr('all', 'revert', 'story262', 'story262_tc02')
    def test_02_n_read_only_url(self):
        """
        @tms_id: litpcds-262_tc02
        @tms_requirements_id: LITPCDS-262
        @tms_title: Verify that the fixed REST url is returning all
                    registered item types
        @tms_description: Verify that the fixed REST url for item
                discovery is 'read-only'. Attempt to perform
                an update (PUT) and assert failure
        @tms_test_steps:
         @step:  run POST (update) on item-type url and assert failures
         @result: Failure returned from POST on item-type
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        # 1. perform post
        std_out, std_err, rcode = self.rest.put(
            os.path.join(self.rest.item_type_path, "software-item"),
            self.rest.HEADER_JSON, """{"id":"test_update"}""")
        # assert failures
        self.assertNotEqual('', std_out, 'There was no output from '
                                         'the command')
        self.assertEqual('', std_err, 'The following error '
                                      'was encountered:'
                                      '{0}'.format(std_err))
        self.assertNotEqual(0, rcode,
                            'Zero status code returned: {0}'.format(rcode))
        self.assertTrue("MethodNotAllowedError" in std_out,
                        'No MethodNotAllowError returned')

    @attr('pre-reg', 'revert', 'cdb_priority1', 'cdb-only', 'story262',
          'story262_tc03')
    def test_03_p_item_types_by_id(self):
        """
        @tms_id: litpcds-262_tc03
        @tms_requirements_id: LITPCDS-262
        @tms_title: Verify that the fixed REST url is returning all
                    registered item types
        @tms_description: Check that all item types can be retrieved by ID.
        @tms_test_steps:
         @step:  attempt to retrieve all item types by ID.
         @result: all item types retrieved by ID
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        # 1. Attempt to retrieve all item
        #    types by ID and assert success
        self.log('info', 'Retrieving Item types by Id')
        for item_type in self.get_litp_docs_data(resource='item_types'):
            std_out, std_err, rcode = self.rest.get(
                os.path.join(self.rest.item_type_path, item_type)
            )
            self.assertNotEqual('', std_out, 'There was no output from '
                                             'the command')
            self.assertEqual('', std_err, 'The following error '
                                          'was encountered:'
                                          '{0}'.format(std_err))
            self.assertTrue(self.rest.is_status_success(rcode),
                            'Returned status code was {0}'.format(rcode))

            hal_json, errors = self.rest.get_json_response(std_out)
            self.assertTrue(hal_json, 'No JSON output returned')
            self.assertEqual([], errors, 'Errors returned in JSON response: '
                                         '{0}'.format(errors))

    # attr('pre-reg', 'revert', 'cdb_priority1', 'cdb-only', 'story262',
    #       'story262_tc04')
    def obsolete_04_p_validate_payload_info(self):
        """
            Description:
                For each item check that whether it is a supertype,
                whether it has children and whether it has properties
                is reported consistently between log files and rest item_types
                call.

                NB. Originally this test was testing exact match between docs
                and what was returned from rest but this was deemed
                unmaintainable due to regularly changes to docs structure.

            Actions:
                1. Get list of item types.
                2. Get data on each item type.
                3. Get data from rest item type's path
                4. Ensure that if the file indicates item has a supertype
                   the rest.
                5. Ensure that if the file indicates item has children the rest
                   call indicates the same.
                6. Check if file indicates properties rest also indicates
                   properties.
            Result:
                That attributes on each item types are correct.
        """
        # Obsolete test. Return pass statement
        pass

    @attr('pre-reg', 'revert', 'cdb_priority1', 'cdb-only', 'story262',
          'story262_tc05')
    def test_05_p_prop_types_by_id(self):
        """
        @tms_id: litpcds-262_tc05
        @tms_requirements_id: LITPCDS-262
        @tms_title: Verify that the fixed REST url is returning all
                    registered property types
        @tms_description: Check that all property types can be retrieved by ID.
        @tms_test_steps:
         @step:  attempt to retrieve all property types by ID.
         @result: all property types retrieved by ID
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        # 1. Attempt to retrieve all property
        #    types by ID and assert success
        self.log('info', 'Retrieving all Property types by Id')
        for prop_type in self.get_litp_docs_data(resource='property_types'):
            std_out, std_err, rcode = self.rest.get(
                os.path.join(self.rest.property_type_path, prop_type)
            )
            self.assertNotEqual('', std_out, 'There was no output from '
                                             'the command')
            self.assertEqual('', std_err, 'The following error '
                                          'was encountered:'
                                          '{0}'.format(std_err))
            self.assertTrue(self.rest.is_status_success(rcode),
                            'Returned status code was {0}'.format(rcode))

            hal_json, errors = self.rest.get_json_response(std_out)
            self.assertTrue(hal_json, 'No JSON output returned')
            self.assertEqual([], errors, 'Errors returned in JSON response: '
                                         '{0}'.format(errors))

    @attr('pre-reg', 'revert', 'cdb_priority1', 'cdb-only', 'story262',
          'story262_tc06')
    def test_06_p_extensions_by_id(self):
        """
        @tms_id: litpcds-262_tc06
        @tms_requirements_id: LITPCDS-262
        @tms_title:  Verify configuration file (.conf) for each extension is
                     exists.
        @tms_description: Check that all extension types can be retrieved
                          by ID and verify that they have configuration files.
        @tms_test_steps:
         @step:  Retrieve all extension names from
                 the extensions index.html file.
         @result: All extension names returned
         @step: Ensure each extension has a .conf
                file under the extensions directory.
         @result: Extension has a .conf file in extensions directory
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        # 1. For each extension name returned
        self.log('info', 'Retrieving all Extensions by Id')
        for ext in self.get_litp_docs_data(resource='extensions'):
            # Ensure '_extension' is appended to name
            if '_extension' not in ext:
                ext = '{0}_extension'.format(ext)

            # Path to check
            check_conf_file = os.path.join(
                test_constants.LITP_EXT_PATH, '{0}.conf'.format(ext))

            # 2. Check that path to config file exists
            self.log('info', 'Checking if path to config file exists {0}'
                     .format(check_conf_file))
            path_exists = self.remote_path_exists(
                self.test_ms, check_conf_file)
            self.assertTrue(path_exists,
                            '{0} does not exist.'.format(check_conf_file))

    @attr('pre-reg', 'revert', 'cdb_priority1', 'cdb-only', 'story262',
          'story262_tc07')
    def test_07_p_plugin_by_id(self):
        """
        @tms_id: litpcds-262_tc07
        @tms_requirements_id: LITPCDS-262
        @tms_title: Verify that the fixed REST url is returning all
                    registered plugins
        @tms_description: Check that all plugins can be retrieved by ID
                          and verify that they have configuration files.
        @tms_test_steps:
         @step:  attempt to retrieve all plugins by ID.
         @result: all plugins retrieved by ID
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        # 1. For each plugin name returned
        self.log('info', 'Retrieving all Plugins by Id')
        for plugin in self.get_litp_docs_data(resource='plugins'):
            # Ensure '_plugin' is appended to name
            if '_plugin' not in plugin:
                plugin = '{0}_plugin'.format(plugin)

            # Path to check
            check_conf_file = os.path.join(
                test_constants.LITP_PLUGIN_PATH, '{0}.conf'.format(plugin))

            # 2. Check that path to config file exists
            self.log('info', 'Checking if path to config file exists {0}'
                     .format(check_conf_file))
            path_exists = self.remote_path_exists(
                self.test_ms, check_conf_file)
            self.assertTrue(path_exists,
                            '{0} does not exist.'.format(check_conf_file))
