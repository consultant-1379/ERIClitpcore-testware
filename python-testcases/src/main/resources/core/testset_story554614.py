"""
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     January 2022
@author:    Laurence Canny
@summary:   TORF-554614
            Make a change to the litpd.service to ensure a systemctl
            daemon-reload warning is not produced to verify that the
            update to litp.actions is reloading the service.
"""
import os
from litp_generic_test import GenericTest, attr
from redhat_cmd_utils import RHCmdUtils


class Story554614(GenericTest):
    """
    TORF-554614 Plugin upgrades causing 'systemctl daemon-reload' warning
    """

    def setUp(self):
        """ Runs before every single test """
        super(Story554614, self).setUp()

        self.redhatutils = RHCmdUtils()
        self.ms_node = self.get_management_node_filename()
        self.litpd_service_file = '/usr/local/lib/systemd/system/litpd.service'
        self.plugin_id = 'torf554614'

    def tearDown(self):
        """ Runs after every single test """
        super(Story554614, self).tearDown()
        self._uninstall_rpms()

    @staticmethod
    def get_local_rpm_paths(path, rpm_id):
        """
        Description:
            Method that returns a list of absolute paths to the
            RPMs required to be installed for testing.
        Args:
            path (str): Path dir to check for RPMs.
            rpm_id (str): RPM name to check for in path.
        """
        # Get all RPMs in 'path' that contain 'rpm_id' in their name
        rpm_names = [rpm for rpm in os.listdir(path) if rpm_id in rpm]

        if not rpm_names:
            return None

        # Return a list of absolute paths to the RPMs found in 'rpm_names'
        return [
            os.path.join(rpath, rpm)
            for rpath, rpm in
            zip([os.path.abspath(path)] * len(rpm_names), rpm_names)
            ]

    def _install_rpms(self):
        """
        Description:
            Method that installs plugin and extension on
            the MS if they are not already installed.
        """
        # Check if the plugin is already installed
        _, _, rcode = self.run_command(
            self.ms_node, self.rhc.check_pkg_installed([self.plugin_id]),
            su_root=True)

        # If not, copy plugin and extension onto MS
        if rcode == 1:
            local_rpm_paths = self.get_local_rpm_paths(
                os.path.abspath(
                    os.path.join(os.path.dirname(__file__), 'plugins')
                ),
                self.plugin_id
            )
            self.assertTrue(
                self.copy_and_install_rpms(self.ms_node, local_rpm_paths),
                "There was an error installing the test plugin on the MS.")

    def _uninstall_rpms(self):
        """
        Description:
            Method that uninstalls plugin and extension on
            the MS.
        """
        local_rpm_paths = self.get_local_rpm_paths(
            os.path.join(
                os.path.dirname(repr(__file__).strip("'")), "plugins"
                ),
            self.plugin_id
            )
        if local_rpm_paths:
            installed_rpm_names = []
            for rpm in local_rpm_paths:
                std_out, std_err, rcode = self.run_command_local(
                    self.rhc.get_package_name_from_rpm(rpm))
                self.assertEquals(0, rcode)
                self.assertEquals([], std_err)
                self.assertEquals(1, len(std_out))

                installed_rpm_names.append(std_out[0])

            _, _, rcode = self.run_command(self.ms_node,
                                           self.rhc.get_yum_remove_cmd(
                                               installed_rpm_names),
                                           add_to_cleanup=False,
                                           su_root=True)
            self.assertEquals(0, rcode)

    @attr('all', 'revert', 'story554614', 'story554614_tc01')
    def test_01_p_update_litpd_service_check_for_warning(self):
        """
        @tms_id: torf_554614_tc01
        @tms_requirements_id: TORF-554614
        @tms_title: Update service check for warning
        @tms_description:
            1) When I install the plugin that updates the
               litpd.service, I see no warning from systemctl
        @tms_test_steps:
            @step: Install test plugin RPM on the MS
            @result: Test plugin RPM successfully installed on MS
            @step: Check the litpd.service has been updated
            @result: litpd.service has been updated
            @step: Check the status of litpd.service is not returning
                   a warning
            @result: No warning returned on litpd.service status check
        @tms_test_precondition: ERIClitptorf554614 RPM available
        @tms_execution_type: Automated
        """
        grep_string = "TimeoutSec=6min"
        warning_string = "'Warning: litpd.service changed'"

        self.log('info', '1. Install test plugin RPM on the MS.')
        self._install_rpms()

        self.log('info', '2. Check the litpd.service has been updated')

        stdout, _, _ = self.run_command(
            self.ms_node,
            self.redhatutils.get_grep_file_cmd(self.litpd_service_file,
                                               grep_string),
            default_asserts=True,
            su_root=True
        )
        self.assertNotEqual([], stdout)

        self.log('info', '3. Check the status of litpd.service is '
                         'not returning a warning.')
        status_cmd = self.redhatutils.get_systemctl_status_cmd("litpd.service")

        stdout, stderr, rcode = self.run_command(
            self.ms_node, '{0} | grep {1}'.format(status_cmd, warning_string),
            su_root=True
        )
        self.assertEqual([], stdout)
        self.assertEqual([], stderr)
        self.assertEqual(rcode, 1)
