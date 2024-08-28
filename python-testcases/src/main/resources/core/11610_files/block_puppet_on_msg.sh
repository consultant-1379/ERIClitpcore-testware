#!/bin/bash

TRIGGER_MSG='Waiting for Puppet phase to complete'
# NODE param empty as it will be updated by actual node name in runtime
NODE=
NODE_IP=`gethostip $NODE | awk '{print $2}'`

unblock_node() {
    echo 'Unblocking node...'
    while /sbin/iptables -D INPUT -s $NODE_IP -j DROP
    do
        echo -n ''
    done 
}

trap "unblock_node; exit " SIGTERM SIGINT

echo "Waiting for trigger message: \"$TRIGGER_MSG\""
tail -f /var/log/messages -n 0 | grep "$TRIGGER_MSG" -m 1

while true;
do
    /sbin/iptables-save | grep "\-A INPUT \-s $NODE_IP\/32 \-j DROP" > /dev/null
    if [ $? -ne 0 ] ; then
	date
	echo "Blocking host $NODE ($NODE_IP)"
        /sbin/iptables -I INPUT -s $NODE_IP -j DROP
    fi 
    sleep 0.2
done
