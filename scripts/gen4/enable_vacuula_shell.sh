#!/bin/sh
export PATH=/sbin:/bin:/usr/sbin:/usr/bin

# Enable ACM USB serial console
if ! grep -q 'vacuula' /usr/sbin/usb_gadgets.sh
then
  sed -i.bak 's/cd ..\/../# Enable vacuula shell\n    mkdir functions\/acm.vacuula\n    ln -s functions\/acm.vacuula configs\/c.1\n\n    &/g' /usr/sbin/usb_gadgets.sh
fi

# Enable autologin on USB serial console
if [ ! -f /etc/systemd/system/serial-getty\@ttyGS0.service.d/override.conf ]
then
  mkdir -p /etc/systemd/system/serial-getty\@ttyGS0.service.d
  cat > /etc/systemd/system/serial-getty\@ttyGS0.service.d/override.conf <<EOF
[Service]
ExecStart=
ExecStart=-/sbin/agetty -a root -w -8 -L %I 115200 $TERM
EOF
fi

# Enable getty for USB serial console
systemctl enable serial-getty\@ttyGS0.service
