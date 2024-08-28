'''
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     January 2020
@author:    Bryan McNulty
@summary:   As a LITP user I want the E-tag header disabled in LITP's
            apache webserver's config so that my deployment is more secure
            Agile:TORF-396949

'''

from litp_generic_test import GenericTest, attr
import test_constants as const


class Story396949(GenericTest):
    """
    As a LITP user I want the E-tag header disabled in LITP's
    apache webserver's config so that my deployment is more secure
    """

    def setUp(self):
        """run before every test"""
        super(Story396949, self).setUp()
        self.ms_node = self.get_management_node_filename()

    def tearDown(self):
        """run after every test"""
        super(Story396949, self).tearDown()

    @attr('all', 'revert', 'story396949', 'story396949_tc05')
    def test_05_n_webserver_response(self):
        """
        @tms_id: torf_396949_tc05
        @tms_requirements_id: TORF-396949
        @tms_title:
            Check the responses from the Apache webserver on the LMS.
        @tms_description:
            Check that the responses from the Apache webserver on the LMS
            do not contain the Etag in the header of the message.
        @tms_test_steps:
            @step: Run curl command to get localhost servers response.
            @result: Verify that a response code of 200 is given.
            @step: Check response for ETag element.
            @result: Response does not contain an "ETag" element.
        @tms_test_precondition:NA
        @tms_execution_type: Automated
        """
        self.log('info', "1. Run curl command and check for a successful"\
            "response code in the response.")
        curl_cmd = "{0} -i http://localhost".format(const.CURL_PATH)
        out, _, _ = self.run_command(self.ms_node, curl_cmd)
        httpcode = "HTTP/1.1 200 OK"
        self.assertEqual(httpcode, out[0],
            "The Http response was not \"{0}\" as expected.".format(httpcode))

        self.log('info', "2. Check the http response for absense of an ETag"\
            "element.")
        outstr = ' '.join([str(elem) for elem in out])
        errmesg = "An ETag entry was found in the webserver response."
        self.assertTrue("ETag" not in outstr, errmesg)
