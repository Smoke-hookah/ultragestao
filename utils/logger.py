import logging
import sys
from config import LOG_FILE, LOG_LEVEL

# Configurar logging
logger = logging.getLogger(__name__)
logger.setLevel(getattr(logging, LOG_LEVEL))

# Handler para arquivo
file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
file_handler.setLevel(getattr(logging, LOG_LEVEL))

console_handler = None
if not getattr(sys, 'frozen', False):
    # Handler para console (evita problemas de encoding no executável)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, LOG_LEVEL))

# Formato
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
file_handler.setFormatter(formatter)
if console_handler is not None:
    console_handler.setFormatter(formatter)

# Adicionar handlers
logger.addHandler(file_handler)
if console_handler is not None:
    logger.addHandler(console_handler)
