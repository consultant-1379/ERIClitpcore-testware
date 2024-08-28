'''
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     Octobre 2015
@author:    Jose Martinez & Jenny Schulze
@summary:   Integration test for story 9961: Upgrade RabbitMQ to latest stable
            release
            Agile: STORY-9961
'''

from litp_generic_test import GenericTest
from redhat_cmd_utils import RHCmdUtils


class Story9961(GenericTest):
    """
        Upgrade RabbitMQ to latest stable release
    """

    def setUp(self):
        """run before every test"""
        super(Story9961, self).setUp()
        self.ms_node = self.get_management_node_filename()
        self.rhcmd = RHCmdUtils()

    def tearDown(self):
        """run after every test"""
        super(Story9961, self).tearDown()

    def obsolete_03_p_verify_rabbitmq_version(self):
        '''
        MOVED TO MISC_CDB

        Description:
            Verify that RabbitMQ version running on the MS is 3.5.4

        Actions
            1. Check version

        Result:
            RabbitMQ version running on the MS is 3.5.4
        '''

        self.log("info", "1. Check version")
        expected_output = "{rabbit,\"RabbitMQ\",\"3.5.4\"}"

        cmd = "/usr/sbin/rabbitmqctl status"

        out, _, _ = self.run_command(self.ms_node, cmd, su_root=True,
                                        default_asserts=True)
        self.assertTrue(self.is_text_in_list(expected_output, out))

    def obsolete_04_p_verify_rabbitmq_description(self):
        '''
        MOVED TO MISC_CDB

        Description:
            Verify that when I check the version of EXTRlitprabbitmqserver
            using rpm -qi command then the repackaged version of
            RabbitMQ-Server is 3.5.4 in the description field.

        Actions
            1. Check description

        Result:
            Check version of RabbitMQ-Server is 3.5.4 in the description field
            of EXTRlitprabbitmqserver
        '''

        self.log("info", "1. Check description")
        expected_output = "RabbitMQ 3.5.4"

        cmd = "/bin/rpm -q --queryformat \"%{DESCRIPTION}\n\" "\
              "EXTRlitprabbitmqserver_CXP9031043"
        out, _, _ = self.run_command(self.ms_node, cmd, su_root=True,
                                        default_asserts=True)
        self.assertTrue(self.is_text_in_list(expected_output, out))
