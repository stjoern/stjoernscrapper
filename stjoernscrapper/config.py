'''
Created on Sep 13, 2017

@author: mmullero
'''
import os


# configuration
class Config(object):
    MONGODB_URI = "mongodb://localhost:27017/"
    MONGODB_DB = "stjoern-scrapper"
    basedir = os.path.abspath(os.path.dirname(__file__))
    logpath = os.path.join(basedir, 'stjoern-scrapper.log')
    chromedriver_log = os.path.join(basedir, 'chromedriver.log')
    threading = True
    chromedriver_path = r"c:\KB\installation_instruction\project\stjoern-scrapper\install\chromedriver.exe"
    
    @staticmethod
    def getLogPath(name):
        return os.path.join(Config.basedir, '{}.log'.format(name))