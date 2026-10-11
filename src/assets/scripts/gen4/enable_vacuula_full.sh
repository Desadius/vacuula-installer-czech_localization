#!/bin/sh
export PATH=/sbin:/bin:/usr/sbin:/usr/bin

# Fix file permissions
chmod a+r /usr/sbin/enable_vacuula.sh
chmod a+r /lib/systemd/system/usb-gadgets.service
chmod a+r /etc/systemd/resolved.conf
chmod a+r /etc/systemd/network/wireless.network
chmod a+r /home/root/tron/config/vendors.ini
chmod a+r /home/root/tron/config/ssl/vacuula.crt
chmod a+r /etc/wpa_supplicant/wpa_supplicant-wlan0.conf
chmod a+r /etc/hosts

# Disable "orbital." prefix in server address
if [ ! -f /home/root/tron/tron/configutils.py.bak ]
then
  sed -i.bak 's/"orbital\.%s"/"%s"/g' /home/root/tron/tron/configutils.py
fi

# Get new DHCP lease
systemctl restart systemd-networkd

# Enable mDNS resolution
ln -sf ../run/systemd/resolve/stub-resolv.conf /etc/resolv.conf
