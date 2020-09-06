import logging

def int2loglevel(i):
    if i == 0:
        return logging.CRITICAL
    elif i == 1:
        return logging.INFO
    elif i == 2:
        return logging.DEBUG
