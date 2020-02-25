#!/usr/bin/python3
# coding: utf-8

from cipher_raspi_client import create_client, setup_logger
from cipher_raspi_client.config import client_config
import logging

DEBUG = client_config.DEBUG

if __name__ == '__main__':
    setup_logger(debug=DEBUG)
    client = create_client(debug=DEBUG)
    logging.info("Application started")
    client.loop_forever()
