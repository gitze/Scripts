#!/bin/bash
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

rm /usr/local/bin/network_status.sh
ln -s   /opt/system/network_status.sh /usr/local/bin/
chown root:root /usr/local/bin/network_status.sh
chmod 755 /usr/local/bin/network_status.sh

rm /etc/systemd/system/network_status.*
systemctl daemon-reload
ln -s /opt/system/network_status.service /etc/systemd/system/
ln -s /opt/system/network_status.timer /etc/systemd/system/


chown root:root /etc/systemd/system/network_status.service
chmod 444 /etc/systemd/system/network_status.service

chown root:root /etc/systemd/system/network_status.timer
chmod 444 /etc/systemd/system/network_status.timer

systemctl enable network_status.timer
systemctl start network_status.timer

systemctl status network_status.timer
