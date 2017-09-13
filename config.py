'''
Created on Sep 13, 2017

@author: mmullero
'''
import os
basedir = os.path.abspath(os.path.dirname(__file__))
logpath = os.path.join(basedir, 'stjoern-scrapper.log')

# configuration
class Config(object):
    MONGODB_URI = "mongodb://localhost:27017/"
    MONGODB_DB = "stjoern-scrapper"

        