sudo umount /mnt/SAMBA
sudo umount /mnt

mkdir /mnt/SAMBA
sudo mount -t cifs -o user=admin,password=daniela,rw,file_mode=0777,dir_mode=0777 //diskstation/backup /mnt/SAMBA
sudo tar -czvf /mnt/SAMBA/garten.opt.tar.gz --exclude=/opt/vc /opt/
sudo tar -czvf /mnt/SAMBA/garten.etc.tar.gz /etc/
sudo tar -czvf /mnt/SAMBA/garten.var.tar.gz /var/spool/cron/ 
sudo tar -czvf /mnt/SAMBA/garten.home.tar.gz --exclude=.cache --exclude=.local --exclude=*.gz /home
sudo tar -czvf /mnt/SAMBA/garten.root.tar.gz /root

