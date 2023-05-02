from __future__ import division, print_function, unicode_literals

import os

from quickumls_simstring import simstring
from drugfinder.utils import safe_unicode


class SimstringDBWriter(object):
    def __init__(self, path, filename="umls-terms.simstring"):

        if not (os.path.exists(path)) or not (os.path.isdir(path)):
            err_msg = '"{}" does not exists or it is not a directory.'.format(path)
            raise IOError(err_msg)
        else:
            try:
                os.makedirs(path)
            except OSError:
                pass

        self.db = simstring.writer(
            os.path.join(path, filename),
            3,
            False,
            True,
        )

    def insert(self, term):
        term = safe_unicode(term)
        self.db.insert(term)


class SimstringDBReader(object):
    def __init__(self, path, similarity_name, threshold, filename="umls-terms.simstring"):
        if not (os.path.exists(path)) or not (os.path.isdir(path)):
            err_msg = '"{}" does not exists or it is not a directory.'.format(path)
            raise IOError(err_msg)

        self.db = simstring.reader(
            os.path.join(path, filename)
        )
        self.db.measure = getattr(simstring, similarity_name)
        self.db.threshold = threshold

    def get(self, term):
        term = safe_unicode(term.lower())
        return self.db.retrieve(term)
