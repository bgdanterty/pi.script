#!/bin/bash

echo -e "\nCHECKING SERIAL TOOLS\n"
a="pip
pip2
pip2.7"
b=`ls -a /opt/pbox-devices/venv/bin | grep pip*`;

if [[ $b != $a ]];
then
    a=`virtualenv --version`
    b=1.11.6
    c=15.1.0

    while [[ $a != $b ]] && [[ $a != $c ]]
    do apt-get install python-virtualenv;
    done

    if  [[ $a == $b ]]
    echo "virtualenv versions $a";
    then
	virtualenv /opt/pbox-devices/venv;

    elif [[ $a == $c ]]
    echo "virtualenv versions $a";
    then
	virtualenv --no-setuptools /opt/pbox-devices/venv;
	/opt/pbox-devices/venv/bin/pip install setuptools==41.0.1;
	sudo /opt/pbox-devices/venv/bin/pip install --find-links /home/pi/pip_index --no-index -r /opt/pbox-devices/src/requirements.txt;

#    else
#	apt-get install python-virtualenv --force-reinstall;
    fi

else echo -e "\nSERIAL TOOLS OK\n"
fi