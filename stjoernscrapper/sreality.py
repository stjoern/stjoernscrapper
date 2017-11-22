'''
Created on Sep 19, 2017

@author: mmullero
'''

from stjoernscrapper.core import Core, autolog, errorlog
from stjoernscrapper.webcrawler import WebCrawler
import re
from selenium.common.exceptions import NoSuchElementException

class Sreality(WebCrawler):
    '''
    Sreality Crawling
    '''
    def __init__(self, *args, **kwargs):
        '''
        Constructor
        '''
        WebCrawler.__init__(self, *args, **kwargs)
    
    def getCategory(self, link):
        autolog(self.logger)
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
        autolog(self.logger)
        ads = self.driver.find_elements_by_xpath(".//span[@class='numero ng-binding']")
        if ads:
            try:
                no_ads = ads[-1].text
                no_ads = Core.parseNumber(no_ads)
                no_ads = int(no_ads)
                
                no_of_ad_in_page = ads[0].text
                filter_ = re.compile(u'.*\u2013(.*)', re.UNICODE)
                per_page = filter_.match(no_of_ad_in_page)
                per_page = int(per_page.group(1))
                return (no_ads + per_page // 2)//per_page
            except Exception as e:
                errorlog(self.logger, e)
                return None
        return None
    
    def parse(self):
        try:
            autolog(self.logger)
            WebCrawler.parse(self)
            
            def _get_title_link(ad):
                autolog(self.logger)
                text = ad.text
                if not text:
                    return None
                title = Core.normalize2ascii(text)
                ad_href = ad.get_attribute('href')
                return (title, ad_href)
                
            filter_url = 'stari=dnes'    
            links = [link.get_attribute('href') for link in self.driver.find_elements_by_xpath("//a[@class='dir-hp-signpost__item__link']")]
            for link in links:
                try:
                    autolog(self.logger)
                    self.logger.info("Crawling {} -> {}".format(self.webDomain, link))
                    
                    self.driver.get(link)
                    my_filter = filter_url
                    try:
                        self.driver.find_element_by_xpath("//span[@class='caption ng-binding' and contains(text(), 'bez omezen')]")
                    except NoSuchElementException as e:
                        my_filter = None
                    except Exception as e:
                        errorlog(self.logger, e)
                        self.logger.error("Sreality problem with filtering link: {}".format(link))
                        continue
                    
                    self.driver.find_element_by_xpath("//button[@type='submit']").click()
                    without_filter_url = self.driver.current_url
                    if my_filter:
                        with_filter = "{}?{}".format(without_filter_url, my_filter)
                        self.driver.get(with_filter)
                    
                    category = self.getCategory(link)
                    self.logger.info("Crawling {} in category: {}".format(self.webDomain, category))
                    
                    # paging
                    current_url = self.driver.current_url
                    no_of_page_hops = self._getPager()
                    
                    if not no_of_page_hops:
                        autolog(self.logger)
                        logger.error("Sreality problem while getting pages from link: {}".format(link))
                        continue
                    else:
                        for page in range(0,no_of_page_hops):
                            try:
                                autolog(self.logger)
                                self.logger.info("{} for page no. {}".format(self.webDomain, page))
                                redirect_url = "{cur_url}?strana={page}".format(cur_url=current_url, page=page)
                                self.driver.get(redirect_url)
                                
                                ads = map(lambda x: _get_title_link(x), self.driver.find_elements_by_xpath('//a[@class="title"]'))
                                ads = list(ads)
                                try:
                                    db_records = []
                                    for titlead in ads:
                                        try:
                                            autolog(self.logger)
                                            title = titlead[0]
                                            ad = titlead[1]
                                            if not title:
                                                continue
                                           
                                            self.logger.debug("Crawling Sreality with title: {}".format(title))
                                            self.driver.get(ad)
                                            
                                            # location
                                            try:
                                                db_record = {'ts': self.ts, 'created': self.iso_time, 'category': category, 'title': title }
                                                
                                                try:
                                                    text = self.driver.find_element_by_class_name('location').text
                                                    if text:
                                                        text = Core.normalize2ascii(text)
                                                        if len(text):
                                                            db_record['location'] = text
                                                except NoSuchElementException:
                                                    pass
                                                except Exception as e:
                                                    raise ValueError(e)
                                                    
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
                                                except Exception as e:
                                                    raise ValueError(e)
                                                
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
                                                except Exception as e:
                                                    raise ValueError(e)        
                                                
                                                # description
                                                try:
                                                    text = self.driver.find_element_by_class_name('description').text
                                                    if text:
                                                        text = Core.normalize2ascii(text)
                                                        if len(text):
                                                            db_record['description'] = text
                                                except NoSuchElementException:
                                                    pass
                                                except Exception as e:
                                                    raise ValueError(e)        
                                                
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
                                                                errorlog(self.logger, e)
                                                                pass
                                                except NoSuchElementException:
                                                    pass
                                                except Exception as e:
                                                    raise ValueError(e)        
                                                            
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
                                                except Exception as e:
                                                    raise ValueError(e)        
                                                    
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
                                                except Exception as e:
                                                    raise ValueError(e)  
                                                        
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
                                                except Exception as e:
                                                    raise ValueError(e)        
                                                    
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
                                                except Exception as e:
                                                    raise ValueError(e)        
                                                    
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
                                                except Exception as e:
                                                    raise ValueError(e)        
                                                    
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
                                                except Exception as e:
                                                    raise ValueError(e)        
                                                    
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
                                                except Exception as e:
                                                    raise ValueError(e)        
                                                    
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
                                                except Exception as e:
                                                    raise ValueError(e)
                                                
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
                                                except Exception as e:
                                                    raise ValueError(e)
                                                
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
                                                except Exception as e:
                                                    raise ValueError(e)
                                                
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
                                                except Exception as e:
                                                    raise ValueError(e)
                                                
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
                                                except Exception as e:
                                                    raise ValueError(e)
                                                
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
                                                except Exception as e:
                                                    raise ValueError(e)
                                                
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
                                                except Exception as e:
                                                    raise ValueError(e)
                                                
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
                                                except Exception as e:
                                                    raise ValueError(e)
                                                
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
                                                except Exception as e:
                                                    raise ValueError(e)
                                                            
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
                                                except Exception as e:
                                                    raise ValueError(e)
                                                
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
                                                except Exception as e:
                                                    raise ValueError(e)
                                                
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
                                                except Exception as e:
                                                    raise ValueError(e)
                                                
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
                                                except Exception as e:
                                                    raise ValueError(e)
                                                
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
                                                except Exception as e:
                                                    raise ValueError(e)
                                                
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
                                                except Exception as e:
                                                    raise ValueError(e)
                                                
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
                                                except Exception as e:
                                                    raise ValueError(e)
                                                
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
                                                except Exception as e:
                                                    raise ValueError(e)
                                                
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
                                                except Exception as e:
                                                    raise ValueError(e)  
                                                
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
                                                except Exception as e:
                                                    raise ValueError(e)  
                                                
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
                                                except Exception as e:
                                                    raise ValueError(e)           
                                                
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
                                                except Exception as e:
                                                    raise ValueError(e)        
                                                
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
                                                except Exception as e:
                                                    raise ValueError(e)   
                                                
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
                                                except Exception as e:
                                                    raise ValueError(e)   
                                                
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
                                                except Exception as e:
                                                    raise ValueError(e)            
                                                
                                                if any(db_record):
                                                    db_records.append(db_record)
                                        
                                            except (Exception, ValueError) as e:
                                                errorlog(self.logger, e)
                                                continue
                                            
                                        except (ValueError, Exception) as e:
                                            errorlog(self.logger, e)
                                            continue
                                        
                                    if any(db_records):
                                        self.logger.debug("Inserting records to {}".format(self.dbName))
                                        self.db[self.dbName].insert(db_records, {'ordered':False})
                                        db_records = []
                                    
                                except Exception as e:
                                    errorlog(self.logger, e)
                                    continue
                            except (ValueError, Exception) as e:
                                errorlog(self.logger, e)
                                continue
                            
                except (ValueError, Exception) as e:
                    errorlog(self.logger, e)
                    continue
                            
        except Exception as e:
            errorlog(self.logger, e)    
        finally:
            WebCrawler.close(self) 
            return WebCrawler.success(self)              
                    
        