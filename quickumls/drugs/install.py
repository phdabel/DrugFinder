import os
import sys
import argparse
import shutil
import time
import xmlschema
import tqdm
import logging
from quickumls.toolbox import mkdir, SimstringDBWriter, DrugBankDB
try:
    from unidecode import unidecode
except ImportError:
    import unidecode
logging.basicConfig(format='%(asctime)s %(levelname)s:%(message)s',
                    filename="drugbank-installation.log",
                    encoding='utf-8',
                    level=logging.DEBUG)


def get_drugbank_iterator(path, schema):

    # parse synonyms of the drug element
    def get_synonyms(_data):
        return {'synonyms': ';'.join([j for k, v in _data[list(_data.keys())[0]][0][1] if k == 'synonyms' and v is not None for i, j in v if i == 'synonym'])}

    # parse product names of the drug element
    def get_products(_data):
        return {'products': ';'.join(set([y for k, v in _data[list(_data.keys())[0]][0][1] if k == 'products' and v is not None for i, j in v if i == 'product' for x, y in j if x == 'name']))}

    # parse basic data of the drug element
    def get_data(_data):
        valid_keys = ['name', 'description', 'state', 'indication', 'pharmacodynamics']
        return {k: v for k, v in _data[list(_data.keys())[0]][0][1] if k in valid_keys}

    # retrieves a dictionary to be saved in the simstring-db
    def get_dict(_data):
        return {**get_synonyms(_data), **get_products(_data), **get_data(_data), 'drugbank_id': [v[0] for k, v in _data[list(_data.keys())[0]][0][1] if k == 'drugbank-id' and v[1] == 'primary'][0]}

    # cuts off the namespace of a element's tag
    def get_tag(tag): return tag[len('{%s}' % schema.namespaces['']):]

    # pops out children elements to assign to the parent element
    def get_element_children(_data, idx, _element):
        tmp = list()
        if len(list(_element)) > len(_data[idx]):
            logging.debug("Counting error: (%s) > (%s)" % (str(len(list(_element))), str(len(_data[idx]))))
            logging.debug("%s", _element)
            logging.debug("%s", tmp)

        for _ in list(_element):
            tmp.append(_data[idx].pop())
        _data[idx].append((get_tag(_element.tag), tmp))

    n = 0
    data = dict()
    data[0] = list()
    for element in xmlschema.XMLResource(path, lazy=True).iter():
        if get_tag(element.tag) == 'drug' and 'type' in element.attrib.keys():
            get_element_children(data, n, element)
            # yield data here
            yield get_dict(data)
            data.pop(n)
            n += 1
            data[n] = list()
        elif get_tag(element.tag) == 'drugbank-id' and 'primary' in element.attrib.keys():
            data[n].append((get_tag(element.tag), (element.text, 'primary')))
        elif get_tag(element.tag) == 'drugbank':
            continue
        else:
            if len(list(element)) == 0:
                data[n].append((get_tag(element.tag), element.text))
            else:
                get_element_children(data, n, element)


def extract_from_drugbank(
        drugbank_filepath,
        drugbank_schema_filepath,
        opts
):
    start = time.time()
    logging.info("Loading drug data...")
    print("Loading drug data...", end=" ")
    schema = xmlschema.XMLSchema(drugbank_schema_filepath)
    drugbank_iterator = get_drugbank_iterator(path=drugbank_filepath, schema=schema)
    for content in tqdm.tqdm(drugbank_iterator):
        if opts.normalize_unicode:
            content = dict(zip(content.keys(), list(map(unidecode, content.values()))))

        yield content

    logging.info("Done in {:.2f} s".format(time.time() - start))
    print("Done in {:.2f} s".format(time.time() - start))


def parse_and_encode_ngrams(
    drugbank_iterator,
    simstring_dir,
    drugbank_db_dir,
    database_backend
):
    # create destination directories for simstring dataset
    mkdir(simstring_dir)
    mkdir(drugbank_db_dir)

    ss_db = SimstringDBWriter(simstring_dir, filename="drug-terms.simstring")
    drugbank_db = DrugBankDB(drugbank_db_dir, database_backend=database_backend)

    for content in drugbank_iterator:
        ss_db.insert(content['name'].lower())
        if len(content['synonyms']) > 0:
            [ss_db.insert(synonym.lower()) for synonym in content['synonyms'].split(';')]
        if len(content['products']) > 0:
            [ss_db.insert(product.lower()) for product in content['products'].split(';')]
        drugbank_db.insert(content)


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


def main():
    opts = parse_args()

    if not os.path.exists(opts.destination_path):
        msg = 'Directory "{}" does not exists; should I create it? [y/N] ' "".format(
            opts.destination_path
        )
        create = input(msg).lower().strip() == 'y'

        if create:
            os.makedirs(opts.destination_path)
        else:
            print("Aborting")
            exit(1)

    if len(os.listdir(opts.destination_path)) > 0:
        msg = 'Directory "{}" is not empty; should I empty it? [y/N] ' "".format(
            opts.destination_path
        )
        empty = input(msg).lower().strip() == "y"
        if empty:
            shutil.rmtree(opts.destination_path)
            os.mkdir(opts.destination_path)
        else:
            print("Aborting")
            exit(1)

    if opts.normalize_unicode:
        try:
            unidecode
        except NameError:
            err = (
                "`unidecode` is needed for unicode normalization"
                "please install it via the `[sudo] pip install "
                "unidecode` command."
            )
            print(err, file=sys.stderr)
            exit(1)

        flag_fp = os.path.join(opts.destination_path, "normalize-unicode.flag")
        open(flag_fp, "w").close()

    flag_fp = os.path.join(opts.destination_path, "database_backend.flag")
    with open(flag_fp, "w") as f:
        f.write(opts.database_backend)

    drugbank_path = os.path.join(opts.drugbank_filepath)
    drugbank_schema = os.path.join(opts.drugbank_schema_filepath)
    simstring_dir = os.path.join(opts.destination_path, "drugbank-simstring.db")
    drugbank_db_dir = os.path.join(opts.destination_path, "drugbank-db.db")

    drugbank_iterator = extract_from_drugbank(drugbank_path, drugbank_schema, opts)
    parse_and_encode_ngrams(
        drugbank_iterator,
        simstring_dir,
        drugbank_db_dir,
        database_backend=opts.database_backend
    )


if __name__ == "__main__":
    main()
