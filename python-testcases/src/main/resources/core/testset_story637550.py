'''
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     March  2023
@author:    Paul Chambers
@summary:   TORF-637550
            Test to verify that RabbitMQ and PuppetServer are configured to
            use TLSv1.2 exclusively.
'''
from litp_generic_test import GenericTest, attr


class Story637550(GenericTest):
    """
    TORF-637550:
        Test to verify that RabbitMQ and PuppetServer are configured to
        use TLSv1.2 exclusively.
    """
    def setUp(self):
        """runs before every test to perform required setup"""
        super(Story637550, self).setUp()
        self.ms_node = self.get_management_node_filename()
        self.puppet_path = "/etc/puppetserver/conf.d/puppetserver.conf"
        self.webserver_path = "/etc/puppetserver/conf.d/webserver.conf"
        self.rabbit_path = "/etc/rabbitmq/rabbitmq.config"

        self.puppetserver_conf = ['# settings related to HTTP client requests'
            ' made by Puppet Server', 'http-client: {', '# A list of'
            ' acceptable protocols for making HTTP requests', 'ssl-protocols:'
            ' [TLSv1.2]']

        self.webserve_conf = [
                'webserver: {',
                'access-log-config = /etc/puppetserver/request-logging.xml',
                'client-auth = want',
                'ssl-host = 0.0.0.0',
                'ssl-port = 8140',
                'ssl-protocols = TLSv1.2',
                'cipher-suites = [TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256,',
                'TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384,',
                'TLS_ECDHE_ECDSA_WITH_AES_128_CBC_SHA256,',
                'TLS_ECDHE_ECDSA_WITH_AES_256_CBC_SHA384,',
                'TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256,',
                'TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384,',
                'TLS_ECDHE_RSA_WITH_AES_128_CBC_SHA256,',
                'TLS_ECDHE_RSA_WITH_AES_256_CBC_SHA384,',
                'TLS_DHE_RSA_WITH_AES_128_GCM_SHA256,',
                'TLS_DHE_RSA_WITH_AES_256_GCM_SHA384,',
                'TLS_DHE_RSA_WITH_AES_128_CBC_SHA256,',
                'TLS_DHE_RSA_WITH_AES_256_CBC_SHA256,',
                'TLS_ECDH_ECDSA_WITH_AES_256_GCM_SHA384,',
                'TLS_ECDH_ECDSA_WITH_AES_256_CBC_SHA384,',
                'TLS_ECDH_ECDSA_WITH_AES_128_GCM_SHA256,',
                'TLS_ECDH_ECDSA_WITH_AES_128_CBC_SHA256]',
                '}']

        self.rabbit_conf = """{ssl, [{versions, ['tlsv1.2']}]},
            {rabbit, [
            {ssl_listeners, [5671]},
            {ssl_options, [{cacertfile,"/etc/rabbitmq/ssl/ca.pem"},
                            {certfile,"/etc/rabbitmq/ssl/server_public.pem"},
                            {keyfile,"/etc/rabbitmq/ssl/server_private.pem"},
                            {verify,verify_peer},
                            {secure_renegotiate,true},
                            {client_renegotiation,false},
                            {fail_if_no_peer_cert,true},
                            {honor_cipher_order,true},
                            {honor_ecc_order,true},
                            {ciphers, [
                                {ecdhe_rsa,aes_256_gcm,aead,sha384},
                                {ecdhe_rsa,aes_256_cbc,sha384,sha384},
                                {ecdhe_rsa,aes_128_gcm,aead,sha256},
                                {ecdhe_rsa,aes_128_cbc,sha256,sha256}]},
                            {versions, ['tlsv1.2']}]},"""

    def tearDown(self):
        """runs after every test to perform required cleanup/teardown"""
        super(Story637550, self).tearDown()

    def _assert_line_in_logs(self, expected_line, log_excerpt):
        """
        Asserts that the log excerpt from /var/log/messages contains the
        expected line.

        Args:
            expected_line (str): This line is expected in the log & will be
            checked for.

            log_excerpt (list): This is the excerpt of logs in list format.
        """

        log_not_found_msg = '"{0}" not found in {1} as expected.'.format(
            expected_line, log_excerpt)
        line_found = False
        self.log('info', 'log_excerpt: {0} '.format(log_excerpt))
        for number in range(len(log_excerpt)):
            if expected_line[number] == log_excerpt[number]:
                line_found = True
                self.log('info', 'expected_line [{0}]: {1} == '
                    'log_excerpt[{0}]: {2}'.format(
                    number, expected_line[number], log_excerpt[number]))
        self.assertTrue(line_found, log_not_found_msg)

    @attr('all', 'revert', 'Story637550', 'Story637550_tc01')
    def test_01_n_rabbitmq_and_puppetserver_only_use_tls_1_2(self):
        """
        @tms_id: TORF-637550_tc01
        @tms_requirements_id: TORF-637550
        @tms_title: Check exclusive use of TLSv1.2
        @tms_description: This test checks the configuration files for
            rabbitMQ, webserver and PupperServer to verify they only use
            TLSv1.2
        @tms_test_steps:
            @step:  Check that the pupperserver.conf file.
            @result:  The puppetserver.conf file contains expected values.
            @step:  Check that the webserver.conf file.
            @result:  The webserver.conf file contains expected values.
            @step:  Check that the rabbitMQ.conf file.
            @result:  The rabbitMQ.conf file contains expected values.
        @tms_test_precondition: None
        @tms_execution_type: Automated
        """
        cmd = ("grep -i "
              "'# settings related to HTTP client requests made by "
              "Puppet Server' -A 3 {0}".format(self.puppet_path))
        self.log('info', ' 1a. cmd : {0}'.format(cmd))
        std_out, _, _ = self.run_command(
                self.ms_node, cmd, su_root=True)

        self._assert_line_in_logs(self.puppetserver_conf, std_out)

        cmd = "cat {0}".format(self.webserver_path)
        self.log('info', ' 1b. cmd : {0}'.format(cmd))
        std_out, _, _ = self.run_command(
                self.ms_node, cmd, su_root=True)

        self._assert_line_in_logs(self.webserve_conf, std_out)

        cmd = "cat {0}".format(self.rabbit_path)
        self.log('info', ' 1c. cmd : {0}'.format(cmd))
        std_out, _, _ = self.run_command(
                self.ms_node, cmd, su_root=True)

        self._assert_line_in_logs(self.rabbit_conf, std_out)
