#!/bin/bash
#set -x

base=~/rpmbuild

for FILE in ${base}/SOURCES/*.rpm;
do

    filename=$(basename $FILE)

    ERIClitpstoryname=$(echo $filename | awk -F '_' '{print $1}')

    ## A number of rpms require storyname to be hardcoded ###
    #########################################################
    ## ERIClitptorf<number> ##
    ## storyname=torf_187127
    ## storyname=torf176181
    ## ERIClitpstory9903_fail_restore ##
    ## storyname=${ERIClitpstoryname:8}_fail_restore_snapshot
    ## ERIClitpstory1838_second ##
    ## storyname=${ERIClitpstoryname:8}_second
    ## ERIClitpmcoagenttest rpm
    ## storypluginname=helloworld

    storyname=${ERIClitpstoryname:8}

    storypluginname=${storyname}_plugin

    snapshottimestamp=$(echo $filename | awk -F '.' '{print $3}')

    file_timestamp=${snapshottimestamp:10}

    rpmbuild -bb --target noarch --define "_story_name ${storyname}" --define "_story_plugin_name ${storypluginname}" --define "_time_stamp ${file_timestamp}" ${base}/SPECS/genericstory.spec

    # For ERIClitpmcoagenttest replace genericstory.spec with customised version for mcoagent specs
    # rpmbuild -bb --target noarch --define "_story_name ${storyname}" --define "_story_plugin_name ${storypluginname}" --define "_time_stamp ${file_timestamp}" ${base}/SPECS/mcoagenttest.spec

    ## If no TIMESTAMP in rpm name
    # rpmbuild -bb --target noarch --define "_story_name ${storyname}" --define "_story_plugin_name ${storypluginname}" ${base}/SPECS/genericstory.spec
done
