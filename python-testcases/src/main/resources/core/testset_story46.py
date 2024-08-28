'''
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     March 2013
@author:    Philip Daly
@summary:   Integration test for LITP plan
            Agile: STORY-46

Obsolete:
All tests from Story46 are obsolete and are replaced by Story2240 tests as
either IT or AT tests as described below:

IT:
ERIClitpcore-testware/python-testcases/src/main/resources/core/
testset_story2240.py

AT:
ERIClitpcore/ats/testset_story2240
ERIClitpcore/ats/plan

Story46 tests are mapped to Story2240 ITs as follows:
=====================================================
test_01_p_remove_running_plan
    replaced by: test_01_n_no_remove_create_run_plan_state_running
test_02_p_remove_stopping_plan
    repalced by: test_03_n_no_remove_create_run_stop_plan_state_stopping
test_03_p_run_stopped_plan
    replaced by: test_03_n_no_remove_create_run_stop_plan_state_stopping
test_04_p_run_running_plan:
    replaced by: test_01_n_no_remove_create_run_plan_state_running

Story46 tests are mapped to ATs as follows:
===========================================
test_05_p_create_plan_again_after_model_addition
    replaced by: testset_story2240/test_18_p_create_plan_state_success.at
test_06_p_create_plan_again_after_model_delete
    replaced by: plan/plan_cleanup_tasks.at
test_07_p_create_plan_again_after_prop_update_undone
    replaced by: plan/create_plan_again_after_prop_update_undone.at
test_08_p_create_plan_after_plan_deployment
    replaced by:
    testset_story2240/test_17_n_create_plan_state_success_no_model_change.at
test_09_p_create_plan_after_plan_stop_and_updates
    replaced by: plan/plan_state_stopped.at
test_10_p_create_plan_after_plan_stop_remaining_tasks
    replaced by:
    testset_story2240/test_24_p_create_plan_after_plan_stop_remaining_tasks.at
'''

# Import Generic Test and the required area class
from litp_generic_test import GenericTest
# As tests  are obsolete and commented out, test_constants are no longer used
#from test_constants import PLAN_COMPLETE
#from test_constants import PLAN_STOPPED


# Create a story class that inherits GenericTest
class Story46(GenericTest):
    """
    As a user I want to know if my plan is out of date with my model
    so I can create a new plan.
    """

    #Create a setup method. This is run at the beginning of every test.
    def setUp(self):
        """
        Description:
            Runs before every single test
        Actions:
            1. Call the super class setup method
            2. Set up variables used in the tests
        Results:
            The super class prints out diagnostics and variables
            are defined which are required in the tests.
        """
        super(Story46, self).setUp()
        # Get the ms name without hardcoding (eg 'ms1') using the
        # helper function
        self.ms_node = self.get_management_node_filename()

    # Create a teardown method. This is run at the end of every test.
    def tearDown(self):
        """
        Description:
            Runs after every single test
        Actions:
            1. Call superclass teardown
        """
        super(Story46, self).tearDown()

    def _create_package(self, url_name, pkg_name=""):
        """
        Description:
            Create test package
        Args:
            url_name (str): package name in model
            pkg_name (str): value for name property in package
            add_to_cleanup (bool): If True add to list of
                                   commands to cleanup
                                   on teardown.
        Actions:
            1. Get softwate items collection path
            2. Create test package
        Results:
            Path in litp tree to the created test package
        """
        # GET ITEMS PATH
        items = self.find(self.ms_node, "/software", "software-item", False)
        items_path = items[0]

        # CREATE A PACKAGE WITH CLI
        package_url = items_path + "/" + url_name
        if pkg_name == "":
            props = "name='{0}'".format(url_name)
        else:
            props = pkg_name
        self.execute_cli_create_cmd(self.ms_node, \
            package_url, "package", props, expect_positive=True)
        return package_url

    def _create_package_link(self, node_url, url_name, pkg_name=""):
        """
        Obsolete:
            execute_cli_link_cmd generates pylint error:
            Instance of 'Story46' has no 'execute_cli_link_cmd'
            member (no-member)
            Can be made obsolete as all test cases are obsolete
        Description:
            Create package link to the test node245
        Args:
            node_url (str): node url
            url_name (str): package name in model
            pkg_name (str): value for name property for link.
            add_to_cleanup (bool): If True add to list of
                                   commands to cleanup
                                   on teardown.
        Actions:
            1. Create package link
        Results:
            Path in litp tree to the created package link
        """

        # Obsolete test. Return pass statement
        pass

