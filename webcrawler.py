'''
Created on Sep 10, 2017

@author: mmullero
'''
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from stjoernscrapper import logger
from stjoernscrapper.core import Core
from time import sleep
from lxml import html
from stjoernscrapper.mongo_service import db
import re

class WebCrawler(object):
    '''
    classdocs
    '''
    WebDomains = []

    def __init__(self, *args, **kwargs):
        '''
        Constructor
        '''
        self.webDomain = kwargs.get('webDomain', WebCrawler.WebDomains.pop())
        self.checkDriver = kwargs.get('checkDriver', True)
        self.set_web_driver()
        self.dbName = Core.get_db_name(self.webDomain)
        self.iso_time = Core.get_iso_datetime()
        self.ts = Core.get_last_insert_counter(self.dbName)
        
    def set_web_driver(self, driver = 'chrome'):
        try:
            self.driver = webdriver.Chrome()
        except:
            try:
                self.driver = webdriver.Chrome(r"c:\KB\installation_instruction\project\stjoern-scrapper\install\chromedriver.exe")
            except Exception as e:
                logger.error("Chrome driver is not in your path, please download chromedriver.exe!, {}".format(e.message))
                logger.error("stjoern-scrapper will be terminated.")
                exit(-1)
     
    def _check_for_driver(self):
        self.driver.get("http://www.python.org")
        assert "Python" in self.driver.title
        elem = self.driver.find_element_by_name("q")
        elem.clear()
        elem.send_keys("pycon")
        elem.send_keys(Keys.RETURN)
        assert "No results found." not in self.driver.page_source
        self.driver.close()
        
    def _getPager(self):
        '''
        getPager method is dedicated for getting range (start, endPage)
        '''
        elems = self.driver.find_elements_by_xpath("//div[@class='pager']/a[@href]")
        if elems:
            last_href = elems[-1].get_attribute('href')
            print(last_href)
            m = re.search('.*&pg=(?P<maxpage>[0-9]+)$', last_href)
            max_page = int(m.group('maxpage'))
            return max_page
        return None
         
    
    def parse(self):
        if self.checkDriver:
            self._check_for_driver() #TODO: create decorator
            self.set_web_driver()
        self.driver.get(self.webDomain)
        # automodul.cz
        # div id="filter">ul>li>a (osobni, uzitkove, ...)
        #self.driver.find_element(By.CSS_SELECTOR,'p.content:nth-child(1)')
        #filter_tabs = self.driver.find_elements(By.CSS_SELECTOR, '#vyber-ouska li a')
        
        #filter_tabs = self.driver.find_elements_by_xpath("//div[@id='filtr']//li//a[@class='imgr']")
        links = [link.get_attribute('href') for link in self.driver.find_elements_by_xpath("//div[@id='filtr']/ul/li/a")]
        for link in links:
            if 'osobni' in link:
                typ = 'osobni'
            elif 'uzitkove':
                typ = 'uzitkove'
            elif 'nakladni':
                typ = 'nakladni'
            elif 'motocykly':
                typ = 'motocykly'
            elif 'obytne-vozy':
                typ = 'obytne vozy'
            elif 'stavebni-stroje':
                typ = 'stavebni stroje'
            elif 'ostatni':
                typ = 'ostatni'
            else:
                continue
            submitButton = self.driver.find_element_by_xpath('//input[@type="submit"]')
            if submitButton:
                submitButton.click()
                sleep(15)
                
            page_max = self._getPager()
            current_url_without_paging = self.driver.current_url
            for page in range(0,page_max):
                redirect_to_url = "{no_page}&pg={page}".format(no_page=current_url_without_paging, page=page)
                self.driver.get(redirect_to_url)
                db_cars = []
                
                parser = html.fromstring(self.driver.page_source, self.driver.current_url)
                cars = parser.xpath('//div[contains(@name,"auto")]/div[@class="pravaCast"]')
                for car in cars:
                    db_car = {}
                    car_title = car.xpath('.//h2/a')
                    if car_title:
                        db_car['ts'] = self.ts
                        db_car['name'] = Core.normalize2ascii(car_title[0].text)
                        #todo exceptions if nothing found
                    parameters = car.xpath('.//table[@class="parametry"]/tbody')[0]
                    if parameters:
                        cena = parameters.xpath('tr[@class="cena"]/td')[0].text
                        db_car['cena'] = Core.parseNumber(cena)
                        other_parameters = parameters.xpath('tr[not(@class="cena")]')
                        for param in other_parameters:
                            th = param.xpath('th')[0].text
                            td = param.xpath('td')[0].text
                            td = Core.normalize2ascii(td)
                            if th == 'Vyrobeno':
                                value = Core.parseNumber(td)
                                if value:
                                    db_car['vyrobeno'] = value
                            elif th == 'Tachometr':
                                value = Core.parseNumber(td)
                                if value:
                                    db_car['tachometr'] = value
                            elif th == 'Palivo':
                                db_car['palivo'] = td
                            elif th == 'Motorizace':
                                db_car['motorizace'] = td
                            elif th == 'Tvar karoserie':
                                db_car['tvar_karoserie'] = td
                            else:
                                continue
                    if any(db_car):
                        db_cars.append(db_car)
                if any(db_cars):
                    db[self.dbName].insert(db_cars,{'ordered':False})
            
    def close(self):
        logger.info("Successfully finished {}".format(self.webDomain))
        self.driver.close()         
        