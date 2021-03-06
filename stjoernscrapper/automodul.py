'''
Created on Sep 23, 2017

@author: mmullero
'''
from stjoernscrapper.webcrawler import WebCrawler
from stjoernscrapper.core import Core, autolog, errorlog
from selenium import webdriver
from time import sleep
from lxml import html
import re

class Automodul(WebCrawler):
    '''
    Automodul Crawling
    '''

    def __init__(self, *args, **kwargs):
        '''
        Constructor
        '''
        WebCrawler.__init__(self, *args, **kwargs)

    def _getPager(self):
        autolog(self.logger)
        '''
        getPager method is dedicated for getting range (start, endPage)
        '''
        elems = self.driver.find_elements_by_xpath("//div[@class='pager']/a[@href]")
        if elems:
            last_href = elems[-1].get_attribute('href')
            self.logger.info(last_href)
            m = re.search('.*&pg=(?P<maxpage>[0-9]+)$', last_href)
            max_page = int(m.group('maxpage'))
            return max_page
        return None
         
    def parse(self):
        autolog(self.logger)
        try:
        
            WebCrawler.parse(self)
            links = [link.get_attribute('href') for link in self.driver.find_elements_by_xpath("//div[@id='filtr']/ul/li/a")]
            for link in links:
                self.logger.info("Crawling Automodul, link: {}".format(link))
                try:
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
                    
                    self.logger.info("Crawling {} -> {}, category: {}".format(self.webDomain, link, typ))
                    
                    submitButton = self.driver.find_element_by_xpath('//input[@type="submit"]')
                    if submitButton:
                        submitButton.click()
                        sleep(15)
                        
                    page_max = self._getPager()
                    self.logger.debug("Crawling {} -> max page no. {} in link {}".format(self.webDomain, page_max, link))
                    
                    current_url_without_paging = self.driver.current_url
                    
                    for page in range(0,page_max):
                        try:
                            self.logger.info('Parsing {} page: {}'.format(self.webDomain, page))
                            redirect_to_url = "{no_page}&pg={page}".format(no_page=current_url_without_paging, page=page)
                            self.driver.get(redirect_to_url)
                            db_cars = []
                            
                            parser = html.fromstring(self.driver.page_source, self.driver.current_url)
                            cars = parser.xpath('//div[contains(@name,"auto")]/div[@class="pravaCast"]')
                            if not cars:
                                continue
                            for car in cars:
                                try:
                                    autolog(self.logger)
                                    db_car = {'type': typ, 'created': self.iso_time}
                                    car_title = car.xpath('.//h2/a')
                                    if car_title:
                                        db_car['ts'] = self.ts
                                        db_car['title'] = Core.normalize2ascii(car_title[0].text)

                                    parameters = car.xpath('.//table[@class="parametry"]/tbody')[0]
                                    if parameters is not None:
                                        cena = parameters.xpath('tr[@class="cena"]/td')[0].text
                                        if len(cena):
                                            cena = Core.normalize2ascii(cena)
                                            value = Core.parseNumber(cena)
                                            if value:
                                                try:
                                                    val = Core.get_decimal_from_comma_string(value)
                                                    if val:
                                                        db_car['price'] = val
                                                except ValueError:
                                                    db_car['price'] = value
                                                    pass
                                        other_parameters = parameters.xpath('tr[not(@class="cena")]')
                                        for param in other_parameters:
                                            th = param.xpath('th')[0].text
                                            td = param.xpath('td')[0].text
                                            if not td:
                                                continue
                                            td = Core.normalize2ascii(td)
                                            if not len(td):
                                                continue
                                            if th == 'Vyrobeno':
                                                value = Core.parseNumber(td)
                                                if value:
                                                    try:
                                                        val = int(value)
                                                        db_car['produced'] = val
                                                    except ValueError:
                                                        db_car['produced'] = value
                                            elif th == 'Tachometr':
                                                value = Core.parseNumber(td)
                                                if value:
                                                    try:
                                                        val = int(value)
                                                        db_car['speedometer'] = val
                                                    except ValueError:
                                                        db_car['speedometer'] = value
                                            elif th == 'Palivo':
                                                db_car['fuel'] = td
                                            elif th == 'Motorizace':
                                                db_car['motorizace'] = td
                                            elif th == 'Tvar karoserie':
                                                db_car['body_shape'] = td
                                            else:
                                                continue
                                    if any(db_car):
                                        db_cars.append(db_car)
                                
                                except Exception as e:
                                    errorlog(self.logger, e)
                                    continue
                            
                            if any(db_cars):
                                self.logger.debug("Inserting records to {}".format(self.dbName))
                                self.db[self.dbName].insert(db_cars,{'ordered':False})
                        
                        except (ValueError, Exception) as e:
                            errorlog(self.logger, e)
                            continue
                        
                except Exception as e:
                    errorlog(self.logger, e)
                    continue
                
        except Exception as e:
            errorlog(self.logger, e)    
        finally:
            WebCrawler.close(self) 
            return WebCrawler.success(self)
              
