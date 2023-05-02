from __future__ import division, print_function, unicode_literals

import unicodedata
import argparse
import logging
import os
import pickle

import numpy

from quickumls.toolbox import make_ngrams

try:
    import unqlite
    UNQLITE_AVAILABLE = True
except ImportError:
    import leveldb
    UNQLITE_AVAILABLE = False


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "drugbank_filepath",
        help="DrugBank dataset filepath (e.g.: `/home/drugbank/full_database.xml`)"
    )
    ap.add_argument(
        "drugbank_schema_filepath",
        help="DrugBank XML Schema filepath (e.g.: `/home/drugbank/drugbank.xsd`)"
    )
    ap.add_argument(
        "destination_path",
        help="Location where the Scriba files are installed"
    )
    ap.add_argument(
        '-U',
        '--normalize-unicode',
        action='store_true',
        help="Normalize unicode strings to their closes ASCII representation"
    )
    ap.add_argument(
        "-d",
        "--database-backend",
        choices=("leveldb", "unqlite"),
        default="unqlite",
        help="Key-Value database used to store drugbank-ids and drug data",
    )
    opts = ap.parse_args()
    return opts


def mkdir(path):
    try:
        os.makedirs(path)
        return True
    except OSError:
        return False


def safe_unicode(s):
    return "{}".format(unicodedata.normalize("NFKD", s))


def db_key_encode(term):
    return term.encode("utf-8")


class DrugBankDB(object):
    def __init__(self, path, database_backend="unqlite"):
        if not (os.path.exists(path) or os.path.isdir(path)):
            err_msg = '"{}" is not a valid directory'.format(path)
            raise IOError(err_msg)

        if database_backend == "unqlite":
            assert UNQLITE_AVAILABLE, (
                "You selected unqlite as database backend, but it is not "
                "installed. Please install it via `pip install unqlite`"
            )
            self.drugbank_db = unqlite.UnQLite(os.path.join(path, "drugbank_id.unqlite"))
            self.drugbank_db_put = self.drugbank_db.store
            self.drugbank_db_get = self.drugbank_db.fetch
            self.drugbank_data_db = unqlite.UnQLite(os.path.join(path, "drugbank_data.unqlite"))
            self.drugbank_data_db_put = self.drugbank_data_db.store
            self.drugbank_data_db_get = self.drugbank_data_db.fetch
        elif database_backend == "leveldb":
            self.drugbank_db = leveldb.LevelDB(os.path.join(path, "drugbank_id.leveldb"))
            self.drugbank_db_put = self.drugbank_db.Put
            self.drugbank_db_get = self.drugbank_db.Get
            self.drugbank_data_db = leveldb.LevelDB(os.path.join(path, "drugbank_data.leveldb"))
            self.drugbank_data_db_put = self.drugbank_data_db.Put
            self.drugbank_data_db_get = self.drugbank_data_db.Get
        else:
            raise ValueError(f"database_backend {database_backend} not recognized")

    def has_term(self, term):
        term = safe_unicode(term)
        try:
            self.drugbank_db_get(db_key_encode(term))
            return True
        except KeyError:
            return

    @staticmethod
    def _validate(drug):
        keys = ['name', 'drugbank_id']
        if not all([k in list(drug.keys()) for k in keys]):
            raise ValueError("The drug item is not valid to be inserted.")
        return True

    def insert(self, drug):
        try:
            DrugBankDB._validate(drug)
        except ValueError as err:
            logging.debug(err)
            logging.debug("Drug data: %s", list(drug.keys()))
            return

        name = safe_unicode(drug['name'].lower())
        synonyms = [safe_unicode(synonym.lower())
                    for synonym in drug['synonyms'].split(',') if len(synonym) > 0]
        products = [safe_unicode(product.lower())
                    for product in drug['products'].split(',') if len(product) > 0]
        drugbank_id = safe_unicode(drug.pop('drugbank_id'))

        self.drugbank_db_put(name, pickle.dumps(drugbank_id))
        if len(synonyms) > 0:
            [self.drugbank_db_put(synonym, pickle.dumps(drugbank_id)) for synonym in synonyms if len(synonym) > 0]
        if len(products) > 0:
            [self.drugbank_db_put(product, pickle.dumps(drugbank_id)) for product in products if len(product) > 0]

        try:
            self.drugbank_data_db_get(db_key_encode(drugbank_id))
        except KeyError:
            self.drugbank_data_db_put(db_key_encode(drugbank_id), pickle.dumps(drug))

    def get(self, term):
        term = safe_unicode(term.lower())
        try:
            drugbank_id = pickle.loads(self.drugbank_db_get(db_key_encode(term)))
        except KeyError:
            return None

        return drugbank_id, pickle.loads(self.drugbank_data_db_get(db_key_encode(drugbank_id)))


class Intervals(object):
    def __init__(self):
        self.intervals = []

    @staticmethod
    def _is_overlapping_intervals(a, b):
        if b[0] < a[1] and b[1] > a[0]:
            return True
        elif a[0] < b[1] and a[1] > b[0]:
            return True
        else:
            return False

    def __contains__(self, interval):
        return any(
            self._is_overlapping_intervals(interval, other) for other in self.intervals
        )

    def append(self, interval):
        self.intervals.append(interval)


def get_similarity(x, y, n, similarity_name):
    if len(x) == 0 or len(y) == 0:
        # we define similarity between two strings
        # to be 0 if any of the two is empty.
        return 0.0

    x, y = set(make_ngrams(x, n)), set(make_ngrams(y, n))
    intersection = len(x.intersection(y))

    if similarity_name == "dice":
        return 2 * intersection / (len(x) + len(y))
    elif similarity_name == "jaccard":
        return intersection / (len(x) + len(y) - intersection)
    elif similarity_name == "cosine":
        return intersection / numpy.sqrt(len(x) * len(y))
    elif similarity_name == "overlap":
        return intersection
    else:
        msg = "Similarity {} not recognized".format(similarity_name)
        raise TypeError(msg)
