#!/bin/sh
# root_gitbackup.sh v3
# Location: /root/root_gitbackup.sh
cd /home/Jobmanager
# rm job*.txt
cd /home/
HOUR=`date +%-H`
HOUR=$((HOUR + 1))
if [ $HOUR -eq 24 ]; then
    HOUR=00
fi
DATE=$(date +"%m%d-")${HOUR}$(date +%M)
gitingest ./Jobmanager -e /static -e /backups -e /db -e /README.txt -e /export -e *.db -e /utils -o /home/Jobmanager/jobmgr-${DATE}.txt
