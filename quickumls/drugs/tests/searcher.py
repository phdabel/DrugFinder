import os
from pathlib import Path
from unittest import TestCase, main
from quickumls.toolbox import SimstringDBReader, DrugBankDB


class TestSearch(TestCase):

    def setUp(self):
        drugbank_data = os.environ['DRUGBANK_DATA'] if 'DRUGBANK_DATA' in os.environ else os.path.join(Path.home(), 'drugbank_data')
        self.simstring_dir = os.path.join(drugbank_data, "drugbank-simstring.db")
        drugbank_dir = os.path.join(drugbank_data, "drugbank-db.db")
        self.drugbank_db = DrugBankDB(drugbank_dir)

    def test_cosine_search(self):
        simstring_db = SimstringDBReader(self.simstring_dir,
                                              similarity_name='cosine',
                                              threshold=0.7,
                                              filename="drug-terms.simstring")
        self.assertEqual(simstring_db.get('lepirudi'), ('lepirudin',))
        self.assertEqual(simstring_db.get('refludan'), ('refludan',))
        self.assertNotEqual(simstring_db.get('hirudin'), ('hirudin variant-1',))
        self.assertEqual(simstring_db.get('ritalin'), ('ritalin',
                                                       'ritalin sr',
                                                       'ritalin la',
                                                       'ritalin-sr',
                                                       'ritalin 10mg',
                                                       'ritalin 20mg'))
        self.assertEqual(simstring_db.get('lisdexamfetamine'), ('amfetamine',
                                                                'dexamfetamine',
                                                                'dexamfetamina',
                                                                'dexamfetaminum',
                                                                'lisdexamfetamine',
                                                                'lisdexamfetamine'))
        self.assertEqual(simstring_db.get('Ivermectin'), ('ivermectin',
                                                          'ivermectin',
                                                          'ivermectin',
                                                          'ivermectine',
                                                          'ivermectina',
                                                          'ivermectinum'))

    def test_jaccard_search(self):
        simstring_db = SimstringDBReader(self.simstring_dir,
                                         similarity_name='jaccard',
                                         threshold=0.7,
                                         filename="drug-terms.simstring")
        self.assertEqual(simstring_db.get('lepirudin'), ('lepirudin',))
        self.assertEqual(simstring_db.get('refludan'), ('refludan',))
        self.assertNotEqual(simstring_db.get('hirudin'), ('hirudin variant-1',))
        self.assertEqual(simstring_db.get('ritalin'), ('ritalin', ))
        self.assertEqual(simstring_db.get('lisdexamfetamine dimesylate'), ())
        self.assertEqual(simstring_db.get('Ivermectin'), ('ivermectin',
                                                          'ivermectin',
                                                          'ivermectin',
                                                          'ivermectine',
                                                          'ivermectina'))

    def test_get_drug_data(self):
        self.assertEqual(self.drugbank_db.get('Refludan')[0], 'DB00001')
        self.assertEqual(self.drugbank_db.get('Ritalin')[0], 'DB00422')
        self.assertEqual(self.drugbank_db.get('Methylphenidate')[0], 'DB00422')


if __name__ == '__main__':
    main()
