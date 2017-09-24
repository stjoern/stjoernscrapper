'''
Created on Sep 10, 2017

@author: mmullero
'''
from logging import handlers
import logging
from multiprocessing import Pool
from optparse import OptionParser

from stjoernscrapper import logger
from stjoernscrapper.automodul import Automodul
from stjoernscrapper.config import Config
from stjoernscrapper.core import Core
from stjoernscrapper.nakup_itesco import NakupITesco
from stjoernscrapper.portal_mpsv import PortalMpsv
from stjoernscrapper.rohlik import Rohlik
from stjoernscrapper.sreality import Sreality
from stjoernscrapper.webcrawler import WebCrawler


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
        logger = logging.getLogger('sjoern-scrapper')
        logger.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
        handler = handlers.RotatingFileHandler(Config.logpath, maxBytes=20000000, backupCount=1)
        handler.setFormatter(formatter)
        handler.setLevel(logging.INFO)
        logger.addHandler(handler)
        logger.info("{} INIT {}".format(27*'#', 27*'#'))
        
    def parse_input():
        parser = OptionParser(usage="usage: %prog [options] filename", version="%prog 1.0")
        parser.add_option("-i", "--input", dest="input_file", type="string", help="Specify the input file with all web domains for scrapping")
        parser.add_option("-v", "--verbose", action="store_true", dest="verbose", default=False, help="Print out in debug mode, default=False")
        
        (options, _) = parser.parse_args()
        if (options.input_file == None):
            logger.error("no input file for switches entered, " + parser.usage)
            exit(0)

        if options.verbose:
            WebCrawler.Debug=True
        
        def init_web_domains():
            try:
                logger.debug("Parse input file with web domains")
                logger.info("Reading all web domain")
                result = None
                with open(options.input_file) as f:
                    line = f.read().splitlines()
                    web = filter(lambda x: x.strip().startswith('#')==False, line)
                    result = {Core.removeEmptyLines(x).split(',')[0]:Core.removeEmptyLines(x).split(',')[1] for x in web}
                if result:
                    logger.info("These websites will be scrapped: ")
                    for key in result.iterkeys():
                        logger.info(" -> {}".format(key)) 
                        
                    logger.info("{}".format('-'*60))
                return result
            except Exception as e:
                logger.error("Error, the file with web domains is not valid. {}".format(e.message))
                logger.error("The program will be terminated.")
                exit(-1)
            
        # fill the list of web domain to the webcrawler
        WebCrawler.WebDomains = init_web_domains()
        
    init_logging()
    parse_input()


def thread_and_parse(metaclass, url):
    web = globals()[metaclass](webDomain=url)#, checkDriver=False)
    result = web.parse()
    return result

def unwrap_metaclasses(args):
    return thread_and_parse(*args)
     
if __name__ == '__main__':
    main()
    webs = [(value.replace('<','').replace('>',''), key) for key,value in WebCrawler.WebDomains.iteritems()]
    
    if Config.threading:
        pool = Pool(len(WebCrawler.WebDomains))
        results = pool.map(unwrap_metaclasses, webs)
    else:
        for metaclass, url in webs:
            web = globals()[metaclass](webDomain=url, checkDriver=False)
            if web:
                result = web.parse()
                print(result) 
    logger.info("Successfully finished.")
    logger.info("{}".format('-'*60))
    
    