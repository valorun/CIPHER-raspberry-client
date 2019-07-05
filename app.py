#!/usr/bin/python3
# coding: utf-8

from cipher_raspi_client import create_client, setup_logger 
import logging

DEBUG = True

if __name__ == '__main__':
    setup_logger(debug=DEBUG)
    client = create_client(debug=DEBUG)
    logging.info("Application started")
    client.loop_forever()
