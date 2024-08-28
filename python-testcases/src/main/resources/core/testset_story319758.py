'''
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     January 2019
@author:    Sam Luby
@summary:   TORF-319758
            Integration test to check that the files critical to the startup
            of celeryd and celerybeat have the correct file ownership (user
            and group). The files should have ownership 'celery celery'
'''
from litp_generic_test import GenericTest, attr
import test_constants as consts
import os


class Story319758(GenericTest):
    """
    TORF-319758:
        Introduce IT to check ownership of files criticial to the start up of
        celeryd and celerybeat services
    """
    def setUp(self):
        """runs before every test to perform required setup"""
        super(Story319758, self).setUp()
        self.ms_node = self.get_management_node_filename()
        self.stat = consts.STAT_PATH

        # filepath to file/folder, boolean to check recursive files
        self.celery_files = [
            (consts.METRICS_LOG, False),
            (consts.LITPD_ACCESS_LOG, False),
            (consts.LITPD_ERROR_LOG, False),
            ('/var/log/litp', False),
            ('/var/run/celery', True)]
        self.celery_ownership = 'celery celery'
        self.incorrect_owner_string = 'has incorrect ownership'

    def tearDown(self):
        """runs after every test to perform required cleanup/teardown"""
        super(Story319758, self).tearDown()

    def check_file_ownership(self, file_path):
        """
        Description:
            Gets the file ownership for the input file and checks it matches
            the expected (group:celery, user:celery).

        Args:
            file_path (str): Path of the file to check ownership of
        """
        cmd = '{0} -c "%U %G" {1}'.format(consts.STAT_PATH, file_path)
        ownership, _, _ = self.run_command(self.ms_node, cmd, su_root=True,
                                           default_asserts=True)
        ownership = ownership[0]
        self.assertEqual(ownership, self.celery_ownership,
                        '{0} {1} '.format(file_path,
                        self.incorrect_owner_string))

    @attr('all', 'revert', 'Story319758', 'Story319758_tc01')
    def test_01_p_celery_files_have_correct_ownership(self):
        """
        @tms_id: TORF_319758_tc01
        @tms_requirements_id: TORF-289907
        @tms_title: Check correct ownership of celery files
        @tms_description:
            Verify that the list of files used by celeryd and celerybeat
            have the correct ownership (user and group)
        @tms_test_steps:
            @step: Verify the ownership of the list of files
            @result: Each file has correct ownership
        @tms_test_precondition: N/A
        @tms_execution_type: Automated
        """

        for celery_file, check_contents in self.celery_files:
            is_dir = self.remote_path_exists(self.ms_node, celery_file,
                                             expect_file=False)
            if is_dir and check_contents:
                contents = self.list_dir_contents(self.ms_node, celery_file)
                for content in contents:
                    full_path = os.path.join(celery_file, content)
                    self.check_file_ownership(full_path)
            else:
                self.check_file_ownership(celery_file)
