"""
COPYRIGHT Ericsson 2023
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@date:      March 2023
@author:    Eoin Hughes
@summary:   Verify the options for manage_postgres_certs.sh work
"""

from litp_generic_test import GenericTest, attr
import datetime


# This is used for TC37, it's up here due to formatting issues
DELTASCRIPT = """from datetime import datetime
from dateutil.relativedelta import relativedelta
start = datetime.strptime("{0}", "{3} ")
newdate = start + relativedelta({1}={2})
print(newdate.strftime("{3}"))
"""


class Story615959(GenericTest):
    """
    TORF-615959
    Setup logging/filehandler for litpd_error.log at litp service startup
    so correct ownership of file is preserved if the file is removed.
    """

    def setUp(self):
        """ Runs before every single test """
        super(Story615959, self).setUp()
        self.ms_node = self.get_management_node_filename()
        # Filesystem location of cert regeneration script
        self.cert_cmd = "/opt/ericsson/nms/litp/bin/manage_postgres_certs.sh"
        # Datetime format used by the cert regeneration script
        self.cert_time_fmt = "%b %d %H:%M:%S %Y %Z"

    def tearDown(self):
        """ Runs after every single test """
        super(Story615959, self).tearDown()

    def _get_certtimes(self):
        """
        Description:
            Returns a list of timestamps returned from
            '/opt/ericsson/nms/litp/bin/manage_postgres_certs.sh'
        Returns:
            A list of datetime objects
        """
        stdout, _, _ = self.run_command(self.ms_node, "{0} -e".format(
            self.cert_cmd), su_root=True)
        expiry_output = [line.split("expires on")[1].strip() for line in stdout
            if "expires on" in line]
        expiry_dates = [datetime.datetime.strptime(tstamp, self.cert_time_fmt)
            for tstamp in expiry_output]

        return expiry_dates

    def _get_ms_datetime(self):
        """
        Description:
            Returns a datetime object representing the current time on the MS
        Returns:
            A datetime object of the current time on the MS
        """
        stdout, _, _ = self.run_command(self.ms_node, "date +'{0}'".format(
            self.cert_time_fmt))
        return datetime.datetime.strptime(stdout[0], self.cert_time_fmt)

    def _get_relative_delta(self, date, unit, quantity):
        """
        Description:
            Uses the relativedelta library on the ms to return an
            updated date
        Args:
            date (datetime.datetime): The base date to update
            unit (string): The unit of time to add onto @date
                  e.g. {days, months, years}
        Returns:
            A datetime object of the updated date
        """
        dscript = DELTASCRIPT.format(date.strftime(self.cert_time_fmt),
                                          unit, quantity, "%b %d %H:%M:%S %Y")

        stdout, _, _ = self.run_command(self.ms_node, "python -c '{0}'".format(
            dscript), su_root=False, default_asserts=True)
        return datetime.datetime.strptime(stdout[0], "%b %d %H:%M:%S %Y")

    def _assert_expiry_timestamps_have_not_changed(self, old_timestamps):
        """
        Description:
            Returns a datetime object representing the current time on the MS
        Args:
            old_timestamps (list): A list of the datestamps to comare against
        Raises:
            AssertionError if the current cert expiry dates do not match
            old_timestamps
        """
        # Verify the expiry times have not changed
        new_timestamps = self._get_certtimes()
        for (old, new) in zip(old_timestamps, new_timestamps):
            self.assertEquals(old, new, "Timestamps have changed unexpectedly")

    @attr('all', 'revert', 'story_615959', 'story_615959_tc35')
    def test_35_p_verify_cert_script_works_without_minus_t_option(self):
        """
        @tms_id: torf_615959_tc35
        @tms_requirements_id: TORF-615959
        @tms_title: Verify manage_postgres_certs.sh -r runs normally without
            -t flag and extends the certs by 50 years
        @tms_description:
        @tms_test_steps:
            @step: Get the current postgres cert expiry times by running
                '/opt/ericsson/nms/litp/bin/manage_postgres_certs.sh -e'
            @result: The current expiry times are returned
            @step: Invoke manage_postgres_certs.sh with '-r' and no '-t'
                argument
            @result: The script returns a zero return code
            @step: Get the current cert expiry times
            @result: The timestamps are 50 years ahead of today's date
        @tms_test_precondition: None
        @tms_execution_type: Automated
        """
        # Get MS time
        current_datetime = self._get_ms_datetime()
        expected_expiry = self._get_relative_delta(current_datetime, "years",
            50)

        # Allow a drift of 5 minutes, as the script takes time to run
        minutes_allowed = 5
        threshold = datetime.timedelta(seconds=(minutes_allowed * 60))

        # Run the regeneration script without -t parameter
        _ = self.run_command(self.ms_node, "{0} -r".format(
            self.cert_cmd), su_root=True, default_asserts=True)

        # Check the updated times
        updated_timestamps = self._get_certtimes()

        for expiry_date in updated_timestamps:
            self.assertTrue(expiry_date - expected_expiry < threshold,
                ("Actual expiry date {0} is more than {1} minutes greater"
                 "than expected expiry {2}".format(expiry_date, threshold,
                 expected_expiry)))

    @attr('all', 'revert', 'story_615959', 'story_615959_tc36')
    def test_36_n_verify_cert_script_does_not_accept_negative_minus_t(self):
        """
        @tms_id: torf_615959_tc36
        @tms_requirements_id: TORF-615959
        @tms_title: Verify manage_postgres_certs.sh -t rejects negative values
        @tms_description:
        @tms_test_steps:
            @step: Get the current postgres cert expiry times by running
                '/opt/ericsson/nms/litp/bin/manage_postgres_certs.sh -e'
            @result: The current expiry times are returned
            @step: Invoke manage_postgres_certs.sh with '-t' and a negative
                value as an argument
            @result: The script returns a non-zero return code
            @step: Get the current cert expiry times, and check they have
                not changed
            @result: The timestamps have not changed
        @tms_test_precondition: None
        @tms_execution_type: Automated
        """
        # Get the expiry times
        original_timestamps = self._get_certtimes()
        # Run regeneration script, with an invalid time
        _, _, rc = self.run_command(self.ms_node,
            "{0} -r -t -1d".format(self.cert_cmd), su_root=True)
        self.assertNotEqual(rc, 0,
            "Invalid invocation of {0} returned 0".format(
            self.cert_cmd))
        # Verify the expiry times have not changed
        self._assert_expiry_timestamps_have_not_changed(original_timestamps)

    @attr('all', 'revert', 'story_615959', 'story_615959_tc37')
    def test_37_p_verify_each_time_type_is_supported(self):
        """
        @tms_id: torf_615959_tc37
        @tms_requirements_id: TORF-615959
        @tms_title: Verify manage_postgres_certs.sh rejects bad time types
        @tms_description:
        @tms_test_steps:
            @step: For each type 'd', 'D', 'm', 'M', 'y', 'Y'
            @result: peform the next step with that type
            @step: Invoke the cert script with the given type
            @result: Cert is extended by the corresponding period
        @tms_test_precondition: None
        @tms_execution_type: Automated
        """
        # For each time type (day, month, year)
        #   Get the date on the SUT - parse it
        #   run script
        #   Check cert expiry
        #   Check that the difference between the expiry and (MS-date + delta)
        #      is less than 1 hour
        types = {"d": "days",
                 "D": "days",
                 "m": "months",
                 "M": "months",
                 "y": "years",
                 "Y": "years"
                }
        # Allow a drift of 5 minutes, as the script takes time to run
        minutes_allowed = 5
        threshold = datetime.timedelta(seconds=(minutes_allowed * 60))
        for type_code, long_name in types.items():
            # Get current date
            ms_date = self._get_ms_datetime()
            expected_expiry = self._get_relative_delta(ms_date, long_name, 1)
            _ = self.run_command(self.ms_node,
                "{0} -r -t 1{1}".format(self.cert_cmd, type_code),
                su_root=True)
            new_expiries = self._get_certtimes()
            for expiry_date in new_expiries:
                self.assertTrue(expiry_date - expected_expiry < threshold,
                    ("Actual expiry date {0} is more than {1} minutes greater"
                     "than expected expiry {2}".format(expiry_date, threshold,
                     expected_expiry)))

    @attr('all', 'revert', 'story_615959', 'story_615959_tc38')
    def test_38_n_verify_cert_script_minus_t_rejects_bad_time_types(self):
        """
        @tms_id: torf_615959_tc38
        @tms_requirements_id: TORF-615959
        @tms_title: Verify manage_postgres_certs.sh rejects bad time types
        @tms_description:
        @tms_test_steps:
            @step: Get the current postgres cert expiry times by running
                '/opt/ericsson/nms/litp/bin/manage_postgres_certs.sh -e'
            @result: The current expiry times are returned
            @step: Invoke manage_postgres_certs.sh with '-t' and an invalid
                time type as an argument
            @result: The script returns a non-zero return code
            @step: Get the current cert expiry times, and check they have
                not changed
            @result: The timestamps have not changed
        @tms_test_precondition: None
        @tms_execution_type: Automated
        """
        # Get the expiry times
        original_timestamps = self._get_certtimes()

        # Run regeneration script with a bad time parameter
        _, _, rc = self.run_command(self.ms_node,
            "{0} -r -t 1h".format(self.cert_cmd), su_root=True)
        self.assertNotEqual(rc, 0,
            "Invalid invocation of {0} returned 0".format(
            self.cert_cmd))

        # Verify the expiry times have not changed
        self._assert_expiry_timestamps_have_not_changed(original_timestamps)

    @attr('all', 'revert', 'story_615959', 'story_615959_tc39')
    def test_39_n_verify_cert_script_minus_t_requires_parameter(self):
        """
        @tms_id: torf_615959_tc39
        @tms_requirements_id: TORF-615959
        @tms_title: Verify manage_postgres_certs.sh rejects bad time types
        @tms_description:
        @tms_test_steps:
            @step: Get the current postgres cert expiry times by running
                '/opt/ericsson/nms/litp/bin/manage_postgres_certs.sh -e'
            @result: The current expiry times are returned
            @step: Invoke manage_postgres_certs.sh with a '-t' option and
                no other parameter
            @result: The script returns a non-zero return code
            @step: Get the current cert expiry times, and check they have
                not changed
            @result: The timestamps have not changed
        @tms_test_precondition: None
        @tms_execution_type: Automated
        """
        # Get the expiry times
        original_timestamps = self._get_certtimes()

        # Run regeneration script with no time parameter
        _, _, rc = self.run_command(self.ms_node,
            "{0} -r -t".format(self.cert_cmd), su_root=True)
        self.assertNotEqual(rc, 0,
            "Invalid invocation of {0} returned 0".format(
            self.cert_cmd))

        # Verify the expiry times have not changed
        self._assert_expiry_timestamps_have_not_changed(original_timestamps)

    @attr('all', 'revert', 'story_615959', 'story_615959_tc40')
    def test_40_n_verify_cert_script_minus_t_reqs_numeric_parameter(self):
        """
        @tms_id: torf_615959_tc40
        @tms_requirements_id: TORF-615959
        @tms_title: Verify manage_postgres_certs.sh -t option requires a
            numeric parameter
        @tms_description:
        @tms_test_steps:
            @step: Get the current postgres cert expiry times by running
                '/opt/ericsson/nms/litp/bin/manage_postgres_certs.sh -e'
            @result: The current expiry times are returned
            @step: Invoke manage_postgres_certs.sh with a '-t' option and
                a non-numeric parameter
            @result: The script returns a non-zero return code
            @step: Get the current cert expiry times, and check they have
                not changed
            @result: The timestamps have not changed
        @tms_test_precondition: None
        @tms_execution_type: Automated
        """
        # Get the expiry times
        original_timestamps = self._get_certtimes()

        # Run regeneration script with non-numeric time parameter
        _, _, rc = self.run_command(self.ms_node,
            "{0} -r -t OneYear".format(self.cert_cmd), su_root=True)
        self.assertNotEqual(rc, 0,
            "Invalid invocation of {0} returned 0".format(
            self.cert_cmd))

        # Verify the expiry times have not changed
        self._assert_expiry_timestamps_have_not_changed(original_timestamps)

    @attr('all', 'revert', 'story_615959', 'story_615959_tc41')
    def test_41_n_verify_cert_script_minus_t_rejects_multiple_units(self):
        """
        @tms_id: torf_615959_tc41
        @tms_requirements_id: TORF-615959
        @tms_title: Verify manage_postgres_certs.sh rejects multiple
            invocations of the '-t' argument
        @tms_description:
        @tms_test_steps:
            @step: Get the current postgres cert expiry times by running
                '/opt/ericsson/nms/litp/bin/manage_postgres_certs.sh -e'
            @result: The current expiry times are returned
            @step: Invoke manage_postgres_certs.sh with two valid time
                units
            @result: The script returns a non-zero return code
            @step: Get the current cert expiry times, and check they have
                not changed
            @result: The timestamps have not changed
        @tms_test_precondition: None
        @tms_execution_type: Automated
        """
        # Get the expiry times
        original_timestamps = self._get_certtimes()

        # Run regeneration script with multiple time units
        _, _, rc = self.run_command(self.ms_node,
            "{0} -r -t 1d1y".format(self.cert_cmd), su_root=True)
        self.assertNotEqual(rc, 0,
            "Invalid invocation of {0} returned 0".format(
            self.cert_cmd))

        # Verify the expiry times have not changed
        self._assert_expiry_timestamps_have_not_changed(original_timestamps)

    @attr('all', 'revert', 'story_615959', 'story_615959_tc42')
    def test_42_n_verify_cert_script_minus_t_rejects_floating_point(self):
        """
        @tms_id: torf_615959_tc42
        @tms_requirements_id: TORF-615959
        @tms_title: Verify manage_postgres_certs.sh -t rejects floating point
            values
        @tms_description:
        @tms_test_steps:
            @step: Get the current postgres cert expiry times by running
                '/opt/ericsson/nms/litp/bin/manage_postgres_certs.sh -e'
            @result: The current expiry times are returned
            @step: Invoke manage_postgres_certs.sh with '-t' argument
                and a floating-point value
            @result: The script returns a non-zero return code
            @step: Get the current cert expiry times, and check they have
                not changed
            @result: The timestamps have not changed
        @tms_test_precondition: None
        @tms_execution_type: Automated
        """
        # Get the expiry times
        original_timestamps = self._get_certtimes()

        # Run regeneration script with floating-point time parameter
        _, _, rc = self.run_command(self.ms_node,
            "{0} -r -t 1.5d".format(self.cert_cmd), su_root=True)
        self.assertNotEqual(rc, 0,
            "Invalid invocation of {0} returned 0".format(
            self.cert_cmd))

        # Verify the expiry times have not changed
        self._assert_expiry_timestamps_have_not_changed(original_timestamps)

    @attr('all', 'revert', 'story_615959', 'story_615959_tc43')
    def test_43_n_verify_cert_script_minus_t_rejects_preceding_zeros(self):
        """
        @tms_id: torf_615959_tc43
        @tms_requirements_id: TORF-615959
        @tms_title: Verify manage_postgres_certs.sh -t rejects values with
            preceding zeros
        @tms_description:
        @tms_test_steps:
            @step: Get the current postgres cert expiry times by running
                '/opt/ericsson/nms/litp/bin/manage_postgres_certs.sh -e'
            @result: The current expiry times are returned
            @step: Invoke manage_postgres_certs.sh with '-t' argument
                and an otherwise valid value, but preceded with a 0
            @result: The script returns a non-zero return code
            @step: Get the current cert expiry times, and check they have
                not changed
            @result: The timestamps have not changed
        @tms_test_precondition: None
        @tms_execution_type: Automated
        """
        # Get the expiry times
        original_timestamps = self._get_certtimes()

        # Run regeneration script with time parameter starting with 0
        _, _, rc = self.run_command(self.ms_node,
            "{0} -r -t 05d".format(self.cert_cmd), su_root=True)
        self.assertNotEqual(rc, 0,
            "Invalid invocation of {0} returned 0".format(
            self.cert_cmd))

        # Verify the expiry times have not changed
        self._assert_expiry_timestamps_have_not_changed(original_timestamps)

    @attr('all', 'revert', 'story_615959', 'story_615959_tc44')
    def test_44_n_verify_cert_script_minus_t_rejects_time_unit_typos(self):
        """
        @tms_id: torf_615959_tc44
        @tms_requirements_id: TORF-615959
        @tms_title: Verify manage_postgres_certs.sh -t rejects values with
            malformed time units
        @tms_description:
        @tms_test_steps:
            @step: Get the current postgres cert expiry times by running
                '/opt/ericsson/nms/litp/bin/manage_postgres_certs.sh -e'
            @result: The current expiry times are returned
            @step: Invoke manage_postgres_certs.sh with '-t' argument
                and a value with multiple valid time units
            @result: The script returns a non-zero return code
            @step: Get the current cert expiry times, and check they have
                not changed
            @result: The timestamps have not changed
        @tms_test_precondition: None
        @tms_execution_type: Automated
        """
        # Get the expiry times
        original_timestamps = self._get_certtimes()

        # Run regeneration script with time parameter starting with 0
        _, _, rc = self.run_command(self.ms_node,
            "{0} -r -t 1my".format(self.cert_cmd), su_root=True)
        self.assertNotEqual(rc, 0,
            "Invalid invocation of {0} returned 0".format(
            self.cert_cmd))

        # Verify the expiry times have not changed
        self._assert_expiry_timestamps_have_not_changed(original_timestamps)

    @attr('all', 'revert', 'story_615959', 'story_615959_tc46')
    def test_46_n_verify_cert_script_rejects_minus_t_more_than_once(self):
        """
        @tms_id: torf_615959_tc46
        @tms_requirements_id: TORF-615959
        @tms_title: Verify manage_postgres_certs.sh -t rejects -t argument
            specified more than once
        @tms_description:
        @tms_test_steps:
            @step: Get the current postgres cert expiry times by running
                '/opt/ericsson/nms/litp/bin/manage_postgres_certs.sh -e'
            @result: The current expiry times are returned
            @step: Invoke manage_postgres_certs.sh with multiple valid '-t'
                arguments
            @result: The script returns a non-zero return code
            @step: Get the current cert expiry times, and check they have
                not changed
            @result: The timestamps have not changed
        @tms_test_precondition: None
        @tms_execution_type: Automated
        """
        # Get the expiry times
        original_timestamps = self._get_certtimes()

        # Run regeneration script with time parameter starting with 0
        _, _, rc = self.run_command(self.ms_node,
            "{0} -r -t 1y -t 1m".format(self.cert_cmd), su_root=True)
        self.assertNotEqual(rc, 0,
            "Invalid invocation of {0} returned 0".format(
            self.cert_cmd))

        # Verify the expiry times have not changed
        self._assert_expiry_timestamps_have_not_changed(original_timestamps)

    @attr('all', 'revert', 'story_615959', 'story_615959_tc47')
    def test_47_n_verify_cert_script_rejects_minus_t_without_g_or_r(self):
        """
        @tms_id: torf_615959_tc47
        @tms_requirements_id: TORF-615959
        @tms_title: Verify manage_postgres_certs.sh -t rejects -t argument
            in conjunction with arguments other than -r and -g
        @tms_description:
        @tms_test_steps:
            @step: Get the current postgres cert expiry times by running
                '/opt/ericsson/nms/litp/bin/manage_postgres_certs.sh -e'
            @result: The current expiry times are returned
            @step: Invoke manage_postgres_certs.sh with '-t' with conflicting
                arguments
            @result: The script returns a non-zero return code
            @step: Get the current cert expiry times, and check they have
                not changed
            @result: The timestamps have not changed
        @tms_test_precondition: None
        @tms_execution_type: Automated
        """
        conflicting_flags = ['-e', '-h', 'c']

        for flag in conflicting_flags:
            # Get the expiry times
            original_timestamps = self._get_certtimes()

            # Run regeneration script with conflicting options
            _, _, rc = self.run_command(self.ms_node,
                "{0} {1} -t 1y".format(self.cert_cmd, flag), su_root=True)
            self.assertNotEqual(rc, 0,
                "Invalid invocation of {0} returned 0".format(
                self.cert_cmd))

            # Verify the expiry times have not changed
            self._assert_expiry_timestamps_have_not_changed(
                original_timestamps)
