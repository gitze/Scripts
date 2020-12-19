#! /bin/sh
PATH='/usr/local/sbin:/usr/sbin:/usr/bin:/sbin:/bin'

#UPDATE
#UpdateServerURL="http://diskstation/amp_power/"
#UpdateVersionFile="amp_power.version"
#UpdateScriptFile="amp_power"

#Logging
debuglogfile="./powersave_debug"$$.log
#exec > $debuglogfile 2>&1
MasterLogfile="/home/pi/powersave.log"

# set verbose level to info
__VERBOSE=6
# declare -A LOG_LEVELS
# https://en.wikipedia.org/wiki/Syslog#Severity_level
# LOG_LEVELS=([0]="emerg" [1]="alert" [2]="crit" [3]="err" [4]="warning" [5]="notice" [6]="info" [7]="debug")


#GPIO / AMP Management
PORT=23


LogIt () {
  local LEVEL=${1}
  shift
  if [ ${__VERBOSE} -ge ${LEVEL} ]; then
	timestamp=`date "+%Y-%m-%d %H:%M:%S"`
	echo $timestamp":" $@
	echo $timestamp":" $@ >> $MasterLogfile
  fi
}


InitGPIO(){
	LogIt 7 "InitGPIO"
   if ! [ -d /sys/class/gpio/gpio$PORT ]
   then
      echo "$PORT" > /sys/class/gpio/export
      echo "out" > /sys/class/gpio/gpio$PORT/direction
   fi
   echo 1 > /sys/class/gpio/gpio$PORT/value
}



######################################################
###### SelfUpdate
###### Thx to script from:
###### http://stackoverflow.com/questions/8595751/is-this-a-valid-self-update-approach-for-a-bash-script
######################################################
runSelfUpdate() {
  LogIt 5 "Performing self-update..."

  # Download new version
  echo -n "Downloading latest version..."
  if ! wget --quiet --output-document="$0.tmp" $UpdateServerURL/$SELF ; then
    echo "Failed: Error while trying to wget new version!"
    echo "File requested: $UpdateServerURL/$SELF"
    exit 1
  fi
  echo "Done."

  # Copy over modes from old version
  OCTAL_MODE=$(stat -c '%a' $SELF)
  if ! chmod $OCTAL_MODE "$0.tmp" ; then
    echo "Failed: Error while trying to set mode on $0.tmp."
    exit 1
  fi

  # Spawn update script
  cat > /tmp/updateScript.sh << EOF
#!/bin/bash
# Overwrite old file with new
if mv "$0.tmp" "$0"; then
  echo "Done. Update complete."
  rm \$0
else
  echo "Failed!"
fi
EOF

  echo -n "Inserting update process..."
  exec /bin/bash /tmp/updateScript.sh
}


######################################################
###### Main
######################################################
InputParam="$1"

# if [ "$InputParam" == "update" ]
# then
# 	LogIt 5 "Update:  $UpdateServerURL$UpdateScriptFile > /mnt/mmcblk0p2/tce/amp_power/amp_power"
# 	echo "Starting Update"
# 	wget -q -O - $UpdateServerURL$UpdateScriptFile > /mnt/mmcblk0p2/tce/amp_power/amp_power
# 	exit
# fi

InitGPIO

case "$InputParam" in
    "OFF")	echo 1 > /sys/class/gpio/gpio$PORT/value; LogIt 6 "Power Off";;
    "ON")	echo 0 > /sys/class/gpio/gpio$PORT/value; LogIt 6 "Power On";;
esac
