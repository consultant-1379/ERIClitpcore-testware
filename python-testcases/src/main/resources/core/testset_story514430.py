'''
COPYRIGHT Ericsson 2021
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     May 2021
@author:    Philip Daly
@summary:   For security, specific ports need to be closed.
            Agile: TORF-514430
'''

from litp_generic_test import GenericTest, attr
import re


class Story514430(GenericTest):
    """
    For security, specific ports need to be closed.
    """

    def setUp(self):
        """run before every test"""
        super(Story514430, self).setUp()
        self.ms_node = self.get_management_node_filename()

    def tearDown(self):
        """run after every test"""
        super(Story514430, self).tearDown()

    def gather_open_ports(self, protocol):
        """
        Description:
            Function to gather the open TCP/UDP ports on the MS.
        Args:
            protocol (str): TCP or UDP.
        Returns:
            list. A list of open ports on the MS.
        """
        if protocol == "TCP":
            netstat_cmd = "netstat -ltn | awk -F\" \" '{print $4}'"
        else:
            netstat_cmd = "netstat -lun | awk -F\" \" '{print $4}'"
        netstat_addresses, _, _ = \
            self.run_command(self.ms_node, netstat_cmd)

        open_ports = \
        [line.split(':')[-1] for line in netstat_addresses
         if re.search(r'[0-9:]', line[0])]
        # Removing duplicate entries
        open_ports = list(dict.fromkeys(open_ports))
        return open_ports

    @staticmethod
    def check_ports_are_closed(expected_closed_ports, open_ports):
        """
        Description:
            Checks a list of ports which are expected to be closed against
            a list of ports found to be open.
        Args:
            expected_closed_ports (list): The ports expected to be closed.
            open_ports (list): The ports found to be open.
        Returns:
            list. A list of port found to be open
                  which were expected to be closed.
        """
        issue_ports = \
        [port for port in expected_closed_ports if port in open_ports]
        return issue_ports

    @attr('all', 'revert', 'story514430', 'story514430_tc01')
    def test_01_p_chk_ports_closed(self):
        """
        @tms_id: torf_514430_tc01
        @tms_requirements_id: TORF-514430
        @tms_title: Check closed ports.
        @tms_description:
            Test to verify that the list of retrieved open ports
            does not include any ports which are expected to be
            closed.
        @tms_test_steps:
            @step: Gather the list of TCP open ports.
            @result: TCP open ports are gathered.
            @step: Gather the list of UDP open ports.
            @result: UDP open ports are gathered.
            @step: Ensure no port expected to be closed is open.
            @result: No port expected to be closed is open.
        @tms_test_precondition:NA
        @tms_execution_type: Automated
        """
        # Lists of TCP & UDP ports expected to be closed.
        tcp_ports_expected_closed = ["443"]
        udp_ports_expected_closed = ["443"]

        self.log('info', "Gather the open TCP ports on the MS.")
        open_tcp_ports = self.gather_open_ports("TCP")

        issue_tcp_ports = \
        self.check_ports_are_closed(tcp_ports_expected_closed, open_tcp_ports)

        self.log('info', "Gather the open UDP ports on the MS.")
        open_udp_ports = self.gather_open_ports("UDP")

        issue_udp_ports = \
        self.check_ports_are_closed(udp_ports_expected_closed, open_udp_ports)

        self.assertEqual([], issue_tcp_ports,
                         "The following TCP ports were found "
                         "to be open on the MS: " + ", ".join(issue_tcp_ports))
        self.assertEqual([], issue_udp_ports,
                         "The following UDP ports were found "
                         "to be open on the MS: " + ", ".join(issue_udp_ports))
