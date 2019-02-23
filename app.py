#!/usr/bin/python3
# coding: utf-8

from raspi_client import create_client, setup_logger 
import logging

if __name__ == '__main__':
    setup_logger()
    client = create_client()
    client.loop_forever()
