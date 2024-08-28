%define build_timestamp %(date +"%Y%m%d%H%M")

Name:           ERIClitp%{_story_name}_CXP1234567
Version:        1.0.1
Release:        SNAPSHOT%{build_timestamp}
Summary:        LITP %{name} test package

License:        2012 Ericsson AB All rights reserved
URL:            www.ericsson.com
Source0:        %{name}-%{version}-SNAPSHOT%{_time_stamp}.noarch.rpm

%define _unpackaged_files_terminate_build 0
%define _litp_dir opt/ericsson/nms/litp
%define _litp_mcollective_agents_dir %{_litp_dir}/etc/puppet/modules/mcollective_agents/files

%description
%{summary}

%prep
rm -rf $RPM_SOURCE_DIR/opt
cd $RPM_SOURCE_DIR
rpm2cpio %{SOURCE0} | cpio -idmv


%install
mkdir -p %{buildroot}/%{_litp_dir}
mkdir -p %{buildroot}/%{_litp_mcollective_agents_dir}

cp %{_sourcedir}/%{_litp_mcollective_agents_dir}/helloworld.ddl %{buildroot}/%{_litp_mcollective_agents_dir}
cp %{_sourcedir}/%{_litp_mcollective_agents_dir}/helloworld.rb %{buildroot}/%{_litp_mcollective_agents_dir}
cp %{_sourcedir}/%{_litp_mcollective_agents_dir}/helloworld.py %{buildroot}/%{_litp_mcollective_agents_dir}

exit 0

#%clean
#rm -rf $RPM_BUILD_ROOT


%files
#%defattr(755,root,root,-)
#/%{_litp_mcollective_agents_dir}/%{_story_plugin_name}.ddl
#/%{_litp_mcollective_agents_dir}/%{_story_plugin_name}.py
#/%{_litp_mcollective_agents_dir}/%{_story_plugin_name}.rb
