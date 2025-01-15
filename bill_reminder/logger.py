import logging

# Configure the logger
logging.basicConfig(
    level=logging.DEBUG,  # Set the logging level
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',  # Log message format
    handlers=[
        logging.StreamHandler()  # Log to the console
    ]
)

# Create a logger object
logger = logging.getLogger(__name__)