"""
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     October 2013 , Refactored on May 2019
@author:    gabor , Yashi Sahu
@summary:   Integration test for model validation framework
            Agile: EPIC-667, STORY-236, Sub-Task: STORY-727
"""

from litp_generic_test import GenericTest, attr


class Story236(GenericTest):

    """
    As a Product Designer I want to provide a validation framework for full
    model validation (called by create plan command) so that my model is
    validated before deployment
    """

    def setUp(self):
        """ "Runs before every test"""
        super(Story236, self).setUp()
        self.ms_node = self.get_management_node_filename()

    def tearDown(self):
        """"Runs after every test"""
        super(Story236, self).tearDown()

    @attr('all', 'revert', 'story236', 'story236_tc08')
    def test_08_p_validate_collection(self):
        """
        @tms_id: litpcds_story236_tc08
        @tms_requirements_id: LITPCDS-236
        @tms_title: Validate a create plan reports no errors when
            a node item is created with children.
        @tms_description: Create a plan to test a positive case when
            the collection size is in the allowed range.
        @tms_test_steps:
            @step: Query the system to create a list of
                commands for deploying a new peer node
            @result: List of commands obtained successfully.
            @step: Run create commands and check no errors reported.
            @result: Create commands executed successfully
                and no errors obtained.
            @step: Create a plan.
            @result: Plan created successfully.
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        self.log('info', '1. Query the system to create a list of '
                         'commands for deploying a new peer node')
        setup_cmds = self.get_create_node_deploy_cmds(self.ms_node)

        self.log('info', '2. Run all commands and check no errors reported')
        results = self.run_commands(self.ms_node, setup_cmds)
        self.assertNotEqual([], results, "No results obtained")
        errors = self.get_errors(results)
        self.assertEqual([], errors, "Create commands returned "
                                     "errors on node: '{0}'".format(errors))

        self.log('info', '3. Create a plan')
        self.execute_cli_createplan_cmd(self.ms_node)
