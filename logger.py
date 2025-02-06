import logging

class Logger:
    def __init__(self, name):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        # Adding square brackets around the timestamp
        formatter = logging.Formatter('[%(asctime)s] %(levelname)s %(name)s %(message)s',
                                      datefmt='%d/%b/%Y:%H:%M:%S')
        
        # Stream handler to output logs to the console
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        
        # Adding the handler to the logger
        self.logger.addHandler(stream_handler)
    
    def info(self, message):
        self.logger.info(message)
    
    def error(self, message):
        self.logger.error(message)
    
    def exception(self, message):
        self.logger.exception(message)
