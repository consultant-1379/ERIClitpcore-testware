#!/bin/bash

base=~/rpmbuild

for FILE in ${base}/SOURCES/*.rpm;
do

    filename=$(basename $FILE)

    ERIClitpstoryname=$(echo $filename | awk -F 'api' '{print $1}')

    storyname=${ERIClitpstoryname:8}

    storypluginname=${storyname}_extension

    snapshottimestamp=$(echo $filename | awk -F '.' '{print $3}')

    file_timestamp=${snapshottimestamp:10}

    tc=$(echo $filename | awk -F 'noarch' '{print $2}')
    tc_name=$(echo $tc | awk -F '.rpm' '{print $1}')

    rpmbuild -bb --target noarch --define "_story_name ${storyname}" --define "_story_plugin_name ${storypluginname}" --define "_time_stamp ${file_timestamp}" --define "_tc_name ${tc_name}" ${base}/SPECS/generic_story1126_2509_5568api.spec
done
