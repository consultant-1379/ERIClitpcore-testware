%define build_timestamp %(date +"%Y%m%d")

Name:           ERIClitp%{_story_name}api_CXP1234567
Version:        1.0.2
Release:        SNAPSHOT%{build_timestamp}
Summary:        LITP %{name} test package

License:        2012 Ericsson AB All rights reserved
URL:            www.ericsson.com
Source0:        %{name}-%{version}-SNAPSHOT%{_time_stamp}.noarch%{_tc_name}.rpm
#Source0:        %{name}-%{version}-SNAPSHOT%{_time_stamp}.noarch.rpm

%define _unpackaged_files_terminate_build 0
%define _litp_dir opt/ericsson/nms/litp
%define _litp_etc_plugins_dir %{_litp_dir}/etc/extensions
#%define _litp_migrations_plugins_dir %{_litp_dir}/etc/migrations/%{_story_name}extension
%define _litp_migrations_plugins_dir %{_litp_dir}/etc/migrations
#%define _litp_rename_dir %{_litp_migrations_plugins_dir}/rename_property
#%define _litp_story_dir %{_litp_migrations_plugins_dir}/%{_story_plugin_name}
%define _litp_story_dir %{_litp_migrations_plugins_dir}/story1126_2509_5568extension
%define _litp_lib_plugin_dir %{_litp_dir}/lib/%{_story_plugin_name}

%description
%{summary}

%prep
rm -rf $RPM_SOURCE_DIR/opt
cd $RPM_SOURCE_DIR
rpm2cpio %{SOURCE0} | cpio -idmv


%install
mkdir -p %{buildroot}/%{_litp_etc_plugins_dir}
#mkdir -p %{buildroot}/%{_litp_migrations_plugins_dir}
mkdir -p %{buildroot}/%{_litp_rename_dir}
mkdir -p %{buildroot}/%{_litp_lib_plugin_dir}
mkdir -p %{buildroot}/%{_litp_story_dir}
cp %{_sourcedir}/%{_litp_etc_plugins_dir}/%{_story_plugin_name}.conf %{buildroot}/%{_litp_etc_plugins_dir}
#cp %{_sourcedir}/%{_litp_rename_dir}/001_rename_property_name.py %{buildroot}/%{_litp_rename_dir}
#cp %{_sourcedir}/%{_litp_rename_dir}/__init__.py %{buildroot}/%{_litp_rename_dir}
cp %{_sourcedir}/%{_litp_story_dir}/001_migration_operations_successful.py %{buildroot}/%{_litp_story_dir}
cp %{_sourcedir}/%{_litp_story_dir}/__init__.py %{buildroot}/%{_litp_story_dir}
#cp %{_sourcedir}/%{_litp_migrations_plugins_dir}/001_migration_operations_successful.py %{buildroot}/%{_litp_migrations_plugins_dir}
cp %{_sourcedir}/%{_litp_lib_plugin_dir}/__init__.py %{buildroot}/%{_litp_lib_plugin_dir}
cp %{_sourcedir}/%{_litp_lib_plugin_dir}/%{_story_name}extension.py %{buildroot}/%{_litp_lib_plugin_dir}


%clean
rm -rf $RPM_BUILD_ROOT


%files
%defattr(755,root,root,-)
/%{_litp_etc_plugins_dir}/%{_story_plugin_name}.conf
#/%{_litp_rename_dir}/001_rename_property_name.py
#/%{_litp_rename_dir}/__init__.py
/%{_litp_story_dir}/001_migration_operations_successful.py
/%{_litp_story_dir}/__init__.py
#/%{_litp_etc_plugins_dir}/%{_story_plugin_name}.conf
#/%{_litp_migrations_plugins_dir}/001_migration_operations_successful.py
#/%{_litp_migrations_plugins_dir}/001%{_tc_name}.py
#/%{_litp_migrations_plugins_dir}/__init__.py
%dir /%{_litp_lib_plugin_dir}
/%{_litp_lib_plugin_dir}/__init__.py
/%{_litp_lib_plugin_dir}/%{_story_name}extension.py
#/%{_litp_lib_plugin_dir}/story1126_2075_5568extension.py
