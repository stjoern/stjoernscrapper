'''
Created on Sep 10, 2017

@author: mmullero
'''
import re

from selenium.common.exceptions import NoSuchElementException

from stjoernscrapper import logger
from stjoernscrapper.core import Core
from stjoernscrapper.mongo_service import db
from stjoernscrapper.webcrawler import WebCrawler


class NakupITesco(WebCrawler):
    '''
    classdocs
    '''

    def __init__(self, *args, **kwargs):
        '''
        Constructor
        '''
        WebCrawler.__init__(self, *args, **kwargs)
    
    def _getPager(self):
        '''
        getPager method is dedicated for getting range (start, endPage)
        '''
        elems = self.driver.find_elements_by_xpath("//li[@class='pagination-btn-holder']/a")
        if elems:
            #driver.find_element_by_css_selector('#tinymce > p').send_keys('your text here')
            last_href = elems[-2].get_attribute('href')
            print(last_href)
            m = re.search('.*/all\?page=(?P<maxpage>[0-9]+)$', last_href)
            max_page = int(m.group('maxpage'))
            return max_page
        return None
    
    def parse(self):
        if self.checkDriver:
            self._check_for_driver() #TODO: create decorator
            self.set_web_driver()
        self.driver.get(self.webDomain)
        
        links = [
            'shop/ovoce-a-zelenina/all',
            'shop/mlecne-vyrobky-a-vejce/all',
            'shop/pecivo/all',
            'shop/maso-ryby-a-lahudky/all',
            'shop/trvanlive-potraviny/all',
            'shop/mrazene-potraviny/all',
            'shop/napoje/all',
            'shop/alkoholicke-napoje/all',
            'shop/pece-o-domacnost/all',
            'shop/drogerie-a-kosmetika/all',
            'shop/pece-o-deti/all',
            'shop/chovatelske-potreby/all',
            'shop/domov-a-zabava/all'
        ]
        
        def get_sortiment(string_from):
            m = re.search('^shop/(?P<sortiment>.*)/all$', string_from)
            string_to = m.group('sortiment')
            string_to = string_to.replace('-',' ')
            return string_to
        
        current_url_without_paging = self.driver.current_url
        for link in links:
            
            redirect_to_url = "{}/{}".format(current_url_without_paging, link)
            self.driver.get(redirect_to_url)
            page_max = self._getPager()
            sortiment = get_sortiment(link)
            for page in range(1,page_max):
                db_groceries = []
                print('page: {}'.format(page))
                redirect_to_url = "{no_page}?page={page}".format(no_page=redirect_to_url, page=page)
                self.driver.get(redirect_to_url)
              
                goods = self.driver.find_elements_by_class_name('tile-content')
                for item in goods:
                    try:
                        # title
                        try:
                            db_grocery = {'sortiment': sortiment, 'ts': self.ts, 'created': self.iso_time}
                            jmeno = item.find_element_by_css_selector('a.product-tile--title').text
                            if not jmeno:
                                continue
                            jmeno = Core.normalize2ascii(jmeno)
                            db_grocery['title'] = jmeno
                        except NoSuchElementException:
                            pass
                        except Exception, e:
                            raise ValueError(e.message)
                        # promoce
                        try:
                            promoce_text = item.find_element_by_css_selector('.product-promotion .offer-text').text
                            db_grocery['promotion_text'] = Core.normalize2ascii(promoce_text)
                            
                            promoce_date = item.find_element_by_css_selector('.product-promotion .dates').text
                            db_grocery['promotion_date'] = Core.normalize2ascii(promoce_date)
                        except NoSuchElementException:
                            pass
                        except Exception, e:
                            raise ValueError(e.message)
                        # check radio button for weight 
                        try:
                            #item.find_element_by_xpath('.//input[@type="radio" and @value="kg"]').click
                            cena = item.find_element_by_xpath('.//div[@class="price-per-quantity-weight"]//span[@class="value"]').text
                            db_grocery['price'] = Core.get_decimal_from_comma_string(cena)
                            
                            mena = item.find_element_by_xpath('.//div[@class="price-per-quantity-weight"]//span[@class="currency').text
                            mena = Core.normalize2ascii(mena)
                            jednotka = item.find_element_by_xpath('.//div[@class="price-per-quantity-weight"]//span[@class="weight').text
                            jednotka = Core.normalize2ascii(jednotka)
                            db_grocery['unit_of_measure'] =  '{}/{}'.format(mena, jednotka)
                        except NoSuchElementException:
                            pass
                        except Exception, e:
                            raise ValueError(e.message)    
                     
                    except ValueError, e:
                        logger.error("Error occurred at {} while parsing the site. {}".format(self.dbName, e.message))
                        continue
                    if any(db_grocery):
                        db_groceries.append(db_grocery)    
                
                if any(db_groceries):
                    db[self.dbName].insert(db_groceries,{'ordered':False})
            
    def close(self):
        logger.info("Successfully finished {}".format(self.webDomain))
        self.driver.close()         
        