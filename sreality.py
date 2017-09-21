'''
Created on Sep 19, 2017

@author: mmullero
'''
import re

from selenium.common.exceptions import NoSuchElementException

from stjoernscrapper import logger
from stjoernscrapper.core import Core
from stjoernscrapper.mongo_service import db
from stjoernscrapper.webcrawler import WebCrawler
from selenium.webdriver.common.keys import Keys


class Sreality(WebCrawler):
    '''
    classdocs
    '''

    def __init__(self, *args, **kwargs):
        '''
        Constructor
        '''
        WebCrawler.__init__(self, *args, **kwargs)
    
    def getCategory(self, link):
        # 'https://www.sreality.cz/hledani/byty'
        m = re.match('.*/(?P<sortiment>.*)$', link)
        if not m:
            return None
        sortiment = m.group('sortiment')
        return sortiment 
    
    def _getPager(self):
        '''
        getPager method is dedicated for getting range (start, endPage)
        '''
        ads = self.driver.find_elements_by_xpath(".//span[@class='numero ng-binding']")
        if ads:
            try:
                no_ads = ads[-1].text
                no_ads = Core.parseNumber(no_ads)
                no_ads = int(no_ads)
                
                no_of_ad_in_page = ads[0].text
                filter = re.compile(ur'.*\u2013(.*)', re.UNICODE)
                per_page = filter.match(no_of_ad_in_page)
                per_page = int(per_page.group(1))
                return (no_ads + per_page // 2)//per_page
            except Exception, e:
                logger.error("Cannot get paging for {}, details: {}".format(self.dbName, e.message))
                return None
        return None
    
    def parse(self):
        if self.checkDriver:
            self._check_for_driver() #TODO: create decorator
            self.set_web_driver()
        self.driver.get(self.webDomain)
        
        def _get_title_link(ad):
            text = ad.text
            if not text:
                return None
            title = Core.normalize2ascii(text)
            ad_href = ad.get_attribute('href')
            return (title, ad_href)
            
        filter_url = 'stari=dnes'    
        links = [link.get_attribute('href') for link in self.driver.find_elements_by_xpath("//a[@class='dir-hp-signpost__item__link']")]
        for link in links:
            self.driver.get(link)
            my_filter = filter_url
            try:
                self.driver.find_element_by_xpath("//span[@class='caption ng-binding' and contains(text(), 'bez omezen')]")
            except NoSuchElementException, e:
                my_filter = None
            except Exception, e:
                logger.error("problem getting filter button")
                return -1
            #stari_inzeratu = self.driver.find_element_by_xpath("//span[@class='caption ng-binding' and contains(text(), 'bez omezen')]")
            #self.driver.execute_script("arguments[0].innerHTML = arguments[1];", stari_inzeratu, "den")
            #stari_inzeratu.send_keys(Keys.DOWN)
            
            self.driver.find_element_by_xpath("//button[@type='submit']").click()
            without_filter_url = self.driver.current_url
            if my_filter:
                with_filter = "{}?{}".format(without_filter_url, my_filter)
                self.driver.get(with_filter)
            
            category = self.getCategory(link)
            
            # paging
            current_url = self.driver.current_url
            no_of_page_hops = self._getPager()
            if not no_of_page_hops:
                return -1
            else:
                for page in range(1,no_of_page_hops):
                    print("page no. {}".format(page))
                    redirect_url = "{cur_url}?strana={page}".format(cur_url=current_url, page=page)
                    self.driver.get(redirect_url)
                    db_records = []
                    
                    ads = map(lambda x: _get_title_link(x), self.driver.find_elements_by_xpath('//a[@class="title"]'))
                    try:
                        for title, ad in ads:
                            if not title:
                                continue
                            db_record = {'ts': self.ts, 'created': self.iso_time, 'category': category, 'title': title }
                           
                            self.driver.get(ad)
                            
                            # location
                            try:
                                try:
                                    text = self.driver.find_element_by_class_name('location').text
                                    if text:
                                        text = Core.normalize2ascii(text)
                                        if len(text):
                                            db_record['location'] = text
                                except NoSuchElementException:
                                    pass
                                except Exception, e:
                                    raise ValueError(e.message)
                                    
                                # price
                                try:
                                    text = self.driver.find_element_by_class_name('norm-price').text
                                    if text:
                                        text = Core.parseNumber(text)
                                        text = Core.get_decimal_from_comma_string(text)
                                        db_record['price'] = text
                                except NoSuchElementException:
                                    pass
                                except AttributeError:
                                    if len(text):
                                        db_record['price']=text
                                except Exception, e:
                                    raise ValueError(e.message)
                                
                                # stavba
                                try:
                                    text = self.driver.find_element_by_xpath("//*[starts-with(text(), 'Pozn') and contains(text(), 'mka k cen')]")
                                    if text:
                                        text = text.find_element_by_xpath('../strong').text
                                        text = Core.normalize2ascii(text)
                                        if len(text):
                                            db_record['price_comment'] = text
                                except NoSuchElementException:
                                    pass
                                except Exception, e:
                                    raise ValueError(e.message)        
                                
                                # description
                                try:
                                    text = self.driver.find_element_by_class_name('description').text
                                    if text:
                                        text = Core.normalize2ascii(text)
                                        if len(text):
                                            db_record['description'] = text
                                except NoSuchElementException:
                                    pass
                                except Exception, e:
                                    raise ValueError(e.message)        
                                
                                # ID zakazky
                                try:
                                    id_zakazky_lbl = self.driver.find_element_by_xpath("//*[starts-with(text(), 'ID zak')]")
                                    if id_zakazky_lbl:
                                        id_zakazky = id_zakazky_lbl.find_element_by_xpath('../strong').text
                                        if id_zakazky:
                                            try:
                                                id_zakazky = Core.normalize2ascii(id_zakazky)
                                                if len(id_zakazky):
                                                    db_record['order_id']=id_zakazky
                                            except Exception as e:
                                                logger.error("While parsing {}, details: {}".format(self.dbName, e.message))
                                                pass
                                except NoSuchElementException:
                                    pass
                                except Exception, e:
                                    raise ValueError(e.message)        
                                            
                                # actualizace
                                try:
                                    text = self.driver.find_element_by_xpath("//*[starts-with(text(), 'Aktualizace')]")
                                    if text:
                                        text = text.find_element_by_xpath('../strong').text
                                        text = Core.normalize2ascii(text)
                                        if len(text):
                                            db_record['updated'] = text
                                except NoSuchElementException:
                                    pass
                                except Exception, e:
                                    raise ValueError(e.message)        
                                    
                                # stavba
                                try:
                                    text = self.driver.find_element_by_xpath("//*[starts-with(text(), 'Stavba')]")
                                    if text:
                                        text = text.find_element_by_xpath('../strong').text
                                        text = Core.normalize2ascii(text)
                                        if len(text):
                                            db_record['building'] = text
                                except NoSuchElementException:
                                    pass
                                except Exception, e:
                                    raise ValueError(e.message)  
                                        
                                # stav objektu
                                try:
                                    text = self.driver.find_element_by_xpath("//*[starts-with(text(), 'Stav objektu')]")
                                    if text:
                                        text = text.find_element_by_xpath('../strong').text
                                        text = Core.normalize2ascii(text)
                                        if len(text):
                                            db_record['building_state'] = text
                                except NoSuchElementException:
                                    pass
                                except Exception, e:
                                    raise ValueError(e.message)        
                                    
                                # poloha domu
                                try:
                                    text = self.driver.find_element_by_xpath("//*[starts-with(text(), 'Poloha domu')]")
                                    if text:
                                        text = text.find_element_by_xpath('../strong').text
                                        text = Core.normalize2ascii(text)
                                        if len(text):
                                            db_record['building_situation'] = text
                                except NoSuchElementException:
                                    pass
                                except Exception, e:
                                    raise ValueError(e.message)        
                                    
                                # umisteni objektu
                                try:
                                    text = self.driver.find_element_by_xpath("//*[starts-with(text(), 'Um') and contains(text(), 'objektu')]")
                                    if text:
                                        text = text.find_element_by_xpath('../strong').text
                                        text = Core.normalize2ascii(text)
                                        if len(text):
                                            db_record['building_location'] = text
                                except NoSuchElementException:
                                    pass
                                except Exception, e:
                                    raise ValueError(e.message)        
                                    
                                # typ domu
                                try:
                                    text = self.driver.find_element_by_xpath("//*[starts-with(text(),'Typ domu')]")
                                    if text:
                                        text = text.find_element_by_xpath('../strong').text
                                        text = Core.normalize2ascii(text)
                                        if len(text):
                                            db_record['house_type'] = text
                                except NoSuchElementException:
                                    pass
                                except Exception, e:
                                    raise ValueError(e.message)        
                                    
                                # podlazi
                                try:
                                    text = self.driver.find_element_by_xpath("//*[starts-with(text(), 'Podla')]")
                                    if text:
                                        text = text.find_element_by_xpath('../strong').text
                                        text = Core.normalize2ascii(text)
                                        if len(text):
                                            db_record['floor'] = text
                                except NoSuchElementException:
                                    pass
                                except Exception, e:
                                    raise ValueError(e.message)        
                                    
                                # zastavena plocha
                                try:
                                    text = self.driver.find_element_by_xpath("//*[starts-with(text(), 'Plocha zastav')]")
                                    if text:
                                        text = text.find_element_by_xpath('../strong').text
                                        text = Core.normalize2ascii(text)
                                        if len(text):
                                            db_record['buil_up_area']=text
                                except NoSuchElementException:
                                    pass
                                except Exception, e:
                                    raise ValueError(e.message)
                                
                                # uzitna plocha
                                try:
                                    text = self.driver.find_element_by_xpath("//*[starts-with(text(), 'U') and contains(text(),'plocha')]")
                                    if text:
                                        text = text.find_element_by_xpath('../strong').text
                                        text = Core.normalize2ascii(text)
                                        if len(text):
                                            db_record['built_up_area']=text
                                except NoSuchElementException:
                                    pass
                                except Exception, e:
                                    raise ValueError(e.message)
                                
                                # plocha podlahova
                                try:
                                    text = self.driver.find_element_by_xpath("//*[starts-with(text(), 'Plocha podlahov')]")
                                    if text:
                                        text = text.find_element_by_xpath('../strong').text
                                        text = Core.normalize2ascii(text)
                                        if len(text):
                                            db_record['floor_area']=text
                                except NoSuchElementException:
                                    pass
                                except Exception, e:
                                    raise ValueError(e.message)
                                
                                # sklep
                                try:
                                    text = self.driver.find_element_by_xpath("//*[starts-with(text(), 'Sklep')]")
                                    if text:
                                        text = text.find_element_by_xpath('../strong').text
                                        text = Core.normalize2ascii(text)
                                        if len(text):
                                            db_record['buil_up_area']=text
                                except NoSuchElementException:
                                    pass
                                except Exception, e:
                                    raise ValueError(e.message)
                                
                                # parkovani
                                try:
                                    text = self.driver.find_element_by_xpath("//*[starts-with(text(), 'Parkov')]")
                                    if text:
                                        text = text.find_element_by_xpath('../strong').text
                                        text = Core.normalize2ascii(text)
                                        if len(text):
                                            db_record['parking']=text
                                except NoSuchElementException:
                                    pass
                                except Exception, e:
                                    raise ValueError(e.message)
                                
                                # doprava
                                try:
                                    text = self.driver.find_element_by_xpath("//*[starts-with(text(), 'Doprava')]")
                                    if text:
                                        text = text.find_element_by_xpath('../strong').text
                                        text = Core.normalize2ascii(text)
                                        if len(text):
                                            db_record['transport']=text
                                except NoSuchElementException:
                                    pass
                                except Exception, e:
                                    raise ValueError(e.message)
                                
                                # doprava
                                try:
                                    text = self.driver.find_element_by_xpath("//*[starts-with(text(), 'Doprava')]")
                                    if text:
                                        text = text.find_element_by_xpath('../strong').text
                                        text = Core.normalize2ascii(text)
                                        if len(text):
                                            db_record['communication']=text
                                except NoSuchElementException:
                                    pass
                                except Exception, e:
                                    raise ValueError(e.message)
                                
                                # komunikace
                                try:
                                    text = self.driver.find_element_by_xpath("//*[starts-with(text(), 'Komunikace')]")
                                    if text:
                                        text = text.find_element_by_xpath('../strong').text
                                        text = Core.normalize2ascii(text)
                                        if len(text):
                                            db_record['transport']=text
                                except NoSuchElementException:
                                    pass
                                except Exception, e:
                                    raise ValueError(e.message)
                                
                                # vlastnictvi
                                try:
                                    text = self.driver.find_element_by_xpath("//*[starts-with(text(), 'Vlastnictv')]")
                                    if text:
                                        text = text.find_element_by_xpath('../strong').text
                                        text = Core.normalize2ascii(text)
                                        if len(text):
                                            db_record['ownership'] = text
                                except NoSuchElementException:
                                    pass
                                except Exception, e:
                                    raise ValueError(e.message)
                                            
                                # energeticka narocnost budovy
                                try:
                                    text = self.driver.find_element_by_xpath("//*[starts-with(text(), 'Energetick') and contains(text(), 'nost budovy')]")
                                    if text:
                                        text = text.find_element_by_xpath('../strong').text
                                        text = Core.normalize2ascii(text)
                                        if len(text):
                                            db_record['energy_performance'] = text
                                except NoSuchElementException:
                                    pass
                                except Exception, e:
                                    raise ValueError(e.message)
                                
                                # topeni
                                try:
                                    text = self.driver.find_element_by_xpath("//*[starts-with(text(), 'Topen')]")
                                    if text:
                                        text = text.find_element_by_xpath('../strong').text
                                        text = Core.normalize2ascii(text)
                                        if len(text):
                                            db_record['heating'] = text
                                except NoSuchElementException:
                                    pass
                                except Exception, e:
                                    raise ValueError(e.message)
                                
                                # vytah
                                try:
                                    text = self.driver.find_element_by_xpath("//*[starts-with(text(), 'V') and contains(text(), 'tah')]")
                                    if text:
                                        text = text.find_element_by_xpath('../strong').text
                                        text = Core.normalize2ascii(text)
                                        if len(text):
                                            db_record['lift'] = text
                                except NoSuchElementException:
                                    pass
                                except Exception, e:
                                    raise ValueError(e.message)
                                
                                # vybaveni
                                try:
                                    text = self.driver.find_element_by_xpath("//*[starts-with(text(), 'Vybaven')]")
                                    if text:
                                        text = text.find_element_by_xpath('../strong').text
                                        text = Core.normalize2ascii(text)
                                        if len(text):
                                            db_record['furnished'] = text
                                except NoSuchElementException:
                                    pass
                                except Exception, e:
                                    raise ValueError(e.message)
                                
                                # elektrina
                                try:
                                    text = self.driver.find_element_by_xpath("//*[starts-with(text(), 'Elekt')]")
                                    if text:
                                        text = text.find_element_by_xpath('../strong').text
                                        text = Core.normalize2ascii(text)
                                        if len(text):
                                            db_record['electricity'] = text
                                except NoSuchElementException:
                                    pass
                                except Exception, e:
                                    raise ValueError(e.message)
                                
                                # voda
                                try:
                                    text = self.driver.find_element_by_xpath("//*[starts-with(text(), 'Voda')]")
                                    if text:
                                        text = text.find_element_by_xpath('../strong').text
                                        text = Core.normalize2ascii(text)
                                        if len(text):
                                            db_record['water'] = text
                                except NoSuchElementException:
                                    pass
                                except Exception, e:
                                    raise ValueError(e.message)
                                
                                if any(db_record):
                                    db_records.append(db_record)
                                    
                                # plocha pozemku
                                try:
                                    text = self.driver.find_element_by_xpath("//*[starts-with(text(), 'Plocha pozemku')]")
                                    if text:
                                        text = text.find_element_by_xpath('../strong').text
                                        text = Core.normalize2ascii(text)
                                        if len(text):
                                            db_record['land_area'] = text
                                except NoSuchElementException:
                                    pass
                                except Exception, e:
                                    raise ValueError(e.message)
                                
                                # plocha zahrady
                                try:
                                    text = self.driver.find_element_by_xpath("//*[starts-with(text(), 'Plocha zahrady')]")
                                    if text:
                                        text = text.find_element_by_xpath('../strong').text
                                        text = Core.normalize2ascii(text)
                                        if len(text):
                                            db_record['garden_area'] = text
                                except NoSuchElementException:
                                    pass
                                except Exception, e:
                                    raise ValueError(e.message)
                                
                                # vnitrni omitky
                                try:
                                    text = self.driver.find_element_by_xpath("//*[starts-with(text(), 'vnit') and contains(text(), 'tky')]")
                                    if text:
                                        text = text.find_element_by_xpath('../strong').text
                                        text = Core.normalize2ascii(text)
                                        if len(text):
                                            db_record['internal_plaster'] = text
                                except NoSuchElementException:
                                    pass
                                except Exception, e:
                                    raise ValueError(e.message)  
                                
                                # krytina
                                try:
                                    text = self.driver.find_element_by_xpath("//*[contains(text(), 'Krytina')]")
                                    if text:
                                        text = text.find_element_by_xpath('../strong').text
                                        text = Core.normalize2ascii(text)
                                        if len(text):
                                            db_record['covering'] = text
                                except NoSuchElementException:
                                    pass
                                except Exception, e:
                                    raise ValueError(e.message)  
                                
                                # strecha
                                try:
                                    text = self.driver.find_element_by_xpath("//*[starts-with(text(), 'St') and contains(text(), 'echa')]")
                                    if text:
                                        text = text.find_element_by_xpath('../strong').text
                                        text = Core.normalize2ascii(text)
                                        if len(text):
                                            db_record['roof'] = text
                                except NoSuchElementException:
                                    pass
                                except Exception, e:
                                    raise ValueError(e.message)           
                                
                                # stropy
                                try:
                                    text = self.driver.find_element_by_xpath("//*[contains(text(), 'Stropy')]")
                                    if text:
                                        text = text.find_element_by_xpath('../strong').text
                                        text = Core.normalize2ascii(text)
                                        if len(text):
                                            db_record['ceilings'] = text
                                except NoSuchElementException:
                                    pass
                                except Exception, e:
                                    raise ValueError(e.message)        
                                
                                # vnejsi obklady
                                try:
                                    text = self.driver.find_element_by_xpath("//*[starts-with(text(), 'Vn') and contains(text(), 'obklady')]")
                                    if text:
                                        text = text.find_element_by_xpath('../strong').text
                                        text = Core.normalize2ascii(text)
                                        if len(text):
                                            db_record['outer_cladding'] = text
                                except NoSuchElementException:
                                    pass
                                except Exception, e:
                                    raise ValueError(e.message)   
                                
                                # okna
                                try:
                                    text = self.driver.find_element_by_xpath("//*[starts-with(text(), 'Okna')]")
                                    if text:
                                        text = text.find_element_by_xpath('../strong').text
                                        text = Core.normalize2ascii(text)
                                        if len(text):
                                            db_record['windows'] = text
                                except NoSuchElementException:
                                    pass
                                except Exception, e:
                                    raise ValueError(e.message)   
                                
                                # cena za m2
                                try:
                                    text = self.driver.find_element_by_xpath("//*[starts-with(text(), 'Cena za m')]")
                                    if text:
                                        text = text.find_element_by_xpath('../strong').text
                                        text = Core.normalize2ascii(text)
                                        text, _ = Core.get_decimal_from_comma_string(text)
                                        if len(text):
                                            db_record['price_per_m2'] = text
                                except NoSuchElementException:
                                    pass
                                except AttributeError:
                                    if len(text):
                                        db_record['price_per_m2']=text
                                except Exception, e:
                                    raise ValueError(e.message)            
                                
                                if any(db_record):
                                    db_records.append(db_record)
                        
                            except ValueError, e:
                                logger.error("Error occurred at {} while parsing the site. {}".format(self.dbName, e.message))
                                continue
                    
                        if any(db_records):
                            db[self.dbName].insert(db_records, {'ordered':False})
                        
                    except Exception, e:
                        logger.error("Error occurred at {} while parsing the site. {}".format(self.dbName, e.message))
                        continue
                    
        return 0             
                
            
    def close(self):
        logger.info("Successfully finished {}".format(self.webDomain))
        self.driver.close()         
        