#!/bin/sh
# root_gitbackup.sh v3
# Location: /root/root_gitbackup.sh

HOUR=`date +%-H`
HOUR=$((HOUR + 1))
if [ $HOUR -eq 24 ]; then
    HOUR=00
fi
DATE=$(date +"%m%d-")${HOUR}$(date +%M)
gitingest  /home/Jobmanager -e /static -e /backups -e /instance -e *.db  -o /home/jobmanager-${DATE}.txt
