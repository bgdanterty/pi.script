#!/bin/bash

#LOGS
    echo -e '\nCHEKING LOGS\n';
if
    cat /var/log/syslog | grep 'Under-voltage detected'; 
    cat /var/log/syslog | grep 'EXT4-fs error'; 
    cat /var/log/syslog | grep 'JBD2: Spotted dirty metadata buffer'; 
    cat /var/log/syslog | grep 'usbfs: interface 1 claimed by usbfs while 'python' sets config #1';
then
	echo -e '\nall clear\n';
else
	echo -e '\nUnder-voltage detected — не хватает питания, нужно менять БП \nEXT4-fs error — ошибка файловой системы, перезапись на НОВУЮ карту памяти \nJBD2: Spotted dirty metadata buffer — ошибка файловой системы, перезапись на НОВУЮ карту памяти \nusbfs: interface 1 claimed by usbfs while 'python' sets config #1 — если есть жалобы на отпадание ФР, то замена USB кабеля или работа напрямую';
fi

#STATUS
    echo -e '\nCHEKING STATUS\n';
    sudo supervisorctl status;
if
    sudo supervisorctl status | grep pbox-devices |  grep -v RUNNING;
then
	while sudo supervisorctl status | grep pbox-devices | grep -v RUNNING;
		do
		echo -e '\nneed action\n';
		#sudo opkg install pbox-devices --force-reinstall --force-remove;
		opkg -f /etc/opkg.conf install pbox-devices --force-remove --force-reinstall;
		sleep 10
	done
	sudo supervisorctl status;
else
source referrers.sh;
source serial.tools.sh;
	echo -e '\nAll OK\n'
fi
