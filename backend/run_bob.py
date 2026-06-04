import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from monitor import rodar_agente_automatico
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
rodar_agente_automatico()