#        # LINK PACKAGE WITH CLI
#        link_url = node_url + "/items/{0}".format(url_name)
#        if pkg_name == "":
#            props = "name='{0}'".format(url_name)
#        else:
#            props = pkg_name
#        self.execute_cli_link_cmd(self.ms_node, \
#          link_url, "package", props, expect_positive=True)
#        return link_url

    def _delete_package_link(self, node_url, url_name):
        """
        Description:
            Delete package link to the test node245
        Args:
            node_url (str): node url
            url_name (str): package name in model
            pkg_name (str): value for name property for link.
            add_to_cleanup (bool): If True add to list of
                                   commands to cleanup
                                   on teardown.
        Actions:
            1. Create package link
        Results:
            Path in litp tree to the created package link
        """

        # LINK PACKAGE WITH CLI
        package_url = node_url + "/items/{0}".format(url_name)
        self.execute_cli_remove_cmd(self.ms_node, \
          package_url, expect_positive=True)

    def _create_os_profile(self, url_name, profile_name=""):
        """
        Description:
            Create test os profile
        Args:
            url_name (str): package name in model
            pkg_name (str): value for name property in package
            add_to_cleanup (bool): If True add to list of
                                   commands to cleanup
                                   on teardown.
        Actions:
            1. Get softwate items collection path
            2. Create test package
        Results:
            Path in litp tree to the created test package
        """
        # GET ITEMS PATH
        profiles = self.find(self.ms_node, "/software", "profile", False)
        profiles_path = profiles[0]

        # CREATE A PACKAGE WITH CLI
        profile_url = profiles_path + "/" + url_name
        if profile_name == "":
            props = "version=rhel6 path=/profiles/node-iso/ " \
            "arch=x86_64 breed=redhat name='{0}'".format(url_name)
        else:
            props = "name='{0}' version=rhel6 path=/profiles/node-iso/ " \
            "arch=x86_64 breed=redhat".format(profile_name)
        self.execute_cli_create_cmd(self.ms_node, \
                                    profile_url, "os-profile",
                                    props, expect_positive=True)
        return profile_url

    def obsolete_01_p_remove_running_plan(self):
        """
       Obsolete:
            Replaced by Story2240 test:
            ERIClitpcore-testware/python-testcases/src/main/resources/core/
            testset_story2240.py
            test_01_n_no_remove_create_run_plan_state_running
        Description:
            This test checks that should a remove plan command be issued
            against a currently running plan, that an informative error
            message is returned to the user.
        Actions:
            1. Create test package
            2. Link package to node
            3. Create and run plan.
            4. During running of plan issue remove plan
        Results:
            Issuing of remove plan command while plan is running results
            in an informative error being returned.
        """

        # Obsolete test. Return pass statement
        pass

