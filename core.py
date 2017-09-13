'''
Created on Sep 11, 2017

@author: mmullero
'''
import re
import unicodedata
from urlparse import urlparse
import tldextract
from time import time
from datetime import datetime
from mongo_service import db

class Core(object):
    '''
    classdocs
    '''


    def __init__(self, params):
        '''
        Constructor
        '''
    
    @staticmethod
    def removeEmptyLines(string):
        filtered = filter(lambda x: not re.match(r'^\s*$', x), string)
        return filtered
    
    @staticmethod
    def trim(string):
        return string.strip(' \t\n\r')
    
    @staticmethod
    def normalize2ascii(string):
        normal = unicodedata.normalize('NFKD', unicode(string)).encode('ASCII', 'ignore')
        return Core.trim(normal)
    
    @staticmethod
    def parseNumber(string):
        if not string or not len(string):
            return None
        cena = Core.normalize2ascii(string)
        cena = Core.removeEmptyLines(cena)
        m = re.search('(\d+)', cena)
        return m.group(1)
        
    @staticmethod
    def get_db_name(url):
        extracted = tldextract.extract(url)
        return extracted.domain
    
    @staticmethod
    def get_iso_datetime(timestamp=None):
        if not timestamp: timestamp = time()
        isodate = datetime.fromtimestamp(timestamp, None)
        return isodate
        
    @staticmethod
    def exists_collection(collection):
        if db[collection].count() > 0:
            return True
        else:
            return False
        
    @staticmethod
    def get_last_insert_counter(collection):
        if Core.exists_collection(collection):  
            ts = db[collection].find_one({'$query': {'ts':{'$exists': True}}, '$orderby': {'ts': -1}}, {'ts':1,'_id':0}).get('ts',0) or 0
            return ts+1
        else:
            return 0
        
#p = '(?:http.*://)?(?P<host>[^:/ ]+).?(?P<port>[0-9]*).*'
#m = re.search(p,'http://www.abc.com:123/test')
#m.group('host') # 'www.abc.com'
#m.group('port') # '123'