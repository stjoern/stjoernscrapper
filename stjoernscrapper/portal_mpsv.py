'''
Created on Sep 18, 2017

@author: mmullero
'''
from stjoernscrapper.core import Core, autolog, errorlog
from stjoernscrapper.webcrawler import WebCrawler
import re
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from dateutil.parser import parse
from time import sleep

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
        autolog(self.logger)
        # e.g. /c300101000-pekarna-a-cukrarna
        link = link.split('?orderBy',1)[0]
        m = re.search('.*[0-9]+-(?P<sortiment>.*).*$', link)
        print(link)
        sortiment = m.group('sortiment')
        return sortiment.replace('-',' ')
    
    def _getPager(self):
        autolog(self.logger)
        try:
            h3 = self.driver.find_element_by_xpath("//*[starts-with(text(), 'Page')]")
            if h3:
                text = h3.find_element_by_xpath("//td[@class='OKbasic2']")
                if not text:
                    raise ValueError()
                text = text.text
                print(text)
                
                # Page 1 of 32:
                m = re.search('Page\s?(?P<cur_page>[0-9]+)\s?\w*\s?(?P<max_page>[0-9]+).*', text)
                if not m:
                    raise ValueError()
             
                cur_page = int(m.group('cur_page'))
                max_page = int(m.group('max_page'))
                
                return cur_page, max_page
                
        except ValueError:
            errorlog(self.logger, "Cannot convert current page and max. page.")
            return 1, 1
        
    
    def parse(self):
        autolog(self.logger)
        try:
            WebCrawler.parse(self)
            
            links = [{'category': Core.normalize2ascii(link.text), 'title': Core.normalize2ascii(link.get_attribute('title')), 'link': link} for link in self.driver.find_elements_by_class_name('vmSubmitLink')]
            
            for index, link in enumerate(links):
                try:
                    if index != 0:
                        self.driver.find_element(By.XPATH, "//a[@onclick='showForm()']").click()
                        sleep(15)
                    ilink = link.get('title')
                    link = self.driver.find_element(By.XPATH, "//a[contains(@title, "+ '\''+ ilink + "')]")
                    link.click()
                    
                    self.logger.info("Crawling {} -> {}, category: {}".format(self.webDomain, link.get('link'), link.get('category')))
                    
                    while True:
                        #table = self.driver.find_element_by_class_name('OKtable')
                        bodies = self.driver.find_elements_by_tag_name('tbody')
                        db_vacancies = []
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
                                                        _, measurement = Core.get_decimal_measurement_unit_from(td)
                                                        if (number and measurement):
                                                            db_vacancy[th] = { 'wage': number, 'time': measurement}
                                                    except AttributeError:
                                                        if len(td):
                                                            db_vacancy[th]=td
                                                    except Exception as e:
                                                        errorlog(self.logger, e)
                                                        continue
                                                
                                                elif 'period' in th.lower():
                                                    try:
                                                        td = td.replace('from','')
                                                        dt = parse(td)
                                                        
                                                        if dt:
                                                            db_vacancy[th]=td
                                                    except ValueError:
                                                        if len(td):
                                                            db_vacancy[th]=td
                                                    except Exception as e:
                                                        errorlog(self.logger, e)
                                                        continue
                                                else:    
                                                    if not th or not td:
                                                        continue
                                                    if len(th) and len(td):
                                                        db_vacancy[th] = td
                                                    
                                            except Exception as e:
                                                errorlog(self.logger, e)
                                                pass
                                          
                                    
                                    except (Exception, NoSuchElementException) as e:
                                        errorlog(self.logger, e)
                                        continue
                                
                                if any(db_vacancy):
                                    if 'Demanded occupation' in db_vacancy:
                                        db_vacancies.append(db_vacancy)    
                                    
                            except (Exception, NoSuchElementException) as e:
                                errorlog(self.logger, e)
                                continue
                        
                        if any(db_vacancies):
                            self.logger.debug("Inserting records to {}".format(self.dbName))
                            self.db[self.dbName].insert(db_vacancies,{'ordered':False})    
                            
                        # click on next
                        start_page, end_page = self._getPager()
                        if start_page != end_page:
                            next = self.driver.find_element_by_link_text("Next")
                            if next:
                                next.click()
                           # self.driver.find_element(By.XPATH, "//a[@onclick='showForm()']").click()
                                sleep(15)
                        else:
                            break
                          
                except (ValueError, Exception) as e:
                    errorlog(self.logger, e)
                    continue
                
        except Exception as e:
            errorlog(self.logger, e)    
        finally:
            self.close()
      
        