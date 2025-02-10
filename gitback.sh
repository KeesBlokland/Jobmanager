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
gitingest ./Jobmanager -e /static -e /backups -e /logs -e /db -e /*.txt  -e/*.md -e /export -e *.db -e /utils -e "__pycache__" -e "jobmanager.db.backup_*" -e "*.pyc" -e "backup_*" -o /home/Jobmanager/jobmgr-${DATE}.txt
