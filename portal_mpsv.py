'''
Created on Sep 18, 2017

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
from dateutil.parser import parse

class PortalMpsv(WebCrawler):
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
        
        
        links = [{'category': Core.normalize2ascii(link.text), 'title': Core.normalize2ascii(link.get_attribute('title')), 'link': link} for link in self.driver.find_elements_by_class_name('vmSubmitLink')]
        current_url_without_paging = self.driver.current_url
        
        for link in links:
            try:
                db_vacancies = []
                link.get('link').click()
                table = self.driver.find_element_by_class_name('OKtable')
                bodies = table.find_elements_by_tag_name('tbody')
                for body in bodies:
                    try:
                        db_vacancy = { 'ts': self.ts, 'created': self.iso_time, 'category': link.get('category'), 'category_title': link.get('title')}
                        rows = body.find_elements_by_tag_name('tr')
                        for row in rows:
                            try:
                                ths = row.find_elements_by_tag_name('th')
                                tds = row.find_elements_by_tag_name('td')
                                if len(ths) == len(tds):
                                    for th, td in zip(ths,tds):
                                        th = Core.normalize2ascii(th.text)
                                        th = th[:-1] if th.endswith(':') else th
                                        td = Core.normalize2ascii(td.text)
                                        if not th or not td:
                                            continue
                                        if len(td) and len(th):
                                            db_vacancy[th] = td
                                elif len(tds) == 3:
                                    try:
                                        th = Core.normalize2ascii(tds[1].text)
                                        th = th[:-1] if th.endswith(':') else th
                                        td = Core.normalize2ascii(tds[2].text)
                                        
                                        if 'wage' in th.lower():
                                            try:
                                                number = Core.parseNumber(td)
                                                _, measurement = Core.get_decimal_measurement_unit(td)
                                                if (number and measurement):
                                                    db_vacancy[th] = { 'wage': number, 'time': measurement}
                                            except AttributeError:
                                                if len(td):
                                                    db_vacancy[th]=td
                                            except Exception,e:
                                                logger.error("error, todo")
                                                pass
                                        
                                        elif 'period' in th.lower():
                                            try:
                                                td = td.replace('from','')
                                                dt = parse(td)
                                                dt = Core.get_iso_datetime(dt)
                                            except AttributeError:
                                                if len(td):
                                                    db_vacancy[th]=td
                                            except Exception,e:
                                                logger.error("error, todo")
                                                pass
                                        else:    
                                            if not th or not td:
                                                continue
                                            if len(th) and len(td):
                                                db_vacancy[th] = td
                                            
                                    except Exception, e:
                                        pass
                                if any(db_vacancy):
                                    db_vacancies.append(db_vacancy)   
                            
                            except Exception, e:
                                logger.error("Error occured at {}, details: {}".format(self.dbName, e.message))
                                continue
                    except Exception, e:
                        logger.error("Error occured at {}, details: {}".format(self.dbName, e.message))
                        continue
                
                if any(db_vacancies):
                    db[self.dbName].insert(db_vacancies,{'ordered':False})    
                      
            except (ValueError, Exception), e:
                logger.error("Error occurred at {} while parsing the site. {}".format(self.dbName, e.message))
                continue
            
        return 0

    def close(self):
        logger.info("Successfully finished {}".format(self.webDomain))
        self.driver.close()         
        