#/usr/local/bin/bash
#
# Usage: program [config.file] [key] [newvalue]
# Delimiter is ":" or "="
#
#echo Script name: $0
#echo $# arguments

editConfigKey() {
    if [ $# -ne 3 ]; then
        echo "illegal number of parameters"
        echo "$0 $@"
        exit 1
    fi
    configfile=$1
    shift
    key=$1
    shift
    replace=$1
    shift

    [ ! -e "$configfile" ] && touch $configfile
    sed -E -i .bak "s/^($key[[:blank:]]*[=|:][[:blank:]]*).*/\1$replace/" "$configfile"
    [ $(grep -c "^$key[[:blank:]]*[=|:]" "$configfile") -eq 0 ] && echo "$key=$replace" >>"$configfile"
}

editConfigKey "$@"
