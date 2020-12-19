#!/bin/bash
# backup_raspifull.sh

CONTROLFILE=/automnt/backup/BACKUP_USB
if [ ! -e "$CONTROLFILE" ]; then
    echo "BACKUP USB Stick not found." >&2
    echo "Looking for folowing file: $CONTROLFILE" >&2
    exit 1
else 
    ./bkup_rpimage.sh start -c -s 8000 /automnt/backup/gartenrpi_8G_backup.img
fi 