__all__ = ['webcrawler', 'core']
import logging
logger = logging.getLogger('sjoern-scrapper')
import mongo_service
mongo_service.init()