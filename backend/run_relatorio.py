import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from monitor import enviar_relatorio_segunda
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
enviar_relatorio_segunda()
