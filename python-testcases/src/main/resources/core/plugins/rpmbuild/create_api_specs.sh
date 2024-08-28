#!/bin/bash

base=~/rpmbuild

for FILE in ${base}/SOURCES/*.rpm;
do

    filename=$(basename $FILE)

    ERIClitpstoryname=$(echo $filename | awk -F '_' '{print $1}')

    storyname=${ERIClitpstoryname:8:-3}

    ## When the rpms unpack the filenames are usually called either a variation of e.g. story4429_extension.py or story6864extension.py. In the case of the latter, use commented out variable
    storypluginname=${storyname}_extension
    #storypluginname=${storyname}extension

    snapshottimestamp=$(echo $filename | awk -F '.' '{print $3}')

    file_timestamp=${snapshottimestamp:10}

    rpmbuild -bb --target noarch --define "_story_name ${storyname}" --define "_story_plugin_name ${storypluginname}" --define "_time_stamp ${file_timestamp}" ${base}/SPECS/genericapi.spec
done
