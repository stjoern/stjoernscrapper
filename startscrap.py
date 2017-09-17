'''
Created on Sep 10, 2017

@author: mmullero
'''
from optparse import OptionParser
from stjoernscrapper.webcrawler import WebCrawler
from stjoernscrapper.nakup_itesco import NakupITesco
from stjoernscrapper import logger
import logging
import sys
from stjoernscrapper.config import Config
from stjoernscrapper.core import Core

def main():
    
    ## stdout filter for logger
    class InfoFilter(logging.Filter):
        def filter(self, rec):
            return rec.levelno in (logging.DEBUG, logging.INFO)
    
    ## stderr filter for logger
    class ErrorFilter(logging.Filter):
        def filter(self, rec):
            return rec.levelno in (logging.ERROR, logging.CRITICAL)


    def init_logging():
        
        logger.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
        h1 = logging.StreamHandler(sys.stdout)
        h1.setLevel(logging.INFO)
        h1.setFormatter(formatter)
        h2 = logging.FileHandler(Config.logpath)
        h2.setFormatter(formatter)
        h2.setLevel(logging.INFO)
       
        logger.addHandler(h1)
        logger.addHandler(h2)
        
    def parse_input():
        parser = OptionParser(usage="usage: %prog [options] filename", version="%prog 1.0")
        parser.add_option("-i", "--input", dest="input_file", type="string", help="Specify the input file with all web domains for scrapping")
        parser.add_option("-v", "--verbose", action="store_true", dest="verbose", default=False, help="Print out in debug mode, default=False")
        
        (options, args) = parser.parse_args()
        if (options.input_file == None):
            logger.error("no input file for switches entered, " + parser.usage)
            exit(0)

        if options.verbose:
            logger.setLevel(logging.DEBUG)
        
        def init_web_domains():
            try:
                logger.debug("Parse input file with web domains")
                with open(options.input_file) as f:
                    line = f.read().splitlines()
                    web = filter(lambda x: x.strip().startswith('#')==False, line)
                    res = {Core.removeEmptyLines(x).split(',')[0]:Core.removeEmptyLines(x).split(',')[1] for x in web} 
                    return res
            except Exception as e:
                logger.error("Error, the file with web domains is not valid. {}".format(e.message))
                exit(-1)
            
        # fill the list of web domain to the webcrawler
        WebCrawler.WebDomains = init_web_domains()
        
    init_logging()
    parse_input()
    
    def Start():
        for key, value in WebCrawler.WebDomains.iteritems():
            print("crawling domain: {}".format(key))
            value = value.replace('<','').replace('>','')
            web = globals()[value](webDomain=key, checkDriver=False)
            if web:
                web.parse()
            
    Start()

if __name__ == '__main__':
    main()