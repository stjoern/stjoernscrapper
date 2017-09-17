'''
Created on Sep 10, 2017

@author: mmullero
'''
from stjoernscrapper import logger
from stjoernscrapper.core import Core
from stjoernscrapper.mongo_service import db
import re
from stjoernscrapper.webcrawler import WebCrawler
from selenium.common.exceptions import NoSuchElementException
from pymongo.errors import DuplicateKeyError
from time import sleep

class Rohlik(WebCrawler):
    '''
    classdocs
    '''

    def __init__(self, *args, **kwargs):
        '''
        Constructor
        '''
        WebCrawler.__init__(self, *args, **kwargs)
    
    def get_sortiment(self, link):
        # e.g. /c300101000-pekarna-a-cukrarna
        link = link.split('?orderBy',1)[0]
        m = re.search('.*[0-9]+-(?P<sortiment>.*).*$', link)
        print(link)
        sortiment = m.group('sortiment')
        return sortiment.replace('-',' ')
    
    def parse(self):
        if self.checkDriver:
            self._check_for_driver() #TODO: create decorator
            self.set_web_driver()
        self.driver.get(self.webDomain)
        
        sortiment_link = self.driver.find_element_by_class_name('categories__scroll-wrapper_desktop')
        
        links = [link.get_attribute('href') for link in sortiment_link.find_elements_by_xpath("//div[@class='categories__item_desktop']//a")]
        current_url_without_paging = self.driver.current_url
        
        for link in links:
            try:
                db_groceries = []
                sortiment = self.get_sortiment(link)
                print(sortiment)
                redirect_to_url = link
                self.driver.get(redirect_to_url)
                sleep(15)
                
                products = self.driver.find_elements_by_css_selector('.product__incart')
                for product in products:
                    db_grocery = {'ts': self.ts, 'created': self.iso_time}
                    if sortiment:
                        db_grocery['sortiment'] = sortiment
                    try:
                        size = product.find_element_by_class_name('product__amount')
                        if size:
                            size = size.text
                            db_grocery['size'] = Core.normalize2ascii(size)
                        h3 = product.find_element_by_xpath('.//h3[@class="product__name"]/a')
                        if h3:
                            title = h3.text
                            db_grocery['title']=Core.normalize2ascii(title)
                    except NoSuchElementException:
                        continue
                    except Exception, e:
                        raise ValueError(e.message)
                    
                    # promotion
                    try:
                        promotion_text = product.find_element_by_css_selector('.action.action-red')
                        if promotion_text:
                            promotion_text = promotion_text.text
                            db_grocery['promotion_text'] = Core.normalize2ascii(promotion_text)
                    except NoSuchElementException:
                        pass
                    except Exception, e:
                        raise ValueError(e.message)
                    
                    
                    try:
                        promotion_price = product.find_element_by_css_selector('.tac')
                        if promotion_price:
                            price = promotion_price.find_element_by_xpath('.//strong')
                            if price:
                                price = price.text
                                price = Core.parseNumber(price)
                                print(price)
                                price = Core.get_decimal_from_comma_string(price)
                                db_grocery['new_price']=price
                    except NoSuchElementException:
                        pass
                    except Exception, e:
                        raise ValueError(e.message)
                    # current/previous price
                    try:
                        old_price_text = None
                        previous_price = promotion_price.find_element_by_css_selector('span.grey > del')
                        if previous_price:
                            old_price_text = Core.normalize2ascii(previous_price.text)
                            old_price = Core.parseNumber(old_price_text)
                            old_price = Core.get_decimal_from_comma_string(old_price)
                            db_grocery['old_price']=old_price
                    except NoSuchElementException:
                        pass
                    except Exception, e:
                        raise ValueError(e.message)
                    
                    try:
                        cur_price = promotion_price.find_element_by_css_selector('span.grey')
                        if cur_price:
                            current_price = cur_price.text
                            current_price = Core.normalize2ascii(current_price)
                            if old_price_text:
                                current_price = current_price.split(old_price_text,1)[0]
                            current_price, measurement_unit = Core.get_decimal_measurement_unit(current_price)
                            db_grocery['current_price'] = {'Kc': current_price, 'measurement_unit': measurement_unit}
                    
                            if any(db_grocery):
                                db_groceries.append(db_grocery)    
                    except NoSuchElementException:
                        pass
                    except Exception, e:
                        raise ValueError(e.message)
                    
                if any(db_groceries):
                    try:
                        db[self.dbName].insert(db_groceries,{'ordered':False})
                    except DuplicateKeyError:
                        raise ValueError("DB error at {}, {}".format(self.dbName, e.message))
                        #for item in db_groceries:
                        #    sub_sortiment = item.pop('sortiment',None)
                        #    db[self.dbName].update({sub_sortiment},{'$set': sub_sortiment})
                    except Exception, e:
                        raise ValueError("DB error at {}, {}".format(self.dbName, e.message))
                        # add subcategory
                    
            except (ValueError, Exception), e:
                logger.error("Error occurred at {} while parsing the site. {}".format(self.dbName, e.message))
                continue
            
        return 0

    def close(self):
        logger.info("Successfully finished {}".format(self.webDomain))
        self.driver.close()         
        