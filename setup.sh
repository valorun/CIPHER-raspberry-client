#!/bin/bash

install_program(){
    while true; do
        read -p "Do you wish to install this program ? " yn
        case $yn in
            [Yy]* ) sudo apt-get install "$1"; break;;
            [Nn]* ) exit;;
            * ) echo "Please answer yes or no.";;
        esac
    done
}

### requirements ###
if type "python3" &>/dev/null; then
    echo "Python found"
else
    echo "Python3 not found"
    install_program "python3"
fi

if type "pip3" &>/dev/null; then
    echo "Pip found"
else
    echo "Pip not found"
    install_program "python3-pip"
fi


APP_PATH=$(cd $(dirname "$0") && pwd)

echo "Application path: $APP_PATH"

if [ -e $APP_PATH/requirements.txt ]
then
    echo "Installing python dependencies ..."
    pip3 install -r $APP_PATH/requirements.txt
else
    echo "No requirements file found."
fi
### configure client ###
CONFIG_FILE=$APP_PATH/cipher_raspi_client/config.ini

read -p "Raspberry id [UNKNOWN]: " id
read -p "MQTT server address [localhost]: " addr
read -p "MQTT server port [1883]: " port
id=${id:-UNKNOWN}
addr=${addr:-localhost}
port=${port:-1883}

echo -e "[GENERAL]" > $CONFIG_FILE
echo -e "RASPBERRY_ID=$id" >> $CONFIG_FILE
echo -e "\n[MQTT_BROKER]" >> $CONFIG_FILE
echo -e "URL=$addr" >> $CONFIG_FILE
echo -e "PORT=$port" >> $CONFIG_FILE

### add to startup ###
if [ -e /etc/rc.local ]
then
    if grep -q "nohup sudo $APP_PATH/app.py &" /etc/rc.local
    then
        echo "Program already added on startup."
    else
        while true; do
            read -p "Do you wish to add this program on startup ? " yn
            case $yn in
                [Yy]* ) sed -i -e "\$i \\nohup sudo $APP_PATH/app.py &\\n" /etc/rc.local; break;;
                [Nn]* ) exit;;
                * ) echo "Please answer yes or no.";;
            esac
        done
    fi
else
    echo "No rc.local file not found, can't add program on startup."
fi
