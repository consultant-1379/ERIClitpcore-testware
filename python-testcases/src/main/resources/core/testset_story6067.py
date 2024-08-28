'''
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     February  2015
@author:    Maurizio, Maria
@summary:   Integration test for LITPCDS-6067
                As a LITP administrator in a disaster recovery situation
                I want to be able to restore my deployment from the MS
                and a backed up version of the model
            Bug LITPCSD-10079
                Ensure that default puppet manifest files are reinstated after
                running prepare_restore
            StoryBug LITPCDS-10593
                Any LITP items under "/ms" will not be set back to "Initial"
                Changes to prepare_restore logic brought about by this
                StoryBug has made most of the following tests no longer
                valid. Test for new prepare_restore logic can be found
                on testset_story10593
'''

import os
from litp_generic_test import GenericTest, attr


class Story6067(GenericTest):
    """
    LITPCDS-6067:
    As a LITP administrator in a disaster recovery situation
    I want to be able to restore my deployment from the MS
    and a backed up version of the model.
    """

    def setUp(self):
        """runs before every test to perform required setup"""
        # call super class setup
        super(Story6067, self).setUp()
        self.ms_node = self.get_management_node_filename()

    def tearDown(self):
        """runs after every test to perform required cleanup/teardown"""
        # call super class teardown
        super(Story6067, self).tearDown()

    @staticmethod
    def _is_cli_error_message_found(err_list, result):
        """
        Description:
            Check that give path and message pair is found in error messages
        Args:
            err_list (list): list of error messages and paths
            result (dict):  dictionary of error data
        """
        found = False
        if result.get('path') is not None:
            for i in xrange(len(err_list) - 1):
                if err_list[i] == result.get('path') and \
                   err_list[i + 1] == result['msg']:
                    found = True
                    break
        else:
            for line in err_list:
                if line == result['msg']:
                    found = True
                    break
        return found

    @attr('all', 'revert', 'story6067', 'story6067_tc12')
    def test_12_n_prepare_restore_xml(self):
        """
        Description:
            test that /litp/prepare-restore is not included in the XML export
            and cannot be exported

        Actions:
            1. Verify that "prepare-restore" element in the XML export of "/"
              1a. Export LITP  "/" (root) LITP model
              1b. Check that "prepare_restore" element is not in the exported
                  file
            2. Verify that path "/litp/prepare-restore" cannot be exported
              2a. Attempt to export the path "/litp/prepare-restore"
              2b. Check that expected error is posted
        """
        self.log('info',
        '1. Verify that "prepare-restore" element in the XML export of "/"')
        self.log('info',
        '1a. Export LITP  "/" (root) LITP model')
        tmp_path = '/tmp'
        root_xml = os.path.join(tmp_path, 'root.xml')
        prepare_restore_xml = os.path.join(tmp_path,
                                           'prepare-restore.xml')

        self.execute_cli_export_cmd(self.ms_node, "/", root_xml)

        self.log('info',
        '1b. Check that "prepare_restore" element is not in the exported file')
        stdout, stderr, rc = self.run_command(self.ms_node,
            self.rhc.get_grep_file_cmd(root_xml, ['<litp:prepare-restore ']))
        self.assertEqual(1, rc)
        self.assertEqual([], stderr)
        self.assertEqual([], stdout)

        self.log('info',
        '2. Verify that path "/litp/prepare-restore" cannot be exported')
        self.log('info',
        '2a. Attempt to export the path "/litp/prepare-restore"')
        _, stderr, _ = self.execute_cli_export_cmd(self.ms_node,
                                                   '/litp/prepare-restore',
                                                   prepare_restore_xml,
                                                   expect_positive=False)

        self.log('info',
        '2b. Check that expected error is posted')
        expected_err = 'MethodNotAllowedError    Operation not permitted'
        self.assertTrue(self.is_text_in_list(expected_err, stderr),
            "\nExpected error message:\n{0}NOT found in\n{1}"
            .format(expected_err, '\n'.join(stderr)))
