"""
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     Febuary 2014
@author:    Maria Varley
@summary:   LITPCDS-671
            As a REST Client developer I want to CRUD on execution manager so
            I can create, review and execute a plan through the REST API
"""


from litp_generic_test import GenericTest, attr
from rest_utils import RestUtils
import test_constants as const
from json_utils import JSONUtils
import re


class Story671(GenericTest):
    """
    As a REST Client developer I want to CRUD on execution manager so I can
    create, review and execute a plan through the REST API
    """

    def setUp(self):
        """ Runs before every single test """
        super(Story671, self).setUp()
        self.ms1 = self.get_management_node_filename()
        self.rest = RestUtils(self.get_node_att(self.ms1, 'ipv4'))
        self.json = JSONUtils()

    def tearDown(self):
        """ Runs after every single test """
        self.rest.clean_paths()
        super(Story671, self).tearDown()

    def _create_packages(self):
        """
            Creates a telnet package and inherit to the MS and peer nodes
        """
        nodes_uri = self.find(self.ms1, path='/deployments', resource='node')
        n1_coll_software_uri = nodes_uri[0] + "/items/"

        message_data = \
        '{"id": "test671","type": "package","properties": {"name": "telnet"}}'
        stdout, stderr, rc = self.rest.post("/software/items",
                                            self.rest.HEADER_JSON,
                                            message_data)
        self.assertEqual(201, rc)
        self.assertEqual("", stderr)
        self.assertNotEqual("", stdout)

        self.rest.inherit_cmd_rest("/ms/items/test671",
                                   "/software/items/test671")
        self.rest.inherit_cmd_rest(n1_coll_software_uri + "/test671",
                                   "/software/items/test671")

    @attr('all', 'revert')
    def test_01_pn_create_plan_positive(self):
        """
        @tms_id: litpcds_671_tc01
        @tms_requirements_id: LITPCDS-671
        @tms_title: Verify plan management via REST interface
        @tms_description:
            Verify that it is possible to create, run and stop a plan via REST
            interface.
            NOTE: also verify story bug TORF-151452
        @tms_test_steps:
        @step: Create an item of package type, inherit it to MS and peer nodes
        @result: Item created and inherited successfully
        @step: Create plan via REST
        @result: Plan created successfully
        @result: The command output is JSON HAL compliant
        @step: Run plan via REST
        @result: Command completed successfully
        @result: Plan state is "running"
        @result: The command output is JSON HAL compliant
        @step: Attempt to delete plan via REST while plan is running
        @result: Not allowed - InvalidRequestError
        @step: Attempt to update plan state via REST without passing the
               'state' value while plan is running
        @result: Not allowed - InvalidRequestError
        @step: Attempt to update a running plan state via REST to "running"
        @result: Not allowed - InvalidRequestError
        @step: Attempt to update a phase via REST with an invalid state
        @result: Not allowed - MethodNotAllowedError
        @step: Attempt to delete a phase via REST while plan is running
        @result: Not allowed - MethodNotAllowedError
        @step: GET list of phases in the running plan
        @result: List of phases returned
        @step: GET a particular phase of the running plan
        @result: Phase returned
        @step: GET list of tasks in particular phase of the running plan
        @result: List of tasks returned
        @step: Attempt to GET a list of tasks from a non existing phase
        @result: InvalidLocationError posted
        @step: Stop a running plan via REST
        @result: Plan stopped successfully
        @step: Create plan via REST
        @result: Plan created successfully
        @step: Run plan via REST and wait for completion
        @result: Plan runs and completes successfully
        @tms_test_precondition: N/A
        @tms_execution_type: Automated
        """
        self.log('info',
        '1. Create package items on MS, MN1 and MN2')
        self._create_packages()

        self.log('info',
        '2. Create plan via REST')
        stdout, stderr, rc = self.rest.create_plan_rest()
        self.assertEqual("", stderr)
        self.assertEqual(201, rc)
        self.assertNotEqual("", stdout)
        self.assertTrue(self.json.is_json_hal_complient(json_output=stdout,
                                                        has_children=True,
                                                        has_props=True))

        self.log('info',
        '3. Get the plan via REST')
        stdout, stderr, rc = self.rest.show_plan_rest()
        self.assertEqual("", stderr)
        self.assertEqual(200, rc)
        self.assertNotEqual("", stdout)
        self.assertTrue(self.json.is_json_hal_complient(json_output=stdout,
                                                        has_children=True,
                                                        has_props=True))

        self.log('info',
        '4. Run plan via REST and '
           'verify that plan state is "running" immediately after '
           '"litp run_plan" command returns (story-bug TORF-151452)')
        stdout, stderr, rc = self.rest.run_plan_rest()
        plan_state = self.get_current_plan_state(self.ms1)
        self.assertEqual(const.PLAN_IN_PROGRESS, plan_state)
        self.assertEqual("", stderr)
        self.assertEqual(200, rc)
        self.assertNotEqual("", stdout)
        self.assertTrue(self.json.is_json_hal_complient(json_output=stdout,
                                                        has_children=True,
                                                        has_props=True))

        self.log('info',
        '6. Attempt to delete a running plan via REST')
        expected_errors = [
            '"message": "Removing a running/stopping plan is not allowed"',
            '"type": "InvalidRequestError"'
        ]
        stdout, stderr, status = self.rest.remove_plan_rest()
        self.assertEqual(422, status)
        self.assertEqual("", stderr)
        for error in expected_errors:
            self.assertTrue(error in stdout)

        self.log('info',
        '7. Attempt to update a running plan state via REST without '
           'specifying the state')
        expected_errors = [
            '"message": "Invalid state specified"',
            '"type": "InvalidRequestError"'
        ]
        message_data = '{"properties": {"state": ""}}'
        stdout, stderr, status = self.rest.put("/plans/plan/",
                                               self.rest.HEADER_JSON,
                                               message_data)
        self.assertEqual(422, status)
        self.assertEqual("", stderr)
        for error in expected_errors:
            self.assertTrue(error in stdout)

        self.log('info',
        '8. Attempt to update a running plan state via REST to "running"')
        expected_errors = [
            '"message": "Plan is currently running or stopping"',
            '"type": "InvalidRequestError"'
        ]
        message_data = '{"properties": {"state": "running"}}'
        stdout, stderr, status = self.rest.put("/plans/plan/",
                                               self.rest.HEADER_JSON,
                                               message_data)
        self.assertEqual(422, status)
        self.assertEqual("", stderr)
        for error in expected_errors:
            self.assertTrue(error in stdout)

        self.log('info',
        '9. Attempt to update a phase via REST with an invalid state')
        expected_errors = [
            '"message": "Update method on path not allowed"',
            '"type": "MethodNotAllowedError"'
        ]
        message_data = '{"properties": {"state": "invalid"}}'
        stdout, stderr, status = self.rest.put("/plans/plan/phases/1",
                                               self.rest.HEADER_JSON,
                                               message_data)
        self.assertEqual(405, status)
        self.assertEqual("", stderr)
        for error in expected_errors:
            self.assertTrue(error in stdout)

        self.log('info',
        '10. Attempt to delete a phase via REST')
        expected_errors = [
            '"message": "Remove method on path not allowed"',
            '"type": "MethodNotAllowedError"'
        ]
        stdout, stderr, status = self.rest.delete("/plans/plan/phases/1")
        self.assertEqual(405, status)
        self.assertEqual("", stderr)
        for error in expected_errors:
            self.assertTrue(error in stdout)

        self.log('info',
        '11. Get list of phases via REST')
        stdout, stderr, rc = self.rest.get("/plans/plan/phases")
        self.assertEqual("", stderr)
        self.assertEqual(200, rc)
        self.assertNotEqual("", stdout)

        self.log('info',
        '12. Get a particular phase via REST')
        stdout, stderr, rc = self.rest.get("/plans/plan/phases/1")
        self.assertEqual("", stderr)
        self.assertEqual(200, rc)
        self.assertNotEqual("", stdout)

        self.log('info',
        '13. Get list of tasks in phase via REST')
        # This plan has only one task each phase, let's go get the task
        # of phase1
        tasks_uri = "/plans/plan/phases/1/tasks"
        regex = re.compile(tasks_uri + '/' + r'(\w{36})')
        stdout, stderr, rc = self.rest.get(tasks_uri)
        self.assertEqual("", stderr)
        self.assertEqual(200, rc)
        self.assertNotEqual("", stdout)
        matches = regex.search(stdout.replace('-', 'x'))
        self.assertTrue(matches, 'No tasks were found on show_plan output')
        task = matches.group(1)
        task_uri = '{0}/{1}'.format(tasks_uri, task.replace('x', '-'))
        self.log('info', 'Task : {0}'.format(task_uri))

        self.log('info',
        '14. Get a particular task from a phase via REST')
        stdout, stderr, rc = self.rest.get(task_uri)
        self.assertEqual("", stderr)
        self.assertEqual(200, rc)
        self.assertNotEqual("", stdout)

        self.log('info',
        '15. Get list of tasks from a non existing phase via REST')
        expected_errors = [
            '"message": "Invalid phase id :99"',
            '"type": "InvalidLocationError"'
        ]
        stdout, stderr, status = self.rest.get("/plans/plan/phases/99/tasks")
        self.assertEqual(404, status)
        self.assertEqual("", stderr)
        for error in expected_errors:
            self.assertTrue(error in stdout)

        self.log('info',
        '16. Stop a running plan via REST')
        stdout, _, _ = self.rest.stop_plan_rest()
        self.assertTrue(self.json.is_json_hal_complient(json_output=stdout,
                                                        has_children=True,
                                                        has_props=True))

        plan_stopped = self.wait_for_plan_state(self.ms1, const.PLAN_STOPPED)
        self.assertTrue(True, plan_stopped)

        self.log('info',
        '17. Create plan via REST')
        stdout, stderr, rc = self.rest.create_plan_rest()
        self.assertEqual("", stderr)
        self.assertEqual(201, rc)
        self.assertNotEqual("", stdout)

        self.log('info',
        '18. Run plan via REST')
        stdout, stderr, rc = self.rest.run_plan_rest()
        self.assertEqual("", stderr)
        self.assertEqual(200, rc)
        self.assertNotEqual("", stdout)

        self.log('info',
        '19. Check that plan completes successfully')
        plan_complete = self.wait_for_plan_state(self.ms1, const.PLAN_COMPLETE)
        self.assertTrue(True, plan_complete)

    @attr('all', 'revert', 'cdb_tmp')
    def test_02_n_run_non_existing_plan(self):
        """
        @tms_id: litpcds_671_tc02
        @tms_requirements_id: LITPCDS-671
        @tms_title: Error handling of REST request against non existing plan
        @tms_description: Verify that attempting to issue a show, run, stop,
            remove request on a non existing plan result on error thrown.
        @tms_test_steps:
        @step: Issue a show plan command via REST
        @result: InvalidLocationError posted, 404
        @step: Issue a run plan command via REST
        @result: InvalidLocationError posted, 404
        @step: Issue a stop plan command via REST
        @result: InvalidLocationError posted, 404
        @step: Issue a delete plan command via REST
        @result: InvalidLocationError posted, 404
        @tms_test_precondition: no plan created
        @tms_execution_type: Automated
        """
        expected_errors = [
            '"message": "Plan does not exist"',
            '"type": "InvalidLocationError"'
        ]

        actions = {
            self.rest.show_plan_rest: 'show_plan',
            self.rest.stop_plan_rest: 'stop_plan',
            self.rest.run_plan_rest: 'run_plan',
            self.rest.remove_plan_rest: 'remove_plan'
        }

        for action, desc in actions.iteritems():
            self.log('info',
            'Issue a "{0}" on a non existing plan via REST'.format(desc))
            stdout, stderr, status = action()
            self.assertEqual(404, status)
            self.assertEqual("", stderr)
            self.assertNotEqual("", stdout)
            for error in expected_errors:
                self.assertTrue(error in stdout)
            self.assertTrue(self.json.is_json_hal_complient(json_output=stdout,
                                                            has_children=False,
                                                            has_props=False))
