import os
import sys
import datetime

from drugfinder.utils import DrugBankDB, Intervals, safe_unicode, get_similarity
from drugfinder.simstring import SimstringDBReader
from drugfinder import constants
import nltk
import spacy
from unidecode import unidecode
import logging
logging.basicConfig(format='%(asctime)s %(levelname)s:%(message)s',
                    filename="drugfinder-match.log",
                    encoding='utf-8',
                    level=logging.DEBUG)


class DrugFinder(object):
    """Main class of the DrugFinder module.
    """

    def __init__(self,
                 drugbank_fp,
                 overlapping_criteria="score",
                 threshold=0.7,
                 window=5,
                 similarity_name="cosine",
                 min_match_length=1,
                 verbose=False,
                 spacy_component=False,
                 umls_linking=False):
        """Instantiate DrugFinder object that is the interface through
            which text can be processed.

            Args:
                drugbank_fp (str): Path to which DrugBank files was installed
                overlapping_criteria (str, optional): Criteria used for tiebreakers: can be `score` or `length`.
                threshold (float, optional): Minimum similarity between strings. Defaults to 0.7.
                window (int, optional): Maximum amount of tokens to consider for matching. Defaults to 5.
                similarity_name (str, optional): similarity measure for string comparison. It can be `dice`, `jaccard`,
                                                    `cosine` or `overlap`. Defaults to `cosine`.
                min_match_length (int, optional): Minimum number of tokens for comparison. Defaults to 1.
                verbose (bool, optional): outputs every drug found in the text. Defaults to false.
                spacy_component (bool, optional): TODO:?? Defaults to false.
                umls_linking (bool, optional): TODO: links the drugfinder found in the text with UMLS concepts using
                                                QuickUMLS. Defaults to false.
        """
        if umls_linking:
            raise Exception("UMLS linking is not supported yet")

        self.verbose = verbose
        self.__validate_parameters(overlapping_criteria, similarity_name)
        simstring_fp = os.path.join(drugbank_fp, "drugbank-simstring.db")
        drugbank_db = os.path.join(drugbank_fp, "drugbank-db.db")

        self.valid_punctuation = constants.UNICODE_DASHES
        self.negations = constants.NEGATIONS

        self.window = window
        self.ngram_length = 3
        self.threshold = threshold
        self.min_match_length = min_match_length
        self.normalize_unicode_flag = os.path.exists(
            os.path.join(drugbank_fp, "normalize-unicode.flag")
        )
        # download stopwords if necessary
        try:
            nltk.corpus.stopwords.words()
        except LookupError:
            nltk.download("stopwords")

        # drugfinder only supports english language since DrugBank contains only english words
        self.language_flag = "ENG"
        self._stopwords = set(
            nltk.corpus.stopwords.words(constants.LANGUAGES[self.language_flag])
        )
        spacy_lang = constants.SPACY_LANGUAGE_MAP[self.language_flag]
        database_backend_fp = os.path.join(drugbank_fp, "database_backend.flag")
        if os.path.exists(database_backend_fp):
            with open(database_backend_fp) as f:
                self._database_backend = f.read().strip()
        else:
            self._database_backend = 'unqlite'

        # domain specific stopwords
        self._stopwords = self._stopwords.union(constants.DRUGBANK_SPECIFIC_STOPWORDS)
        self._info = None

        # if this is not being executed as spacy component, then it must be standalone
        if spacy_component:
            # In this case, the pipeline is external to this current class
            self.nlp = None
        else:
            try:
                self.nlp = spacy.load(spacy_lang)
            except OSError:
                msg = (
                    'Model for language "{}" is not downloaded. Please '
                    'run "python -m spacy download {}" before launching '
                    "DrugFinder"
                ).format(
                    self.language_flag,
                    constants.SPACY_LANGUAGE_MAP.get(self.language_flag, "xx"),
                )
                raise OSError(msg)

        self.simstring_db = SimstringDBReader(path=simstring_fp,
                                              similarity_name=similarity_name,
                                              threshold=threshold,
                                              filename='drug-terms.simstring')
        self.drugbank_db = DrugBankDB(path=drugbank_db, database_backend=self._database_backend)

    def get_info(self):
        """Computes a summary of the matcher options.

        Returns:
            Dict: Dictionary containing information on the DrugFinder instance.
        """
        return self.info

    @property
    def info(self):
        """Computes a summary of the matcher options.

        Returns:
            Dict: Dictionary containing information on the DrugFinder instance.
        """
        # useful for caching of responses
        if self._info is None:
            self._info = {
                "threshold": self.threshold,
                "similarity_name": self.similarity_name,
                "window": self.window,
                "ngram_length": self.ngram_length,
                "min_match_length": self.min_match_length,
                "negations": sorted(self.negations),
                "valid_punctuation": sorted(self.valid_punctuation),
            }
        return self._info

    def __validate_parameters(self, overlapping_criteria, similarity_name):
        valid_criteria = {"length", "score"}
        err_msg = (
            '"{}" is not a valid overlapping_criteria. Choose '
            "between {}".format(overlapping_criteria, ", ".join(valid_criteria))
        )
        assert overlapping_criteria in valid_criteria, err_msg
        self.overlapping_criteria = overlapping_criteria

        valid_similarities = {"dice", "jaccard", "cosine", "overlap"}
        err_msg = '"{}" is not a valid similarity name. Choose between ' "{}".format(
            similarity_name, ", ".join(valid_similarities)
        )
        assert not (valid_similarities in valid_similarities), err_msg
        self.similarity_name = similarity_name

    # functions from QuickUMLS
    @staticmethod
    def _general_grammar_check(token) -> bool:
        return token.pos_ == "ADP" or token.pos_ == "DET" or token.pos_ == "CONJ"

    @staticmethod
    def _is_valid_token(token) -> bool:
        return not (
            token.is_punct
            or token.is_space
            or DrugFinder._general_grammar_check(token)
        )

    def _is_valid_start_token(self, token) -> bool:
        return not (
            token.like_num
            or (self._is_stop_term(token) and token.lemma_ not in self.negations)
            or DrugFinder._general_grammar_check(token)
        )

    def _is_stop_term(self, token) -> bool:
        return token.text in self._stopwords

    def _is_valid_end_token(self, token) -> bool:
        return not (
            token.is_punct
            or token.is_space
            or self._is_stop_term(token)
            or DrugFinder._general_grammar_check(token)
        )

    def _is_valid_middle_token(self, token) -> bool:
        return (
            not (token.is_punct or token.is_space)
            or token.is_bracket
            or token.text in self.valid_punctuation
        )

    def _is_longer_than_min(self, span) -> bool:
        return (span.end_char - span.start_char) >= self.min_match_length

    def _make_ngrams(self, sentence) -> tuple:
        """Create ngrams from sentences equal to the size of the window
            and greater than the minimum size, excluding invalid tokens,
            determiners and stopwords

        """
        sentence_length = len(sentence)

        # do not include determiners inside a span
        skip_in_span = {token.i for token in sentence if token.pos_ == "DET"}

        # invalidate a span if it includes any on these symbols
        invalid_mid_tokens = {
            token.i for token in sentence if not self._is_valid_middle_token(token)
        }

        for i in range(sentence_length):
            token = sentence[i]

            if not self._is_valid_token(token):
                continue

            # do not consider this token by itself if it is
            # a number or a stopword.
            if self._is_valid_start_token(token):
                compensate = False
            else:
                compensate = True

            span_end = min(sentence_length, i + self.window) + 1

            # we take a shortcut if the token is the last one
            # in the sentence
            if (
                i + 1 == sentence_length
                and self._is_valid_end_token(token)  # it's the last token
                and len(token)  # it's a valid end token
                >= self.min_match_length  # it's of minimum length
            ):
                yield token.idx, token.idx + len(token), token.text

            for j in range(i + 1, span_end):
                if compensate:
                    compensate = False
                    continue

                if sentence[j - 1] in invalid_mid_tokens:
                    break

                if not self._is_valid_end_token(sentence[j - 1]):
                    continue

                span = sentence[i:j]

                if not self._is_longer_than_min(span):
                    continue

                yield (
                    span.start_char,
                    span.end_char,
                    "".join(
                        token.text_with_ws
                        for token in span
                        if token.i not in skip_in_span
                    ).strip(),
                )

    def _make_token_sequences(self, parsed):
        """ Creates token sequences from sentences the size of the window
            and that are larger than the minimum size.
            It is used when the ignore_syntax parameter is true.
        """
        for i in range(len(parsed)):
            for j in range(i + 1, min(i + self.window, len(parsed)) + 1):
                span = parsed[i:j]

                if not self._is_longer_than_min(span):
                    continue

                yield span.start_char, span.end_char, span.text

    def _get_all_matches(self, ngrams):
        matches = []
        for start, end, ngram in ngrams:
            ngram_normalized = ngram

            if self.normalize_unicode_flag:
                ngram_normalized = unidecode(ngram_normalized)

            last_drug_id = None
            candidate_ngrams = list(set(self.simstring_db.get(ngram_normalized)))

            ngram_matches = []

            for match in candidate_ngrams:
                item = self.drugbank_db.get(match)
                if item is None:
                    continue

                drugbank_id, data = item

                match_similarity = get_similarity(
                    x=ngram_normalized,
                    y=match,
                    n=self.ngram_length,
                    similarity_name=self.similarity_name,
                )

                if match_similarity == 0:
                    continue

                if last_drug_id is not None and last_drug_id == drugbank_id:
                    if match_similarity > ngram_matches[-1]["similarity"]:
                        ngram_matches.pop(-1)
                    else:
                        continue

                last_drug_id = drugbank_id

                ngram_matches.append(
                    {
                        "start": start,
                        "end": end,
                        "ngram": ngram,
                        "term": safe_unicode(match),
                        "drugbank_id": drugbank_id,
                        "data": data,
                        "similarity": match_similarity,
                    }
                )

            if len(ngram_matches) > 0:
                matches.append(
                    sorted(
                        ngram_matches,
                        key=lambda m: m["similarity"],
                        reverse=True,
                    )
                )
        return matches

    @staticmethod
    def _select_score(match) -> tuple:
        return match[0]["similarity"], (match[0]["end"] - match[0]["start"])

    @staticmethod
    def _select_longest(match) -> tuple:
        return (match[0]["end"] - match[0]["start"]), match[0]["similarity"]

    def _select_terms(self, matches):
        sort_func = (
            self._select_longest
            if self.overlapping_criteria == "length"
            else self._select_score
        )
        matches = sorted(matches, key=sort_func, reverse=True)
        intervals = Intervals()
        final_matches_subset = []
        for match in matches:
            match_interval = (match[0]["start"], match[0]["end"])
            if match_interval not in intervals:
                final_matches_subset.append(match)
                intervals.append(match_interval)

        return final_matches_subset

    def _print_verbose_status(self, parsed, matches):
        logging.info("{:,} extracted from {:,} tokens".format(
                sum(len(match_group) for match_group in matches),
                len(parsed),
        ))
        if not self.verbose:
            return False

        print(
            "[{}] {:,} extracted from {:,} tokens".format(
                datetime.datetime.now().isoformat(),
                sum(len(match_group) for match_group in matches),
                len(parsed),
            ),
            file=sys.stderr,
        )
        return True

    def match(self, text, best_match=True, ignore_syntax=False):
        parsed = self.nlp("{}".format(text))

        # pass in parsed spacy doc to get concept matches
        return self._match(parsed, best_match, ignore_syntax)

    def _match(self, doc, best_match=True, ignore_syntax=False):

        if ignore_syntax:
            ngrams = self._make_token_sequences(doc)
        else:
            ngrams = self._make_ngrams(doc)

        matches = self._get_all_matches(ngrams)

        if best_match:
            matches = self._select_terms(matches)

        self._print_verbose_status(doc, matches)

        return matches
