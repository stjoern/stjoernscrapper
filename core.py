'''
Created on Sep 11, 2017

@author: mmullero
'''
import re
import unicodedata
from urlparse import urlparse

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
        normal = unicodedata.normalize('NFKD', string).encode('ASCII', 'ignore')
        return Core.trim(normal)
    
    @staticmethod
    def parseNumber(string):
        cena = Core.removeEmptyLines(string)
        m = re.search('(\d+)', cena)
        return m.group(1) 
        #m = re.search('\((\d+)\)', zznew)
        #print m.group(1)
        
    @staticmethod
    def get_db_name(url):
        parsed_uri = urlparse(url)
        domain = '{uri.netloc}'.format(uri=parsed_uri)
        print domain