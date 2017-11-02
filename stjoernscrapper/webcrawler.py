'''
Created on Sep 10, 2017

@author: mmullero
'''
from logging import handlers
import logging

from selenium import webdriver
from selenium.webdriver.common.keys import Keys

from stjoernscrapper import mongo_service
from stjoernscrapper.config import Config
from stjoernscrapper.core import Core, autolog


class WebCrawler(object):
    '''
    classdocs
    '''
    WebDomains = {}
    def __init__(self, *args, **kwargs):
        '''
        Constructor
        '''
        self.webDomain = kwargs.get('webDomain')
        self.checkDriver = kwargs.get('checkDriver', False)
        self.debug = kwargs.get('debug',False)
        self.dbName = Core.get_db_name(self.webDomain)
        self.init_logging()
        self.set_web_driver()
        self.iso_time = Core.get_iso_datetime()
        mongo_service.init()
        self.db = mongo_service.db
        self.client = mongo_service.Client
        self.ts = Core.get_last_insert_counter(self.db, self.dbName)
        
    def init_logging(self):
        self.logger = logging.getLogger(self.dbName)
        if self.debug:
            self.logger.setLevel(logging.DEBUG)
        else:
            self.logger.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
        handler = handlers.RotatingFileHandler(Config.getLogPath(self.dbName), maxBytes=20000000, backupCount=1)
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.info("{} INIT {}".format(27*'#', 27*'#'))
     
    def set_web_driver(self, driver = 'chrome'):
        autolog(self.logger)
        '''
        chrome, firefox, IE
        @param driver:
        @type driver:
        '''
        capabilities = {
                'browserName': 'chrome',
                'chromeOptions': {
                    'useAutomationExtension': False,
                    'forceDevToolsScreenshot': True,
                    #'args': ['--start-maximized', '--disable-infobars']
                }
        }
        service_args = ['--start-maximized', '--disable-infobars']
        if self.debug:
            service_args.extend(["--verbose","--log-path={}".format(Config.chromedriver_log)])
            #capabilities.get('chromeOptions',{}).get('args',[]).append('--verbose').append('--log-path={}'.format(Config.chromedriver_log))
        try:
            self.driver = webdriver.Chrome(desired_capabilities=capabilities, service_args=service_args)
        except:
            try:
                self.driver = webdriver.Chrome(Config.chromedriver_path, desired_capabilities=capabilities, service_args=service_args)
            except Exception as e:
                self.logger.error("Chrome driver is not in your path, please download chromedriver.exe!, {}".format(e))
                self.logger.error("stjoern-scrapper will be terminated.")
                exit(-1)

    def _check_for_driver(self):
        '''
        check if driver for scrapping is installed
        '''
        autolog(self.logger)
        self.driver.get("http://www.python.org")
        assert "Python" in self.driver.title
        elem = self.driver.find_element_by_name("q")
        elem.clear()
        elem.send_keys("pycon")
        elem.send_keys(Keys.RETURN)
        assert "No results found." not in self.driver.page_source
        self.driver.close()
    
    def parse(self):
        '''
        parse web elements
        '''
        autolog(self.logger)
        if self.checkDriver:
            self._check_for_driver()
            self.set_web_driver()
        self.driver.get(self.webDomain)
      
    def close(self):
        '''
        close session
        '''
        autolog(self.logger)
        self.logger.info("Scrapping finished for {}".format(self.webDomain))
        if self.driver: 
            self.driver.close() 
        if self.client:
            self.client.close()        
        