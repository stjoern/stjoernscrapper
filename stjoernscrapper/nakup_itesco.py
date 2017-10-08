'''
Created on Sep 10, 2017

@author: mmullero
'''
from stjoernscrapper.core import Core, autolog, errorlog
from stjoernscrapper.webcrawler import WebCrawler
import re
from selenium.common.exceptions import NoSuchElementException

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
        autolog(self.logger)
        elems = self.driver.find_elements_by_xpath("//li[@class='pagination-btn-holder']/a")
        if elems:
            last_href = elems[-2].get_attribute('href')
            print(last_href)
            m = re.search('.*/all\?page=(?P<maxpage>[0-9]+)$', last_href)
            max_page = int(m.group('maxpage'))
            return max_page
        return None
    
    def parse(self):
        autolog(self.logger)
        try:
            WebCrawler.parse(self)
            
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
                autolog(self.logger)
                m = re.search('^shop/(?P<sortiment>.*)/all$', string_from)
                string_to = m.group('sortiment')
                string_to = string_to.replace('-',' ')
                return string_to
            
            current_url_without_paging = self.driver.current_url
            for link in links:
                self.logger.info("Parsing {db}, link: {link}".format(db=self.dbName, link=link))
                redirect_to_url = "{}/{}".format(current_url_without_paging, link)
                self.driver.get(redirect_to_url)
                page_max = self._getPager()
                self.logger.debug("{} pages in link: {}".format(page_max, link))
                sortiment = get_sortiment(link)
                self.logger.debug("Sortiment: {} in link: {}".format(sortiment, link))
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
                                if len(jmeno):
                                    db_grocery['title'] = jmeno
                            except NoSuchElementException:
                                pass
                            except Exception as e:
                                raise ValueError(e)
                            # promoce
                            try:
                                promoce_text = item.find_element_by_css_selector('.product-promotion .offer-text').text
                                if len(promoce_text):
                                    db_grocery['promotion_text'] = Core.normalize2ascii(promoce_text)
                                
                                promoce_date = item.find_element_by_css_selector('.product-promotion .dates').text
                                db_grocery['promotion_date'] = Core.normalize2ascii(promoce_date)
                            except NoSuchElementException:
                                pass
                            except Exception as e:
                                raise ValueError(e)
                            # check radio button for weight 
                            try:
                                #item.find_element_by_xpath('.//input[@type="radio" and @value="kg"]').click
                                cena = item.find_element_by_xpath('.//div[@class="price-per-quantity-weight"]//span[@class="value"]').text
                                db_grocery['price'] = Core.get_decimal_from_comma_string(cena)
                                
                                mena = item.find_element_by_xpath('.//div[@class="price-per-quantity-weight"]//span[@class="currency"]').text
                                mena = Core.normalize2ascii(mena)
                                jednotka = item.find_element_by_xpath('.//div[@class="price-per-quantity-weight"]//span[@class="weight"]').text
                                jednotka = Core.normalize2ascii(jednotka)
                                if len(jednotka):
                                    db_grocery['unit_of_measure'] =  '{}/{}'.format(mena, jednotka)
                            except NoSuchElementException:
                                pass
                            except Exception as e:
                                raise ValueError(e)    
                         
                        except ValueError as e:
                            errorlog(self.logger, e)
                            continue
                        if any(db_grocery):
                            db_groceries.append(db_grocery)  
                              
                    if any(db_groceries):
                        self.logger.debug("Inserting records to {}".format(self.dbName))
                        self.db[self.dbName].insert(db_groceries,{'ordered':False})
        except Exception as e:
            errorlog(self.logger, e)   
        finally:
            self.close()
      
        