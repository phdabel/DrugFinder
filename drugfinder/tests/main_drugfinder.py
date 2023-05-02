from drugfinder.core import DrugFinder
import os
from pathlib import Path
from pprint import pprint

drugbank_data = os.environ['DRUGBANK_DATA'] if 'DRUGBANK_DATA' in os.environ else os.path.join(Path.home(), 'drugbank_data')
matcher = DrugFinder(drugbank_fp=drugbank_data, threshold=0.9, window=3)
print(matcher.get_info())

matches = matcher.match('Ivermectin for Severe COVID-19 Management')
pprint(matches)