#        # CREATE PACKAGE ITEM
#        self._create_package("telnet")
#
#        # GET NODE1 PATH
#        nodes = self.find(self.ms_node, "/", "node")
#        node1_path = nodes[0]
#
#        # LINK PACKAGE ITEM
#        self._create_package_link(node1_path, "telnet")
#
#        # CREATE PLAN
#        self.execute_cli_createplan_cmd(self.ms_node)
#
#        # RUN PLAN
#        self.execute_cli_runplan_cmd(self.ms_node)
#
#        # REMOVE PLAN - SHOULD NOT BE ALLOWED AS PLAN IS CURRENTLY RUNNING.
#        _, stderr, _ = self.execute_cli_removeplan_cmd(self.ms_node,
#                                                       expect_positive=False)
#
#        # Wait for plan to complete with success
#        timeout_mins = 3
#        completed_successfully = \
#        self.wait_for_plan_state(self.ms_node, PLAN_COMPLETE,
#                                 timeout_mins)
#
#        self.assertTrue(completed_successfully, "Plan was not successful")
#
#        # CHECK ERROR MESSAGE - SHOULD INDICATE PLAN CANNOT BE REMOVED.
#        self.assertTrue(self.is_text_in_list("InvalidRequestError    " \
#                                             "Removing a running/stopping " \
#                                             "plan is not allowed", stderr),
#                        "'InvalidRequestError' relating to removing " \
#                        "running plan is not in errorput")

    def obsolete_02_p_remove_stopping_plan(self):
        """
       Obsolete:
            Replaced by Story2240 test:
            ERIClitpcore-testware/python-testcases/src/main/resources/core/
            testset_story2240.py
            test_03_n_no_remove_create_run_stop_plan_state_stopping
        Description:
            This test checks that should the remove plan command be issued
            against a currently stopping plan, that an informative error
            message is returned to the user.
        Actions:
            1. Create test package
            2. Link package to node
            3. Create and run plan.
            4. Issue stop plan command
            5. Issue remove plan command
        Results:
            Issuing of remove plan command while plan is stopping results
            in an informative error message being returned.
        """
        # Obsolete test. Return pass statement
        pass

#        # CREATE PACKAGE ITEM
#        self._create_package("telnet")
#
#        # GET NODE1 PATH
#        nodes = self.find(self.ms_node, "/", "node")
#        node1_path = nodes[0]
#
#        # LINK PACKAGE ITEM
#        self._create_package_link(node1_path, "telnet")
#
#        # CREATE PLAN
#        self.execute_cli_createplan_cmd(self.ms_node)
#
#        # RUN PLAN
#        self.execute_cli_runplan_cmd(self.ms_node)
#
#        # STOP PLAN
#        self.execute_cli_stopplan_cmd(self.ms_node)
#
#        # REMOVE PLAN - SHOULD NOT BE ALLOWED AS PLAN IS CURRENTLY STOPPED.
#        _, stderr, _ = self.execute_cli_removeplan_cmd(self.ms_node,
#                                                       expect_positive=False)
#
#        # CHECK ERROR MESSAGE - SHOULD INDICATE PLAN CANNOT BE REMOVED.
#        self.assertTrue(self.is_text_in_list("InvalidRequestError", stderr),
#                        "'InvalidRequestError' relating to removing " \
#                        "stopping plan is not in errorput")
#        self.assertTrue(self.is_text_in_list("Removing a running/stopping " \
#                                             "plan is not allowed", stderr),
#                        "Informative error message relating to removing " \
#                        "stopping plan is not in errorput, or has changed.")

    def obsolete_03_p_run_stopped_plan(self):
        """
       Obsolete:
            Replaced by Story2240 test:
            ERIClitpcore-testware/python-testcases/src/main/resources/core/
            testset_story2240.py
            test_03_n_no_remove_create_run_stop_plan_state_stopping
        Description:
            This test checks that when a stop plan command is issued against
            an already stopped plan, that an informative error message is
            returned to the user.
        Actions:
            1. Create test package
            2. Link package to node
            3. Create and run plan.
            4. Issue stop plan command
            5. Issue run plan command
            6. Issue the create plan command repeatedly until it stops
               reporting that a plan is currently running - This is so that
               cleanup is successful.
        Results:
            Issuing of run plan command while plan is stopped results
            in an informative error being returned.
        """

        # Obsolete test. Return pass statement
        pass

