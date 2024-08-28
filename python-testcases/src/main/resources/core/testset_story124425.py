"""
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     August 2016
@author:    Maurizio Senno
@summary:   TORF-124425
            As a LITP installer I want to configure Celery (3.1.18) Workers
            to provide LITP the ability to run parts of its plan in parallel
"""
from litp_generic_test import GenericTest, attr
import test_constants as const


class Story124425(GenericTest):
    """
        As a LITP installer I want to configure Celery (3.1.18) Workers
        to provide LITP the ability to run parts of its plan in parallel
    """

    def setUp(self):
        """ Runs before every single test """
        super(Story124425, self).setUp()
        self.ms1 = self.get_management_node_filenames()[0]

    def tearDown(self):
        """ Runs after every single test """
        super(Story124425, self).tearDown()

    @attr('all', 'revert', 'story124425', 'story124425_tc01')
    def test_01_p_verify_that_celery_is_installed(self):
        """
        @tms_id:
            torf_124425_tc_01
        @tms_requirements_id:
            TORF-124425
        @tms_title:
            Verify that Celery is enabled on the MS system
        @tms_description:
            Verify that Celery is enabled on the MS system
        @tms_test_steps:
            @step: Run the command "ps aux | grep -i "celery worker"
            @result: At least one postgres process owned by puppedb is found
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        cmd = '{0} -ef | {1} -i "celery worker" | {1} -v grep'.format(
            const.PS_PATH, const.GREP_PATH)
        stdout, _, _ = self.run_command(self.ms1, cmd, default_asserts=True)
        self.assertTrue(len(stdout) > 0,
            'No celery workers were found running on system')
