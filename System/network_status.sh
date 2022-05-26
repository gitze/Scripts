#!/bin/bash
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

# global variables
interface="wlan1"
gateway=$(ip route get 8.8.8.0/24 | awk ' /'$interface'/ { print $3 }')

# Ping gateway for network status test
if [ "$gateway" != "" ] 
then
  # Ping gateway for network status test
  ping -c4 $gateway > /dev/null
fi

# if gateway is not reachable, restart the network interface 
if [ $? != 0 ] || [ -z "$gateway" ] 
then
  echo "gateway is not reachable, restart the network interface"
  ip link set $interface down
  sleep 3
  ip link set $interface up
fi

# 
interface="tun0"
gateway=$(ip route get 192.168.0.0/24 | awk ' /'$interface'/  { print $3 }')

if [ "$gateway" != "" ] 
then
  # Ping gateway for network status test
  ping -c4 $gateway > /dev/null
fi

# if gateway is not reachable, restart the vpn service
if [ $? != 0 ] || [ -z "$gateway" ] 
then
  echo "gateway is not reachable, restart the vpn service"
  systemctl stop openvpn
  sleep 3
  systemctl start openvpn
  sleep 1
  systemctl status openvpn
fi

