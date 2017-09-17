__all__ = ['webcrawler', 'core', 'config', 'nakup_itesco', 'rohlik']
import logging
logger = logging.getLogger('sjoern-scrapper')
import mongo_service
mongo_service.init()