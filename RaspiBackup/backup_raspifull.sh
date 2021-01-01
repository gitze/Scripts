#!/bin/bash
# backup_raspifull.sh
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

BACKUPDIR=/automnt/backup
BACKUPNAME=gartenrpi

NOW=$(date +"%Y-%m-%d %H:%M:%S")
CONTROLFILE=${BACKUPDIR}/BACKUP_USB
WEEKDAY=`date +%u`
FILESIZE="4000"
FILENAME="${BACKUPDIR}/${BACKUPNAME}_"$FILESIZE"_backup_"$WEEKDAY".img"

echo "################################################################################"
echo "#    RASPI BACKUP"
echo "#    Date:        $NOW"
echo "#    File:        $FILENAME"
echo "################################################################################"
if [ ! -e "$CONTROLFILE" ]; then
    echo "BACKUP Location not found." >&2
    echo "Looking for folowing file: $CONTROLFILE" >&2
    exit 1
else 
    /opt/raspibackup/bkup_rpimage.sh start -c -s $FILESIZE "$FILENAME"
fi 
