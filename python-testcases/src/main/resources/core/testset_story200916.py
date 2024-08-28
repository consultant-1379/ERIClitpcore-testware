"""
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     November 2017
@author:    John Dolan
@summary:   TORF-200916
            As a LITP User I want the ability to update non-configuration
            properties and have the associated item transitioned to Applied
            state without the need to create and run a plan
"""
from litp_generic_test import GenericTest, attr
import os
import test_constants as const


class Story200916(GenericTest):
    """
        As a LITP User I want the ability to update non-configuration
        properties and have the associated item transitioned to Applied
        state without the need to create and run a plan
    """

    def setUp(self):
        """ Runs before every single test """
        super(Story200916, self).setUp()
        self.ms_node = self.get_management_node_filename()
        self.plugin_id = 'story200916'
        self.software_path = "/software/items/"
        self._install_rpms()

    def tearDown(self):
        """ Runs after every single test """
        super(Story200916, self).tearDown()

    @staticmethod
    def get_local_rpm_paths(path, rpm_id):
        """
        Description:
            Method that returns a list of absolute paths to the
            RPMs required to be installed for testing.
        Args:
            path (str): Path dir to check for RPMs.
            rpm_id (str): RPM name to check for in path.
        """
        # Get all RPMs in 'path' that contain 'rpm_id' in their name
        rpm_names = [rpm for rpm in os.listdir(path) if rpm_id in rpm]

        if not rpm_names:
            return None

        # Return a list of absolute paths to the RPMs found in 'rpm_names'
        return [
            os.path.join(rpath, rpm)
            for rpath, rpm in
            zip([os.path.abspath(path)] * len(rpm_names), rpm_names)
            ]

    def _install_rpms(self):
        """
        Description:
            Method that installs plugin and extension on
            the MS if they are not already installed.
        """
        # Check if the plugin is already installed
        _, _, rcode = self.run_command(
            self.ms_node, self.rhc.check_pkg_installed([self.plugin_id]),
            su_root=True)

        # If not, copy plugin and extension onto MS
        if rcode == 1:
            local_rpm_paths = self.get_local_rpm_paths(
                os.path.abspath(
                    os.path.join(os.path.dirname(__file__), 'plugins')
                ),
                self.plugin_id
            )
            self.assertTrue(
                self.copy_and_install_rpms(self.ms_node,
                                           local_rpm_paths),
                "There was an error installing the test plugin on the MS.")

    def _update_test_item(self, url, configuration_property=None,
                         non_configuration_property=None):
        """
        Description:
            Update the test item at url
        Args:
            url (str): The url of the test item
            configuration_property (str): The new value for the configuration
                property on the test item
            non_configuration_property (str): The new value for the non
                configuration property on the test item
        """
        props = self.make_props(configuration_property,
                                non_configuration_property)
        self.execute_cli_update_cmd(self.ms_node,
                                    url,
                                    props)

    def _create_test_item(self, url, configuration_property,
                         non_configuration_property):
        """
        Description:
            Create the test item at url
        Args:
            url (str): The url of the test item
            configuration_property (str): The value for the configuration
                property on the test item
            non_configuration_property (str): The value for the non
                configuration property on the test item
        """
        test_type = "torf-200916-item-type"

        props = self.make_props(configuration_property,
                                non_configuration_property)
        self.execute_cli_create_cmd(self.ms_node,
                                    url,
                                    test_type,
                                    props)

    @staticmethod
    def make_props(configuration_property, non_configuration_property):
        """
        Description:
            Make a props string from the two provided arguments
        Args:
            configuration_property (String): The configuration value
            non_configuration_property (String): The non configuration value
        Return:
            A string containing the two properties
        """
        if configuration_property:
            conf = 'configuration_property="{0}"'.format(
                configuration_property)
        else:
            conf = ""
        if non_configuration_property:
            non_conf = 'non_configuration_property="{0}"'.format(
                non_configuration_property)
        else:
            non_conf = ""
        props = '{0} {1}'.format(conf, non_conf).strip()
        return props

    @attr('all', 'revert', 'story200916', 'story200916_tc01')
    def test_01_p_non_con_state_init(self):
        """
        @tms_id:
            torf_200916_tc_01
        @tms_requirements_id:
            TORF-200916
        @tms_title:
            State transition on non-configuration properties
        @tms_description:
            Given an item in the initial state, verify that it remains in the
            initial state following an update to a non-configuration property
        @tms_test_steps:
        @step: Create an item with a non configuration property
        @result: Item is in model in state initial
        @step: Update the non configuration property
        @result: The item state is initial

        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        self.log("info", "1. Create an item with a non configuration property")
        new_url = "{0}torf200916".format(self.software_path)
        self._create_test_item(
            url=new_url,
            configuration_property="10G",
            non_configuration_property="10G")

        self.log("info", "1. Result - item is in initial state")
        new_item_state = self.get_item_state(self.ms_node, new_url)
        self.assertEqual("Initial", new_item_state)

        self.log("info", "2. Update the non configuration property on the "
                         "new item")
        self._update_test_item(new_url, non_configuration_property="11G")

        self.log("info", "2. Result - item is in initial state")
        item_state = self.get_item_state(self.ms_node, new_url)
        self.assertEqual("Initial", item_state,
                         "Item not in initial state following update "
                         "to a single non-configuration property")

    @attr('all', 'revert', 'story200916', 'story200916_tc02')
    def test_02_p_non_con_state_updtd(self):
        """
        @tms_id:
            torf_200916_tc_02
        @tms_requirements_id:
            TORF-200916
        @tms_title:
            State transition on non-configuration properties
        @tms_description:
            Verify that objects in the Updated state remain Updated following
            a non-configuration property change.
        @tms_test_steps:
        @step: Create an item with a non configuration property
            and a configuration property and create and run a plan
        @result: Item is applied
        @step: Update the configuration property on the item
        @result: The item is in state updated
        @step: Update the non configuration property on the item
        @result: The item is still in state updated

        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        self.log("info", "1. Create an item with a non configuration property"
                         " and create/run a plan")
        new_url = "{0}torf200916perm".format(self.software_path)
        self._create_test_item(
            url=new_url,
            configuration_property="10G",
            non_configuration_property="10G")
        self.run_and_check_plan(self.ms_node,
                                const.PLAN_COMPLETE,
                                10)
        self.log("info", "1. Result - item is in applied state")
        new_item_state = self.get_item_state(self.ms_node, new_url)
        self.assertEqual("Applied", new_item_state,
                         "New item with non configuration property "
                         "not in applied state after plan")

        self.log("info", "2. Update the configuration property on the item")
        self._update_test_item(new_url, configuration_property="11G")
        item_state = self.get_item_state(self.ms_node, new_url)

        self.log("info", "2. Result - item is in updated state")
        self.assertEqual("Updated", item_state,
                         "Item is not in updated state following an "
                         "update to one of its configuration properties")

        self.log("info", "3. Update the non configuration property")
        self._update_test_item(new_url, non_configuration_property="12G")
        item_state = self.get_item_state(self.ms_node, new_url)

        self.log("info", "3. Result - item is in updated state")
        self.assertEqual("Updated", item_state,
                         "Updating a non configuration property on the"
                         " item has moved it from update state")

    @attr('all', 'revert', 'story200916', 'story200916_tc04')
    def test_04_p_non_con_and_con_init(self):
        """
        @tms_id:
            torf_200916_tc_04
        @tms_requirements_id:
            TORF-200916
        @tms_title:
            State transition on non-configuration properties
        @tms_description:
             Verify that, following the update of non-configuration and
             configuration properties on an object in state Initial, the
             object is in the Initial state and that subsequent successful
             plan execution moves the object to the applied state.
        @tms_test_steps:
        @step: Create an item with configuration and non-configuration
            properties
        @result: Item is on the model in state initial
        @step: Update all of the non-configuration properties as well as
            some of the configuration properties
        @result: The properties update and the Item is in state initial
        @step: Create and run plan
        @result: Item is in applied state
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        self.log("info", "1. Create an item with a non configuration property")
        new_url = "{0}torf200916_tc04".format(self.software_path)
        self._create_test_item(
            url=new_url,
            configuration_property="10G",
            non_configuration_property="10G")

        self.log("info", "1. Result - item is in initial state")
        new_item_state = self.get_item_state(self.ms_node, new_url)
        self.assertEqual("Initial", new_item_state,
                         "New item not in initial state")

        self.log("info", "2. Update the configuration property and the "
                         "non configuration property on the item")
        self._update_test_item(new_url, configuration_property="11G",
                              non_configuration_property="11G")

        self.log("info", "2. Result - item is in Initial state")
        item_state = self.get_item_state(self.ms_node, new_url)
        self.assertEqual("Initial", item_state,
                         "Item is not in Initial state.")

        self.log("info", "3. Confirm item is in Applied state after plan run")
        self.run_and_check_plan(self.ms_node,
                                const.PLAN_COMPLETE,
                                10)
        item_state = self.get_item_state(self.ms_node, new_url)
        self.assertEqual("Applied", item_state,
                         "Item is not in Applied state.")

    @attr('all', 'revert', 'story200916', 'story200916_tc05')
    def test_05_p_non_con_and_con_uptd(self):
        """
        @tms_id:
            torf_200916_tc_05
        @tms_requirements_id:
            TORF-200916
        @tms_title:
            State transition on non-configuration properties
        @tms_description:
            Given an item in the Updated state, verify that updating both
            a configuration and non-configuration property on that item do not
            result in the item leaving the updated state.
        @tms_test_steps:
        @step: Create an item with configuration and non configuration props
            and create/run plan
        @result: The new item is in the applied state
        @step: Update a configuration property on the item.
        @result: Item is in state updated
        @step: Update both a non-configuration property and a configuration
            property on the item.
        @result: Item is in state updated
        @step: Create and run plan
        @result: Item is in state applied
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        self.log("info", "1. Create an item with a non configuration property"
                         " and create/run a plan")
        new_url = "{0}torf200916perm".format(self.software_path)
        self._create_test_item(
            url=new_url,
            configuration_property="10G",
            non_configuration_property="10G")
        self.run_and_check_plan(self.ms_node,
                                const.PLAN_COMPLETE,
                                10)
        self.log("info", "2. Update a configuration property "
                         "on an existing item")
        self._update_test_item(
            url=new_url,
            configuration_property="9G")

        self.log("info", "2. Result - item is in updated state")
        new_item_state = self.get_item_state(self.ms_node, new_url)
        self.assertEqual("Updated", new_item_state,
                    "Item not in updated state following"
                    "configuration property change")

        self.log("info", "3. Update both a non configuration and a"
                         " configuration property on the item")
        self._update_test_item(new_url, configuration_property="7G",
                              non_configuration_property="7G")
        item_state = self.get_item_state(self.ms_node, new_url)

        self.log("info", "3. Result - item is in Updated state")
        self.assertEqual("Updated", item_state,
                         "Changing a combination of configuration and non"
                         " configuration properties caused the "
                         "item to move away from updated state.")

        self.log("info", "4. Confirm item is in Applied state after plan run")
        self.run_and_check_plan(self.ms_node,
                                const.PLAN_COMPLETE,
                                10)
        item_state = self.get_item_state(self.ms_node, new_url)
        self.assertEqual("Applied", item_state,
                         "Item is not in Applied state.")

    @attr('all', 'revert', 'story200916', 'story200916_tc06')
    def test_06_p_non_con_and_con_state_app(self):
        """
        @tms_id:
            torf_200916_tc_06
        @tms_requirements_id:
            TORF-200916
        @tms_title:
            State transition on non-configuration properties
        @tms_description:
             Given an item in the applied state, verify that the item moves to
             the updated state following a single update command containing
             changes to both a configuration and a non-configuration property.
        @tms_test_steps:
        @step: Create an item with configuration and non configuration props
            and create/run plan
        @result: The new item is in the applied state
        @step: Update a non-configuration property and a configuration
            property
        @result: Item is in the updated state
        @step: Create and run plan
        @result: Item is in the applied state
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        self.log("info", "1. Create an item with a non configuration property"
                         " and create/run a plan")
        new_url = "{0}torf200916perm2".format(self.software_path)
        self._create_test_item(
            url=new_url,
            configuration_property="10G",
            non_configuration_property="10G")
        self.run_and_check_plan(self.ms_node,
                                const.PLAN_COMPLETE,
                                10)

        self.log("info", "1. Result - New item is in the applied state.")
        new_item_state = self.get_item_state(self.ms_node, new_url)
        self.assertEqual("Applied", new_item_state,
                    "Item not in Applied state - not valid for this test")

        self.log("info", "2. Update a configuration property "
                         "on an existing item")
        self._update_test_item(
            url=new_url,
            configuration_property="5G",
            non_configuration_property="5G")

        self.log("info", "2. Result - item is in updated state")
        new_item_state = self.get_item_state(self.ms_node, new_url)
        self.assertEqual("Updated", new_item_state,
                    "Item not in updated state following a combination of "
                    "configuration and non configuration property changes")

        self.log("info", "3. Confirm item is in Applied state after plan run")
        self.run_and_check_plan(self.ms_node,
                                const.PLAN_COMPLETE,
                                10)
        item_state = self.get_item_state(self.ms_node, new_url)
        self.assertEqual("Applied", item_state,
                         "Item is not in Applied state.")
