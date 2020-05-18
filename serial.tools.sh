#!/bin/bash

a="pip
pip2
pip2.7"
b=`ls -a /opt/pbox-devices/venv/bin | grep pip*`;
if [[ $b != $a ]];
then
    a=`virtualenv --version`
    b=1.11.6
    c=15.1.6
    if  [[ $a == $b ]]
    then
	virtualenv /opt/pbox-devices/venv
    elif [[ $a == $c ]]
    then
	virtualenv --no-setuptools /opt/pbox-devices/venv;
	/opt/pbox-devices/venv/bin/pip install setuptools==41.0.1;
	sudo /opt/pbox-devices/venv/bin/pip install --find-links /home/pi/pip_index --no-index -r /opt/pbox-devices/src/requirements.txt;
    else
	apt-get install python-virtualenv
else echo "не делаю"
fi