#        # CREATE PACKAGE ITEM
#        self._create_package("telnet")
#
#        # GET NODE1 PATH
#        nodes = self.find(self.ms_node, "/", "node")
#        node1_path = nodes[0]
#
#        # LINK PACKAGE ITEM
#        self._create_package_link(node1_path, "telnet")
#
#        # CREATE PLAN
#        self.execute_cli_createplan_cmd(self.ms_node)
#
#        # RUN PLAN
#        self.execute_cli_runplan_cmd(self.ms_node)
#
#        # STOP PLAN
#        self.execute_cli_stopplan_cmd(self.ms_node)
#
#        # RUN PLAN - SHOULD NOT BE ALLOWED AS PLAN IS CURRENTLY STOPPED.
#        _, stderr, _ = self.execute_cli_runplan_cmd(self.ms_node,
#                                                       expect_positive=False)
#
#        # CHECK ERROR MESSAGE - SHOULD INDICATE PLAN CANNOT BE REMOVED.
#        self.assertTrue(self.is_text_in_list("InvalidRequestError", stderr),
#                        "'InvalidRequestError' relating to running " \
#                        "stopped plan is not in errorput")

    def obsolete_04_p_run_running_plan(self):
        """
       Obsolete:
            Replaced by Story2240 test:
            ERIClitpcore-testware/python-testcases/src/main/resources/core/
            testset_story2240.py
            test_01_n_no_remove_create_run_plan_state_running
        Description:
            This test checks that when the run command is issued against
            an already running plan that an informative error message is
            returned to the user.
        Actions:
            1. Create test package
            2. Link package to node
            3. Create and run plan.
            5. Issue run plan command.
        Results:
            Issuing of run plan command while plan is running results
            in an informative error being returned.
        """

        # Obsolete test. Return pass statement
        pass

#        # CREATE PACKAGE ITEM
#        self._create_package("telnet")
#
#        # GET NODE1 PATH
#        nodes = self.find(self.ms_node, "/", "node")
#        node1_path = nodes[0]
#
#        # LINK PACKAGE ITEM
#        self._create_package_link(node1_path, "telnet")
#
#        # CREATE PLAN
#        self.execute_cli_createplan_cmd(self.ms_node)
#
#        # RUN PLAN
#        self.execute_cli_runplan_cmd(self.ms_node)
#
#        # RUN PLAN - SHOULD NOT BE ALLOWED AS PLAN IS CURRENTLY RUNNING.
#        _, stderr, _ = self.execute_cli_runplan_cmd(self.ms_node,
#                                                       expect_positive=False)
#
#        # CHECK ERROR MESSAGE - SHOULD INDICATE PLAN CANNOT BE REMOVED.
#        self.assertTrue(self.is_text_in_list("InvalidRequestError", stderr),
#                        "'InvalidRequestError' relating to running " \
#                        "running plan is not in errorput")

    def obsolete_05_p_create_plan_again_after_model_addition(self):
        """
        Obsolete:
            Replaced by AT:
            ERIClitpcore/ats/testset_story2240/
            test_18_p_create_plan_state_success.at
        Description:
            This test checks the functionality of the create plan
            command when it is issued, the model is updated, and the
            create plan command is issued again.
        Actions:
            1. Create test packages
            2. Link package to node
            3. Create plan.
            5. Link package to node.
            6. Issue the create plan command again.
        Results:
            The subsequent create plan command successfully updates the
            tasks to include the update to the model.
        """

        # Obsolete test. Return pass statement
        pass

#        # CREATE PACKAGE ITEM
#        self._create_package("telnet")
#        self._create_package("wireshark")
#
#        # GET NODE1 PATH
#        nodes = self.find(self.ms_node, "/", "node")
#        node1_path = nodes[0]
#
#        # LINK PACKAGE ITEM
#        self._create_package_link(node1_path, "telnet")
#
#        # CREATE PLAN
#        self.execute_cli_createplan_cmd(self.ms_node)
#
#        # SHOW PLAN
#        stdout, _, _ = self.execute_cli_showplan_cmd(self.ms_node)
#        self.assertTrue(self.is_text_in_list("Installing package telnet",
#                                             stdout),
#                        "Task to install telnet was not found in plan.")
#        # LINK PACKAGE ITEM
#        self._create_package_link(node1_path, "wireshark")
#
#        # CREATE PLAN
#        self.execute_cli_createplan_cmd(self.ms_node)
#
#        # SHOW PLAN
#        stdout, _, _ = self.execute_cli_showplan_cmd(self.ms_node)
#        self.assertTrue(self.is_text_in_list("Installing package telnet",
#                                             stdout),
#                        "Task to install telnet was not found in plan.")
#        self.assertTrue(self.is_text_in_list("Installing package wireshark",
#                                             stdout),
#                        "Task to install wireshark was not found in plan.")

    def obsolete_06_p_create_plan_again_after_model_delete(self):
        """
        Obsolete:
            Replaced by AT:
            ERIClitpcore/ats/plan/plan_cleanup_tasks.at
        Description:
            This test checks that should a plan be created, and some of the
            objects to be deployed be unlinked, and the plan created again,
            that the tasks to deploy the unlinked items are not present in
            the plan any longer.
        Actions:
            1. Create test packages
            2. Link packages to node
            3. Create plan.
            5. Unlink one of the packages from the node.
            6. Create plan
        Results:
            The second plan will only include a task to deploy the package
            currently linked to the node.
        """

        # Obsolete test. Return pass statement
        pass

