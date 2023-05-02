import os
from pathlib import Path
from drugfinder.simstring import SimstringDBReader
from drugfinder.utils import DrugBankDB
from pprint import pprint

drugbank_data = os.environ['DRUGBANK_DATA'] if 'DRUGBANK_DATA' in os.environ else os.path.join(Path.home(), 'drugbank_data')
simstring_dir = os.path.join(drugbank_data, "drugbank-simstring.db")
drugbank_dir = os.path.join(drugbank_data, "drugbank-db.db")
drugbank_db = DrugBankDB(drugbank_dir)

simstring_db = SimstringDBReader(simstring_dir,
                                  similarity_name='cosine',
                                  threshold=0.9,
                                  filename="drug-terms.simstring")
terms = simstring_db.get('stromectol')

for term in terms:
    drugbank_id, data = drugbank_db.get(term)
    print(drugbank_id, data)
