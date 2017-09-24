'''
Created on Sep 13, 2017

@author: mmullero
'''

import pymongo

from stjoernscrapper.config import Config


Client = None
db = None

def init():
    global db
    global Client
    Client = pymongo.MongoClient(Config.MONGODB_URI)
    db = Client[Config.MONGODB_DB]