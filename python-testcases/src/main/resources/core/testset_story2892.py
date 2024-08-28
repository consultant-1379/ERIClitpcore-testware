"""
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     May 2014
@author:    Marcin Spoczynski, Jose Martinez, Jenny Schulze
@summary:   LITPCDS-2892
            As an application designer I want MCollective to use SSL so that
            broadcasting to nodes is more secure
"""

from litp_generic_test import GenericTest, attr
from litp_cli_utils import CLIUtils
import test_constants
import socket
import time
import json
import ssl
import os
import re

LOCAL_DIR = os.path.dirname(__file__)


class Story2892(GenericTest):
    """
        As an application designer I want MCollective to use SSL so that
        broadcasting to nodes is more secure.
    """

    def setUp(self):
        """Setup variables for every test"""
        super(Story2892, self).setUp()
        self.cli = CLIUtils()
        self.ms1 = self.get_management_node_filename()
        self.mns = self.get_managed_node_filenames()
        self.all_nodes = [self.ms1] + self.mns
        self.host = self.get_node_att(self.ms1, "ipv4")
        self.rabbitmq_port = 61614
        self.cert_name = 'story2892_cert'
        self.cert_generate_cmd = \
            "/usr/bin/puppet cert --generate {0}".format(self.cert_name)
        self.cert_clean_cmd = \
            "/usr/bin/puppet cert --clean {0}".format(self.cert_name)
        self.local_cert_ca_path = "{0}/{1}_ca.pem". \
            format(LOCAL_DIR, self.cert_name)
        self.local_cert_key_path = "{0}/{1}_key.pem". \
            format(LOCAL_DIR, self.cert_name)

    def tearDown(self):
        """Runs for every test"""
        super(Story2892, self).tearDown()

    def mco_ping_all_nodes_with_timeout(self, cmd):
        """
        mco ping and check all nodes responded
        checks every 10 seconds and times out after 3mins
        """
        timeout = 180
        interval = 10
        passed = 0
        while True:
            out, err, rc = self.run_command(
                self.ms1,
                cmd,
                su_root=True)
            if rc == 0 and err == []:
                if all(
                    any(line.startswith(node_name) for line in out)
                    for node_name in self.all_nodes
                ):
                    return True
            time.sleep(interval)
            passed += interval

            if passed > timeout:
                return False

    def _assert_mco_ping(self, user, with_timeout=False):
        """
        Description:
            Verifies that mco ping return for all nodes
        Args:
            user (str): The user under which to run the mco ping command
        """
        cmd = "/bin/su {0} -c '{1}'".format(user, self.cli.get_mco_cmd('ping'))
        if with_timeout:
            self.assertTrue(
                self.mco_ping_all_nodes_with_timeout(cmd)
            )

        else:
            out, err, rc = self.run_command(self.ms1, cmd, su_root=True)

            self.assertEqual(0, rc)
            self.assertNotEqual([], out)
            self.assertEqual([], err)

            for node in self.all_nodes:
                self.assertTrue(self.is_text_in_list(node, out))

    def _download_file_from_node(self, node, source_path, dest_path):
        """
        Description:
            Fetch content of a file from a given node and store it in a local
            file
        Args:
            node (str): The remote server where the source file is located
            source_path (str): The source file path on remote server
            dest_path (str): The local destination path
        """
        out = self.get_file_contents(node, source_path, su_root=True)
        with open(dest_path, 'w') as out_file:
            for line in out:
                out_file.write("{0}\n".format(line))

    def _generate_puppet_certificate(self, user):
        """
        Description:
            Generates a puppet certificate and download files to local server
        Args:
            user (str): User under which to generate the certificate
        """
        if user == 'root':
            cert_path = '/var/lib/puppet/ssl/ca/signed'
            key_path = '/var/lib/puppet/ssl/private_keys'
            su_root = True
        else:
            cert_path = '/home/{0}/.puppet/ssl/ca/signed'.format(user)
            key_path = '/home/{0}/.puppet/ssl/private_keys'.format(user)
            su_root = False

        self.log('info', 'a. Generate puppet certificate on MS')
        self.run_command(self.ms1,
                         self.cert_generate_cmd,
                         default_asserts=True,
                         su_root=su_root)

        self.log('info', 'b. Download cert and key from ms')
        self._download_file_from_node(
            self.ms1,
            '{0}/{1}.pem'.format(cert_path, self.cert_name),
            self.local_cert_ca_path)

        self._download_file_from_node(
            self.ms1,
            '{0}/{1}.pem'.format(key_path, self.cert_name),
            self.local_cert_key_path)

    def _update_dns(self, dns_client_url, node, domain):
        """
        Description:
            Update the domain name on a given peer node
        Args:
            dns_client_url (str): path to dns_client item
            node (str): Name of the node where to change the domain name
            domain (str): new domain name
        Returns:
            str, The new domain name
        """
        props = 'search="{0}"'.format(domain)
        self.execute_cli_update_cmd(self.ms1, dns_client_url, props)

        self.run_and_check_plan(self.ms1,
                                test_constants.PLAN_COMPLETE,
                                600,
                                add_to_cleanup=False)

        self.stop_service(node, "puppet")
        self.start_service(node, "puppet")

        # if more than one domain for node puppet will take the first
        if "," in domain:
            domain = domain.split(",")[0]

        return domain

    def _assert_new_private_key_has_been_created(self, node, domain):
        """
        Description:
            Check that the new private key file has been created on the
            given peer node
        Args:
            node (str): Name of the peer node
            domain (str): The domain name
        """
        new_key_exists = False
        timeout = self.get_puppet_interval(node)
        counter = 0
        interval = 10
        new_key_file = "/var/lib/puppet/ssl/private_keys/{0}.{1}.pem". \
            format(node, domain)
        while not new_key_exists and counter < timeout:
            new_key_exists = self.remote_path_exists(node,
                                                     new_key_file,
                                                     su_root=True)
            counter += interval
            time.sleep(interval)
        self.assertTrue(new_key_exists)

    def _assert_mcollective_config_has_been_updated(self, node, domain):
        """
        Description:
            Check that mcollective's configuration file has been updated
        Args:
            node (str): Name of the peer node
            domain (str): The domain name
        """
        expect_text = "plugin.rabbitmq.pool.1.ssl.cert = " \
                      "/var/lib/puppet/ssl/certs/{0}.{1}.pem". \
            format(node, domain)

        self.assertTrue(self.wait_for_log_msg(
            node,
            expect_text,
            log_file=test_constants.MCOLLECTIVE_CONFIG_FILE,
            log_len=1,
            timeout_sec=self.get_puppet_interval(node),
            rotated_log=None))

    @attr('all', 'revert', 'story2892', 'story2892_tc11')
    def test_11_p_check_connections(self):
        """
        @tms_id:
            litpcds_2892_tc11
        @tms_requirements_id:
            LITPCDS-2892
        @tms_title:
            Verify that all nodes connect to "rabbitmq" via stomp:61614
            over SSL
        @tms_description:
           This test verifies that:
           - all nodes connect to rabbitmq via stomp on port 61614 over SSL
           - "rabbitmqadmin" can connect to the rabbitMQ api using default
             settings
        @tms_test_steps:
        @step: Get list of connections by issuing the
               "rabbitmqadmin -f raw_json list connections" command
        @result: All nodes are connected to "rabbitMQ"
        @result: All connections are using port 61614
        @result: The certificate issuer is puppet on MS ("CN=Puppet CA: ms1")
        @result: The protocol is "STOPM 1.1."
        @result: The connections are using SSL "tlsv1.2"
        @result: The user is "mcollective"
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        connections = {
            '5672': {
                'peer_cert_issuer': '',
                'protocol': 'AMQP 0-9-1',
                'ssl': False,
                'ssl_protocol': '',
                'user': 'litp'},
            '61614': {
                'peer_cert_issuer': 'CN=Puppet CA: ms1',
                'protocol': 'STOMP 1.1',
                'ssl': True,
                'ssl_protocol': 'tlsv1.2',
                'user': 'mcollective'}
            }

        self.log('info', '1. connect to rabbitmq API')
        cmd = "rabbitmqadmin -f raw_json list connections"
        out, _, _ = self.run_command(self.ms1, cmd, default_asserts=True)
        self.assertNotEqual([], out)

        self.log('info', '2. Verify all nodes are connected to rabbitMQ')
        clients = json.loads(out[0])

        node_ips = [self.get_node_att(node, "ipv4") for node in self.mns] + \
                   ["127.0.0.1"]
        self.log('info', 'List of node IPs found:')
        for node_ip in node_ips:
            self.log('info', node_ip)

        for node_ip in node_ips:
            self.assertTrue(next((item for item in clients if
                item["peer_host"] == "{0}".format(node_ip)), None),
                "node with IP {0} did not connect to rabbitmq".format(node_ip))

        self.log('info', '3. Check established connections')
        for client in clients:
            port = client.get('port')
            self.assertNotEqual(None, port)
            connection = connections.get(str(port))
            self.assertNotEqual(None, connection)

            self.log('info',
                'Port             : "{0}"'.format(port))
            self.log('info',
                'Peer host        : "{0}"'.format(client['peer_host']))
            self.log('info',
                'Peer_cert_issuer : "{0}"'.format(client['peer_cert_issuer']))
            self.log('info',
                'Protocol         : "{0}"'.format(client['protocol']))
            self.log('info',
                'SSL              : "{0}"'.format(client['ssl']))
            self.log('info',
                'SSL protocol     : "{0}"'.format(client['ssl_protocol']))
            self.log('info',
                'User             : "{0}"'.format(client['user']))
            self.log('info', ' ')

            self.assertEqual(connection['peer_cert_issuer'],
                             client['peer_cert_issuer'])
            self.assertEqual(connection['protocol'],
                             client['protocol'])
            self.assertEqual(connection['ssl'],
                             client['ssl'])
            self.assertEqual(connection['ssl_protocol'],
                             client['ssl_protocol'])
            self.assertEqual(connection['user'],
                             client['user'])

    @attr('all', 'revert', 'story2892', 'story2892_tc12')
    def test_12_p_check_ports(self):
        """
        @tms_id:
            litpcds_2892_tc12
        @tms_requirements_id:
            LITPCDS-2892
        @tms_title:
            Verify that rabbitMQ listens on the correct port
        @tms_description:
           This test verifies that:
           - rabbitmq listens on 61613/4 on the public interfaces
           - rabbitmq listens on 25672 and 5672 on localhost
           - all allowed ports are open
        @tms_test_steps:
        @step: Get list connections by issuing the command
               "rabbitmqadmin -f raw_json show overview" command
        @result: List of listener obtained
        @step: Get list of open internet connection via "netstat"
        @result: List obtained
        @step: Compare list of listeners connection with list of open internet
               connections
        @result: rabbitmq listens on 61613 and 61614 on the public interfaces
        @result: rabbitmq listens on 25672 and 5672 on localhost
        @result: all allowed ports are open
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        localhost_ports = ['25672', '5672']
        public_ports = ['61613', '61614']
        allowed_ports = set(localhost_ports + public_ports)
        found = set()
        self.log('info', '1. connect to rabbitmq API')
        cmd = "rabbitmqadmin -f raw_json show overview"
        out, _, _ = self.run_command(self.ms1, cmd, default_asserts=True)
        self.assertNotEqual([], out)

        json_output = json.loads(out[0])
        listeners = json_output[0]['listeners']

        self.log('info', "2. Check open ports from rabbitmq")
        tested_ports = []
        for listener in listeners:
            port = str(listener['port'])
            if port not in tested_ports:
                tested_ports.append(port)
            else:
                continue
            self.log('info', 'Checking port "{0}"'.format(port))
            self.assertTrue(port in allowed_ports,
                            'RabbitMQ listens on disallowed port "{0}"'.
                            format(port))

            if port in localhost_ports:
                # check netstat output, because rabbitmq does not work reliable
                # for the clustering port
                cmd = '/bin/netstat -an | grep :{0}'.format(port)
                out = self.run_command(self.ms1, cmd, default_asserts=True)[0]
                local_addresses = []
                for line in out:
                    netstat_fields = re.split(r'\s+', line)
                    local_address = netstat_fields[3]
                    state = netstat_fields[5]
                    if local_address.endswith(port) and state == 'LISTEN':
                        local_addresses.append(local_address)

                for local_address in local_addresses:
                    if not local_address.startswith('127.0.0.1') and \
                       not local_address.startswith('::'):
                        self.fail('RabbitMQ listens on disallowed port "{0}"'.
                                  format(port))
            else:
                self.assertEqual("::", listener['ip_address'])
            found.add(port)

        self.assertEqual(sorted(allowed_ports), sorted(found))

    @attr('all', 'revert', 'story2892', 'story2892_tc13')
    def test_13_n_no_certificate(self):
        """
        @tms_id:
            litpcds_2892_tc13
        @tms_requirements_id:
            LITPCDS-2892
        @tms_title:
            Verifies that a client without a certificate is rejected
        @tms_description:
            Verifies that a client without a certificate is rejected
        @tms_test_steps:
        @step: Check setting of "fail_if_no_peer_cert" in rabbitmq.config file
        @result: "fail_if_no_peer_cert" is set to "true"
        @step: Connect to rabbitmq using SSL without client certificate
        @result: SSLError "sslv3 alert handshake failure" is thrown
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        self.log('info',
                 '1. Verify that {fail_if_no_peer_cert,true} is set in '
                 'the rabbitmq.config')
        rabbit_config_path = "/etc/rabbitmq/rabbitmq.config"
        rabbit_config = self.get_file_contents(self.ms1, rabbit_config_path)

        self.assertTrue(
            self.is_text_in_list("{fail_if_no_peer_cert,true}", rabbit_config),
            "rabbit_mq is set to allow clients without certificates")

        self.log('info',
        '2. Try to connect to rabbitmq using ssl without client certificate')
        sock = socket.socket()
        try:
            sock.connect((self.host, self.rabbitmq_port))
            sock = ssl.wrap_socket(sock)
            # make sure test fails if above did not throw an exception
            self.fail("Rabbitmq allows clients without certificates")
        except ssl.SSLError as error:
            self.log('info', "3. Verify wrong CA is rejected")
            self.assertTrue("sslv3 alert handshake failure" in error.strerror,
                            "SSL returned unexpected error {0}".format(
                                error.strerror))

            self.log('info',
                     "Expected SSL error found : {0}".format(error.strerror))
        finally:
            sock.close()

    #attr('revert', 'story2892', 'story2892_tc14')
    def obsolete_test_14_p_check_valid_puppet_signed_certificate(self):
        """
        #tms_id:
            litpcds_2892_tc14
        #tms_requirements_id:
            LITPCDS-2892
        #tms_title:
            Verify that a puppet signed certificate is accepted by rabbitmq
        #tms_description:
            Verify that a puppet signed certificate is accepted by rabbitmq
        #tms_test_steps:
        #step: Generate a new puppet certificate
        #result: Certificate successfully generated
        #step: Connect to rabbitmq using the certificate just created
        #result: Connection is successful
        #tms_test_precondition: NA
        #tms_execution_type: Automated
        """
        pass

    @attr('all', 'revert', 'story2892', 'story2892_tc15')
    def test_15_p_verify_everyone_can_use_mco(self):
        """
        @tms_id:
            litpcds_2892_tc15
        @tms_requirements_id:
            LITPCDS-2892
        @tms_title:
            Verify that root, litp-admin and a newly created user can issue
            mco commands successfully
        @tms_description:
            Verify that root, litp-admin and a newly created user can issue
            mco commands successfully
        @tms_test_steps:
        @step: Issue mco ping as "root"
        @result: Ping command is successful
        @step: Issue mco ping as "litp-admin"
        @result: Ping command is successful
        @step: Create a new user and issue mco ping as the new user
        @result: Ping command is successful
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        mco_client_cfg = "/etc/mcollective/client.cfg"
        self.log("info",
                 "1. Verify that {0} exists on the ms".format(mco_client_cfg))
        self.assertTrue(self.remote_path_exists(self.ms1, mco_client_cfg),
                        "All user mco acccess file {0} does not exist".format(
                            mco_client_cfg))

        self.log("info",
                 "2. Verify mco uses port 61613 without ssl")
        mco_content = self.get_file_contents(self.ms1,
                                             mco_client_cfg,
                                             su_root=True)
        self.assertTrue(self.is_text_in_list(
            "plugin.rabbitmq.pool.1.port = 61613", mco_content))
        self.assertFalse(self.is_text_in_list(
            "plugin.rabbitmq.pool.1.ssl = 1", mco_content))

        self.log('info', "3. Issue mco ping as root")
        self._assert_mco_ping(user='root')

        self.log('info', "4. Issue mco ping as litp-admin")
        self._assert_mco_ping(user='litp-admin')

        self.log("info", "5. Create a new user")
        new_user = "userstory2892"
        try:
            cmd = '/usr/sbin/useradd {0}'.format(new_user)
            out, _, _ = self.run_command(self.ms1,
                                         cmd,
                                         su_root=True,
                                         default_asserts=True)
            self.assertEqual([], out)

            self.log("info", "6. Issue mco as the new user")
            self._assert_mco_ping(user=new_user)
        finally:
            self.log('info', '7. Remove newly created user')
            cmd = '/usr/sbin/userdel -r {0}'.format(new_user)
            out, _, _ = self.run_command(self.ms1,
                                         cmd, su_root=True,
                                         default_asserts=True)
            self.assertEqual([], out)

    @attr('all', 'revert', 'story2892', 'story2892_tc16')
    def test_16_n_check_invalid_signed_certificate(self):
        """
        @tms_id:
            litpcds_2892_tc16
        @tms_requirements_id:
            LITPCDS-2892
        @tms_title:
            Verify that a not correctly signed certificate is not accepted by
            rabbitmq
        @tms_description:
            Verify that a not correctly signed certificate is not accepted by
            rabbitmq
        @tms_test_steps:
        @step: Generate an invalid puppet certificate by creating it as
               user "litp-admin"
        @result: Certificate is generated successfully
        @step: Attempt to connect to rabbitmq via SSL using this certificate
        @result: The SSLError "tlsv1 alert unknown ca" error is thrown
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        sock = socket.socket()
        try:
            self.log('info',
                     '1. Generate new puppet certificate as "litp-admin"')
            self._generate_puppet_certificate(user='litp-admin')

            self.log('info',
            '2. Try to connect to rabbitmq via SSL using this certificate')
            # NOTE: Makes use of "litp/puppet" flaw documented in 12191
            # (certificates created with litp-admin are not valid for puppet)
            sock.connect((self.host, self.rabbitmq_port))
            sock = ssl.wrap_socket(sock,
                                   keyfile=self.local_cert_key_path,
                                   certfile=self.local_cert_ca_path)
            # ensure test fails if exception is not raised
            self.fail("Rabbitmq allows clients with invalid certificates")

        except ssl.SSLError as error:
            self.log('info', "3. Verify wrong CA is rejected")
            self.assertTrue("tlsv1 alert unknown ca" in error.strerror,
                            "SSL returned unexpected error {0}".format(
                                error.strerror))

        finally:
            sock.close()
            self.log('info', "4. Clean certificate")
            self.run_command(self.ms1, self.cert_clean_cmd)
            self.run_command_local("/bin/rm {0}".
                                   format(self.local_cert_ca_path))
            self.run_command_local("/bin/rm {0}".
                                   format(self.local_cert_key_path))

    @attr('all', 'revert', 'story2892', 'story2892_tc17')
    def test_17_n_check_not_allowed_ssl_versions(self):
        """
        @tms_id:
            litpcds_2892_tc17
        @tms_requirements_id:
            LITPCDS-2892
        @tms_title:
            Verify that rabbitmq rejects connection with unsupported protocols
        @tms_description:
            Verify that rabbitmq rejects connection with unsupported protocols
            "SSLv2" and "SSLv3" (POODLE attack)
        @tms_test_steps:
        @step: Generate a new puppet certificate as "root"
        @result: Certificate generated successfully
        @step: Attempt to connect to rabbitmq using protocol "SSLv2"
        @result: An SSLError is thrown
        @step: Attempt to connect to rabbitmq using protocol "SSLv3"
        @result: An SSLError is thrown
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        ssl_versions = [("SSLv2", ssl.PROTOCOL_SSLv2),
                        ("SSLv3", ssl.PROTOCOL_SSLv3)]

        try:
            self.log('info', '1. Generate new puppet certificate')
            self._generate_puppet_certificate(user='root')

            self.log('info',
                     '2. Try to connect to rabbitmq via this certificate')
            for (ssl_name, ssl_version) in ssl_versions:
                try:
                    sock = socket.socket()
                    sock.connect((self.host, self.rabbitmq_port))
                    sock = ssl.wrap_socket(sock,
                                           keyfile=self.local_cert_key_path,
                                           certfile=self.local_cert_ca_path,
                                           ssl_version=ssl_version)
                    # ensure test fails if exception is not raised
                    self.fail('Rabbitmq allows clients with '
                              'disallowed protocol {0}'.
                              format(ssl_name))

                except ssl.SSLError as err:
                    self.log('info',
                             "3. Verify unsupported protocol {0} is rejected".
                             format(ssl_name))
                    self.assertTrue(
                        "TLS/SSL connection has been closed" in err.strerror or
                        "tlsv1 alert protocol version" in err.strerror,
                        "SSL returned unexpected error {0}".
                        format(err.strerror))
                finally:
                    sock.shutdown(socket.SHUT_RDWR)
                    sock.close()
        finally:
            self.log('info', "4. Clean certificate")
            self.run_command(self.ms1, self.cert_clean_cmd, su_root=True)
            self.run_command_local("/bin/rm {0}".
                                   format(self.local_cert_ca_path))
            self.run_command_local("/bin/rm {0}".
                                   format(self.local_cert_key_path))

    @attr('all', 'revert', 'story2892', 'story2892_tc18')
    def test_18_p_verify_domainname_can_be_changed(self):
        """
        @tms_id:
            litpcds_2892_tc18
        @tms_requirements_id:
            LITPCDS-2892
        @tms_title:
            Verify that when the domain name of a node is changed the
            mco command still works as expected
        @tms_description:
            This test verifies that when the domain name of a node is changed:
            - a new puppet certificate is created,
            - the mcollective config file is updated and
            - mco commands still work as expected.
            NOTE: verifies Bug LITPCDS-12714, bug TORF-125723
        @tms_test_steps:
        @step: Update domain name of a peer node
        @result: Domain name updated successfully
        @result: The node still replies to mco ping
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """

        self.log('info',
        '1. Identify a peer node to use for this test')
        new_domain = "test2892.com"
        node = self.mns[0]
        test_node_url = self.get_node_url_from_filename(self.ms1, node)
        dns_client_url = self.find(self.ms1, test_node_url, "dns-client")[0]
        orig_domain = self.get_props_from_url(self.ms1,
                                              dns_client_url,
                                              "search")

        try:
            self.log('info',
            '2. Update domain name of the peer node')
            self._update_dns(dns_client_url, node, new_domain)

            self.log('info',
            '3. Verify that the peer node still replies on mco ping')
            self._assert_mco_ping(user='root', with_timeout=True)

        finally:
            self.log('info',
            '4. FINALLY: Roll back changes')
            self._update_dns(dns_client_url, node, orig_domain)
            self._assert_mco_ping(user='root', with_timeout=True)

            self.log('info',
            '5. FINNALLY: Clean puppet certificates')
            cmd = \
                "/usr/bin/puppet cert --clean {0}.{1}".format(node, new_domain)
            self.run_command(self.ms1, cmd, su_root=True)

            for folder in ["certs", "private_keys", "public_keys",
                           "certificate_requests"]:
                cmd = "rm -f /var/lib/puppet/ssl/{0}/{1}.{2}.pem". \
                      format(folder, node, new_domain)
                self.run_command(node, cmd, su_root=True)
