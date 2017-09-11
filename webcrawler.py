'''
Created on Sep 10, 2017

@author: mmullero
help: https://www.scrapehero.com/tutorial-web-scraping-hotel-prices-using-selenium-and-python/
'''
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from stjoernscrapper import logger
from stjoernscrapper.core import Core
from time import sleep
from lxml import html

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
            self.driver.get(link)
            typ = link.text
            typ = Core.normalize2ascii(typ)
            submitButton = self.driver.find_element_by_xpath('//input[@type="submit"]')
            if submitButton:
                submitButton.click()
                sleep(15)
                
            parser = html.fromstring(self.driver.page_source, self.driver.current_url)
            cars = parser.xpath('//div[contains(@name,"auto")]/div[@class="pravaCast"]')
            for car in cars:
                car_title = car.xpath('.//h2/a')
                if car_title:
                    name = Core.normalize2ascii(car_title[0].text)
                    #todo exceptions if nothing found
                parameters = car.xpath('.//table[@class="parametry"]/tbody')[0]
                if parameters:
                    cena = parameters.xpath('tr[@class="cena"]/td')[0].text
                    
                    other_parameters = parameters.xpath('tr[not(@class="cena")]')
                    for param in other_parameters:
                        th = parameters.xpath('tr/th').text
                        td = parameters.xpath('tr/td').text
                        td = Core.normalize2ascii(td)
                        if th == 'Vyrobeno':
                            vyrobeno = Core.parseNumber(td)
                        elif th == 'Tachometr':
                            tachometr = Core.parseNumber(td)
                        elif th == 'Palivo':
                            palivo = td
                        elif th == 'Motorizace':
                            motorizace = td
                        elif th == 'Tvar karoserie':
                            tvar_karoserie = td
            # DO something
            
    def close(self):
        logger.info("Successfully finished {}".format(self.webDomain))
        self.driver.close()         
        
        #searchKeyElement = response.find_elements_by_xpath('//input[contains(@id,"destination")]')
        #tems = driver.find_elements_by_xpath("//ul[@id = 'myId']//li[not(@class)]")
        #for item in items:
            #item.click()