#        # CREATE PACKAGE ITEM
#        self._create_package("telnet")
#        self._create_package("wireshark")
#
#        # GET NODE1 PATH
#        nodes = self.find(self.ms_node, "/", "node")
#        node1_path = nodes[0]
#
#        # LINK PACKAGE ITEM
#        self._create_package_link(node1_path, "telnet")
#        self._create_package_link(node1_path, "wireshark")
#
#        # CREATE PLAN
#        self.execute_cli_createplan_cmd(self.ms_node)
#
#        # SHOW PLAN
#        stdout, _, _ = self.execute_cli_showplan_cmd(self.ms_node)
#        self.assertTrue(self.is_text_in_list("Installing package telnet",
#                                             stdout),
#                        "Task to install telnet was not found in plan.")
#        self.assertTrue(self.is_text_in_list("Installing package wireshark",
#                                             stdout),
#                        "Task to install wireshark was not found in plan.")
#        # DELETE THE LINK TO THE PACKAGE ITEM
#        self._delete_package_link(node1_path, "wireshark")
#
#        # CREATE PLAN
#        self.execute_cli_createplan_cmd(self.ms_node)
#
#        # SHOW PLAN
#        stdout, _, _ = self.execute_cli_showplan_cmd(self.ms_node)
#        self.assertTrue(self.is_text_in_list("Installing package telnet",
#                                             stdout),
#                        "Task to install telnet was not found in plan.")
#        self.assertFalse(self.is_text_in_list("Installing package wireshark",
#                                             stdout),
#                        "Task to install wireshark was found in plan.")

    def obsolete_07_p_create_plan_again_after_prop_update_undone(self):
        """
        Obsolete:
            Replaced by AT:
            ERIClitpcore/ats/plan/create_plan_again_after_prop_update_undone.at
        reference-to-os-profile.
        Description:
            This test checks that when an update to an object is reverted that
            a plan shall not be generated as the deployment description
            shall once again reflect the environment.
        Actions:
            1. Create a test os profile
            2. Link a nodes os profile to the test profile
            3. Check that the os profile object is in applied state
            4. Create plan.
            5. Remove the test profile, and relink the node to the original
               os profile.
            6. Issue the create plan command.
            7. Check the state of the os profile link
        Results:
            A plan is not created as the model once again reflects the
            environment, also the os profile link does not change its state
            from applied.
        """

        # Obsolete test. Return pass statement
        pass

