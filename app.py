#!/usr/bin/python
# coding: utf-8

from raspi_client import create_client, setup_logger 

if __name__ == '__main__':
    setup_logger()
    client = create_client()
    client.loop_forever()
