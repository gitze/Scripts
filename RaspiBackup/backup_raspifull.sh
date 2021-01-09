#!/bin/bash
# backup_raspifull.sh
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

BACKUPDIR=/automnt/diskstation
BACKUPNAME=gartenrpi
FILESIZE="4000"
CONTROLFILE=${BACKUPDIR}/BACKUP_DRIVE

NOW=$(date +"%Y-%m-%d %H:%M:%S")
WEEKDAY=`date +%u`
FILENAME="${BACKUPDIR}/${BACKUPNAME}_"$FILESIZE"_backup_"$WEEKDAY".img"

echo "################################################################################"
echo "#    RASPI BACKUP"
echo "#    Date:        $NOW"
echo "#    File:        $FILENAME"
echo "################################################################################"
if [ ! -e "$CONTROLFILE" ]; then
    echo "BACKUP Location not found." >&2
    echo "Looking for following control file: $CONTROLFILE" >&2
    exit 1
else 
    /opt/raspibackup/bkup_rpimage.sh start -c -s $FILESIZE "$FILENAME"
fi 