#        test_profile_url = \
#        self._create_os_profile("test_profile")
#
#        # GET NODE1 PATH
#        nodes = self.find(self.ms_node, "/", "node")
#        node1_path = nodes[0]
#
#        # GET OS PROFILE PATH
#        profiles = self.find(self.ms_node, node1_path, "os-profile")
#        profile_url = profiles[0]
#
#        # CHECK THE OS PROFILE LINK STATE
#        stdout, _, _ = self.execute_cli_show_cmd(self.ms_node, profile_url)
#        self.assertTrue(self.is_text_in_list("state: Applied",
#                                             stdout),
#                       "Object was not in appliled state prior to test start")
#
#        # GET THE CURRENT VALUE FOR THE PROFILE LINK NAME
#        current_name = \
#        self.get_props_from_url(self.ms_node, profile_url, "name")
#
#        # UPDATE THE PROFILE LINK NAME TO THE TEST PROFILE
#        self.execute_cli_update_cmd(self.ms_node, profile_url,
#                                    'name=test_profile')
#
#        # CREATE PLAN
#        self.execute_cli_createplan_cmd(self.ms_node)
#
#        # RETURN OS PROFILE LINK TO ORIGINAL
#        self.execute_cli_update_cmd(self.ms_node, profile_url,
#                                    props='name=%s' % current_name)
#
#        # REMOVE THE TEST PROFILE
#        self.execute_cli_remove_cmd(self.ms_node, test_profile_url)
#
#        # CREATE PLAN
#        self.execute_cli_createplan_cmd(self.ms_node, expect_positive=False)
#
#        # CHECK THE OS PROFILE LINK STATE
#        stdout, _, _ = self.execute_cli_show_cmd(self.ms_node, profile_url)
#        self.assertTrue(self.is_text_in_list("state: Applied",
#                                             stdout),
#                        "State of object has changed due to test.")

    def obsolete_08_p_create_plan_after_plan_deployment(self):
        """
        Obsolete:
            Replaced by AT:
            ERIClitpcore/ats/testset_story2240/
            test_17_n_create_plan_state_success_no_model_change.at
        Description:
            This test checks that following a successful plan deployment
            that the issuing of the create plan command fails and returns an
            informative error message to the user as no changes to the
            deployment description have occurred.
        Actions:
            1. Create test package
            2. Link package to node
            3. Create and run plan.
            4. Wait for the plan to complete
            5. Issue the create plan command again
        Results:
            The create plan command fails and returns an informative
            error message.
        """

        # Obsolete test. Return pass statement
        pass

#        # CREATE PACKAGE ITEM
#        self._create_package("telnet")
#
#        # GET NODE1 PATH
#        nodes = self.find(self.ms_node, "/", "node")
#        node1_path = nodes[0]
#
#        # LINK PACKAGE ITEM
#        self._create_package_link(node1_path, "telnet")
#
#        # CREATE PLAN
#        self.execute_cli_createplan_cmd(self.ms_node)
#
#        # RUN PLAN
#        self.execute_cli_runplan_cmd(self.ms_node)
#
#        # Wait for plan to complete with success
#        timeout_mins = 3
#        completed_successfully = \
#        self.wait_for_plan_state(self.ms_node, PLAN_COMPLETE,
#                                 timeout_mins)
#
#        self.assertTrue(completed_successfully, "Plan was not successful")
#
#        # CREATE PLAN
#        _, stderr, _ = \
#        self.execute_cli_createplan_cmd(self.ms_node, expect_positive=False)
#
#        # CHECK ERROR MESSAGE - SHOULD INDICATE PLAN CANNOT BE CREATED.
#        self.assertTrue(self.is_text_in_list("Plan cannot be created: " \
#                                             "no tasks were generated",
#                                             stderr),
#                        "Informative error message relating to create plan" \
#                        " is not present, or has been altered.")
#
#        self.assertTrue(self.is_text_in_list("DoNothingPlanError", stderr),
#                        "'DoNothingPlanError' was not returned in error msg.")

    def obsolete_09_p_create_plan_after_plan_stop_and_updates(self):
        """
        Obsolete:
            Replaced by AT:
            ERIClitpcore/ats/plan/plan_state_stopped.at
        Description:
            This test checks that when a plan is created, run, and stopped
            before all of its tasks are complete, that a subsequently
            created plan, following additions to the deployment description
            will include the remaining tasks from the previous plan along
            with the tasks relating to the objects newly added to the
            deployment description.
        Actions:
            1. Create test package
            2. Link package to node
            3. Link package to the management server
            4. Create and run plan.
            5. During running of plan issue stop plan command.
            6. Wait for the plan to stop.
            7. Create another package.
            8. Link the package to node
            9. Create a plan
        Results:
            The created plan includes the tasks that were not completed in the
            previous plan, as well as the tasks related to the objects newly
            added to the deployment description.
        """

        # Obsolete test. Return pass statement
        pass

