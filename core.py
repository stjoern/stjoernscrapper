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
import sys

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
        if not string:
            return None
        cena = Core.removeEmptyLines(string)
        if not len(string):
            return None
        m = re.search('(\d+(?:,\d+)?)', cena)
        return m.group(1)
        
    @staticmethod
    def get_decimal_measurement_unit(string):
        if not string:
            return None
        string = Core.trim(string)
        m = re.search('.*(\d+(?:,\d+)?)\s*(.*)$', string)
        decimal = m.group(1)
        measurement_unit = m.group(2)
        if decimal:
            decimal = Core.get_decimal_from_comma_string(decimal)
        return (decimal, measurement_unit)
        
        
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
        
    @staticmethod
    def get_decimal_from_comma_string(string):
        s1 = Core.removeEmptyLines(string)
        s2 = s1.replace(',','.')
        return float('%.2f' % float(s2))
