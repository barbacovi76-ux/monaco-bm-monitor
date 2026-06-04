import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from monitor import verificar_e_alertar
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
verificar_e_alertar()
