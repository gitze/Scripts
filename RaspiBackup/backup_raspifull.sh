#!/bin/bash
# backup_raspifull.sh
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

NOW=$(date +"%Y-%m-%d %H:%M:%S")
CONTROLFILE=/automnt/backup/BACKUP_USB
WEEKDAY=`date +%u`
FILESIZE="4000"
FILENAME="/automnt/backup/gartenrpi_"$FILESIZE"_backup_"$WEEKDAY".img"
echo "################################################################################"
echo "#    RASPI BACKUP"
echo "#    Date:        $NOW"
echo "#    File:        $FILENAME"
echo "################################################################################"
if [ ! -e "$CONTROLFILE" ]; then
    echo "BACKUP USB Stick not found." >&2
    echo "Looking for folowing file: $CONTROLFILE" >&2
    exit 1
else 
    /opt/solar/bkup_rpimage.sh start -c -s $FILESIZE "$FILENAME"
fi 
