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
CONFIG_FILE=$APP_PATH/config.py

config_set_var() {
    sed -i "s/^\($1\s*=\s*\).*\$/\1$2/" $CONFIG_FILE
}

enable_mode(){
    while true; do
        read -p "Do you wish to enable $1 ? " yn
        case $yn in
            [Yy]* ) config_set_var $1 "True"; break;;
            [Nn]* ) config_set_var $1 "False"; break;;
            * ) echo "Please answer yes or no.";;
        esac
    done
}
read -p "Raspberry id: " id
read -p "Server address: " addr
read -p "Server port: " port
config_set_var "RASPBERRY_ID" "\"$id\""
config_set_var "SERVER_ADDRESS" "\"$(echo $addr | sed -r 's/\./\\./g' | sed -r 's,/,\\/,g')\""
config_set_var "SERVER_PORT" $port
enable_mode "RELAY_MODE"
enable_mode "MOTION_MODE"
enable_mode "SERVO_MODE"

### add to startup ###
if [ -e /etc/rc.local ]
then
    if grep -q "nohup $APP_PATH/app.py &" /etc/rc.local
    then
        echo "Program already added on startup."
    else
        while true; do
            read -p "Do you wish to add this program on startup ? " yn
            case $yn in
                [Yy]* ) sed -i -e "\$i \\nohup $APP_PATH/app.py &\\n" /etc/rc.local; break;;
                [Nn]* ) exit;;
                * ) echo "Please answer yes or no.";;
            esac
        done
    fi
else
    echo "No rc.local file found, can't add program on startup."
fi