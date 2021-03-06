'''
Created on Sep 10, 2017

@author: mmullero
'''
from stjoernscrapper.core import Core, autolog, errorlog
from stjoernscrapper.webcrawler import WebCrawler
import re
from selenium.common.exceptions import NoSuchElementException
from pymongo.errors import DuplicateKeyError
from time import sleep
from asyncio.log import logger

class Rohlik(WebCrawler):
    '''
    Rohlik Crawling
    '''
    def __init__(self, *args, **kwargs):
        '''
        Constructor
        '''
        WebCrawler.__init__(self, *args, **kwargs)
    
    def get_sortiment(self, link):
        try:
            autolog(self.logger)
            # e.g. /c300101000-pekarna-a-cukrarna
            link = link.split('?orderBy',1)[0]
            m = re.search('.*[0-9]+-(?P<sortiment>.*).*$', link)
            sortiment = m.group('sortiment')
            return sortiment.replace('-',' ')
        except (Exception, AttributeError) as e:
            self.logger.error("Error no such sortiment, details: {}".format(e))
            return None
    
    def parse(self):
        try:
            WebCrawler.parse(self)
            sortiment_link = self.driver.find_element_by_class_name('categories__scroll-wrapper_desktop')
            links = [link.get_attribute('href') for link in sortiment_link.find_elements_by_xpath("//div[@class='categories__item_desktop']//a")]
            
            for link in links:
                try:
                    autolog(self.logger)
                    db_groceries = []
                    sortiment = self.get_sortiment(link)
                    if not sortiment:
                        continue
                    self.logger.info("Crawling {} -> {}, category: {}".format(self.webDomain, link, sortiment))
                    
                    redirect_to_url = link
                    self.driver.get(redirect_to_url)
                    sleep(15)
                    
                    products = self.driver.find_elements_by_css_selector('.product__incart')
                    if products is None:
                        continue
                    for product in products:
                        autolog(self.logger)
                        try:
                            db_grocery = {'ts': self.ts, 'created': self.iso_time}
                            if sortiment:
                                db_grocery['sortiment'] = sortiment
                            try:
                                size = product.find_element_by_class_name('product__amount')
                                if size:
                                    size = size.text
                                    if len(size):
                                        db_grocery['size'] = Core.normalize2ascii(size)
                                h3 = product.find_element_by_xpath('.//h3[@class="product__name"]/a')
                                if h3:
                                    title = h3.text
                                    if len(title):
                                        db_grocery['title']=Core.normalize2ascii(title)
                            except NoSuchElementException:
                                continue
                            except Exception as e:
                                errorlog(self.logger, e)
                                continue
                            
                            # promotion
                            try:
                                promotion_text = product.find_element_by_css_selector('.action.action-red')
                                if promotion_text:
                                    promotion_text = promotion_text.text
                                    if len(promotion_text):
                                        db_grocery['promotion_text'] = Core.normalize2ascii(promotion_text)
                            except NoSuchElementException:
                                pass
                            except Exception as e:
                                errorlog(self.logger, e)
                                pass
                            
                            try:
                                promotion_price = product.find_element_by_css_selector('.tac')
                                if promotion_price:
                                    price = promotion_price.find_element_by_xpath('.//strong')
                                    if price:
                                        price = price.text
                                        price = Core.parseNumber(price)
                                        self.logger.debug("{} found price: {}".format(self.webDomain, price or 'price not set in web'))
                                        if not price: continue
                                        price = Core.get_decimal_from_comma_string(price)
                                        db_grocery['new_price']=price
                            except NoSuchElementException:
                                pass
                            except (AttributeError, KeyError) as e:
                                errorlog(self.logger, e)
                                autolog(self.logger)
                                continue
                            except Exception as e:
                                errorlog(self.logger, e)
                                continue
                            
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
                            except Exception as e:
                                errorlog(self.logger, e)
                                pass
                            
                            # current price
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
                            except Exception as e:
                                errorlog(self.logger, e)
                                pass
                            
                        except (ValueError, Exception) as e:
                            errorlog(self.logger, e)
                            continue
                        
                    if any(db_groceries):
                        try:
                            self.logger.debug("Inserting records to {}".format(self.dbName))
                            self.db[self.dbName].insert(db_groceries,{'ordered':False})
                        except DuplicateKeyError:
                            raise ValueError("DB error at {}, {}".format(self.dbName, e))
                        except Exception as e:
                            raise ValueError("DB error at {}, {}".format(self.dbName, e))
                        
                except (ValueError, Exception) as e:
                    errorlog(self.logger, e)
                    continue
        
        except Exception as e:
            errorlog(self.logger, e)    
        finally:
            WebCrawler.close(self) 
            return WebCrawler.success(self)
        