#        # CREATE PACKAGE ITEM
#        self._create_package("telnet")
#        self._create_package("trousers")
#
#        # GET NODE1 PATH
#        nodes = self.find(self.ms_node, "/", "node")
#        node1_path = nodes[0]
#
#        # GET MS PATH
#        nodes = self.find(self.ms_node, "/", "ms")
#        ms_path = nodes[0]
#
#        # LINK PACKAGE ITEM
#        self._create_package_link(node1_path, "telnet")
#        self._create_package_link(ms_path, "trousers")
#
#        # CREATE PLAN
#        self.execute_cli_createplan_cmd(self.ms_node)
#
#        # RUN PLAN
#        self.execute_cli_runplan_cmd(self.ms_node)
#
#        # STOP PLAN
#        self.execute_cli_stopplan_cmd(self.ms_node)
#        self.execute_cli_showplan_cmd(self.ms_node)
#
#        # Wait for plan to complete with success
#        timeout_mins = 3
#        completed_successfully = \
#        self.wait_for_plan_state(self.ms_node, PLAN_STOPPED,
#                                 timeout_mins)
#
#        self.assertTrue(completed_successfully,
#                        "Stopping of plan was not successful")
#
#        # CREATE PACKAGE ITEM
#        self._create_package("wireshark")
#
#        # LINK PACKAGE ITEM
#        self._create_package_link(node1_path, "wireshark")
#
#        # CREATE PLAN
#        self.execute_cli_createplan_cmd(self.ms_node)
#
#        # SHOW PLAN
#        stdout, _, _ = self.execute_cli_showplan_cmd(self.ms_node)
#        self.assertTrue(self.is_text_in_list("Installing package telnet",
#                                             stdout),
#                        "Task to install telnet was not found in plan.")
#        self.assertTrue(self.is_text_in_list("Installing package wireshark",
#                                             stdout),
#                        "Task to install wireshark was not found in plan.")

    def obsolete_10_p_create_plan_after_plan_stop_remaining_tasks(self):
        """
        Obsolete:
            Replaced by AT:
            ERIClitpcore/ats/testset_story2240/
            test_24_p_create_plan_after_plan_stop_remaining_tasks.at
        Description:
            This checks that when a plan is run and stopped before
            all of its tasks are completed, that a subsequently
            created plan included the remaining tasks from the
            previous plan.
        Actions:
            1. Create test packages
            2. Link package to node
            3. Link package to management server
            4. Create and run plan.
            5. During running of plan issue stop plan command.
            6. Wait for the plan to stop.
            7. Issue the create plan command.
        Results:
            A plan is created containing the tasks remaining to be executed
            from the previous plan.
        """

        # Obsolete test. Return pass statement
        pass

#        # CREATE PACKAGE ITEM
#        self._create_package("telnet")
#        self._create_package("trousers")
#
#        # GET NODE1 PATH
#        nodes = self.find(self.ms_node, "/", "node")
#        node1_path = nodes[0]
#
#        # GET MS PATH
#        nodes = self.find(self.ms_node, "/", "ms")
#        ms_path = nodes[0]
#
#        # LINK PACKAGE ITEM
#        self._create_package_link(node1_path, "telnet")
#        self._create_package_link(ms_path, "trousers")
#
#        # CREATE PLAN
#        self.execute_cli_createplan_cmd(self.ms_node)
#
#        # RUN PLAN
#        self.execute_cli_runplan_cmd(self.ms_node)
#
#        # STOP PLAN
#        self.execute_cli_stopplan_cmd(self.ms_node)
#        self.execute_cli_showplan_cmd(self.ms_node)
#
#        # WAIT FOR PLAN TO STOP
#        timeout_mins = 3
#        completed_successfully = \
#        self.wait_for_plan_state(self.ms_node, PLAN_STOPPED,
#                                 timeout_mins)
#
#        self.assertTrue(completed_successfully,
#                        "Stopping of plan was not successful")
#
#        # CREATE PLAN
#        self.execute_cli_createplan_cmd(self.ms_node)
#
#        # SHOW PLAN
#        stdout, _, _ = self.execute_cli_showplan_cmd(self.ms_node)
#        self.assertTrue(self.is_text_in_list("Installing package telnet",
#                                             stdout),
#                        "Task to install telnet was not found in plan.")
#        self.assertFalse(self.is_text_in_list("Installing package trousers",
#                                             stdout),
#                        "Task to install trousers was found in plan.")
#
#        # REMOVE PLAN
#        self.execute_cli_removeplan_cmd(self.ms_node)
