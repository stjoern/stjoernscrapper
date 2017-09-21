__all__ = ['webcrawler', 'core', 'config', 'nakup_itesco', 'rohlik', 'portal_mpsv', 'sreality']
import logging
logger = logging.getLogger('sjoern-scrapper')
import mongo_service
mongo_service.init()