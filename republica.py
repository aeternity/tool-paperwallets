#!/usr/bin/env python3
import argparse
import json
import logging

import os
import requests
import sys

import qrcode
import random
import shutil
import nanoid
import sqlite3

import datetime

from queue import Queue
import threading
import math

# pdf
from reportlab.pdfgen import canvas
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from PyPDF2 import PdfFileWriter, PdfFileReader


# this is just a hack to get this example to import a parent folder:
print()
sys.path.append(
    os.path.abspath(
        os.path.join(__file__, '..', '..', 'aepp-sdk-python')))

from aeternity import Config
from aeternity.signing import KeyPair
from aeternity.epoch import EpochClient
from aeternity.aens import AEName
from aeternity.exceptions import AException

DEFAULT_TARGET_FOLDER = 'wallets'

STATUS_CREATED = 10
STATUS_FILLED = 20
STATUS_CLAIMED = 30


FILE_QR_BEERAPP_NAME = 'qr_beerapp.png'
FILE_QR_PUBKEY_NAME = 'qr_pubkey.png'
FILE_PDF_FRONT_NAME = 'front.pdf'
FILE_PDF_BACK_NAME = 'back.pdf'
FILE_WALLET_NAME = 'wallet.json'


class KuttCli(object):

    def __init__(self, api_key, base_url='https://kutt.it'):
        """initialzie the client with the API key"""
        self.api_key = api_key
        self.kuttit_baseurl = base_url
        self.headers = {'X-API-Key': self.api_key}
        pass

    def shorten(self, original_url):
        """returns a short url string"""
        data = {'target': original_url}
        endp = '%s/api/url/submit' % self.kuttit_baseurl
        r = requests.post(endp, data=data, headers=self.headers)
        # see https://github.com/thedevs-network/kutt#types
        url_object = r.json()
        if r.status_code != 200:
            print(url_object)
            raise Exception("error from the shortener service")
        return url_object['id'], url_object['shortUrl']

    def delete(self, short_id):
        endp = '%s/api/url/deleteurl' % self.kuttit_baseurl
        print(f'remove {short_id}')
        requests.post(endp, headers=self.headers, data={'id': short_id})

    def purge(self):
        has_urls = True
        while has_urls:
            endp = '%s/api/url/geturls' % self.kuttit_baseurl
            r = requests.get(endp, headers=self.headers)
            urls = r.json()
            print('REMOVING %d URLS' % urls['countAll'])
            # loop trought the urls and delete them
            endp = '%s/api/url/deleteurl' % self.kuttit_baseurl
            for u in urls['list']:
                print('remove [%s] %s ' % (u['id'], u['shortUrl']))
                requests.post(endp, headers=self.headers, data={'id': u['id']})
            if urls['countAll'] <= 0:
                has_urls = False


class Namer(object):
    """generate a name for a key"""

    def __init__(self):
        self.animals = []
        self.adjectives = []
        with open('gfycat/adjectives.json') as fp:
            self.adjectives = json.load(fp)
        with open('gfycat/animals.json') as fp:
            self.animals = json.load(fp)
        with open('gfycat/cities.json') as fp:
            self.cities = json.load(fp)
            self.cities_len = len(self.cities)

    def gen_name(self, seed, sep='-'):
        """generate the deterministic name for a public key
        :param seed: the wallet address
        :param sep: word separator for domain
        :param tld: the tld for the domain
        :return:  the wallet name 
        """
        random.seed(a=seed, version=2)
        a1, a2 = random.sample(self.adjectives, 2)
        random.seed(a=seed, version=2)
        a3 = random.choice(self.animals)
        return f'{a1}{sep}{a2}{sep}{a3}'

    def get_city(self, index):
        """return the city name at index (lowercase)"""
        if index < 0 or index >= self.cities_len:
            raise Exception(f"index renage is 0-{self.cities_len-1}")
        return self.cities[index].lower()


class Printer(object):
    """class repsonisible to do the pdf printing"""

    def __init__(self, pdf_front_template_path, pdf_back_template_path):
        # template paths
        #
        self.pdf_front_template_path = pdf_front_template_path
        #
        self.pdf_back_template_path = pdf_back_template_path

        # pdf fonts
        pdfmetrics.registerFont(
            TTFont('Roboto', 'fonts/RobotoMono-Regular.ttf')
        )

    

    def qr_img(self, output_path, data):
        """generate a qr code from a path"""
        qr_cli = qrcode.QRCode(
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            border=0,
            #version=None,
            #box_size=10,
        )
        qr_cli.clear()
        qr_cli.add_data(data)
        qr_cli.make(fit=True)
        img = qr_cli.make_image(fill_color="black", back_color="white")
        img.save(output_path)

    def pdf(self,
            work_dir_path,
            address='',
            name='',
            url=''):
        """generates the pdf with the wallet qr, name and address"""

        # make the target directory
        if not os.path.exists(work_dir_path):
            os.makedirs(work_dir_path, exist_ok=True)

        print(f'generate pdf at {work_dir_path}')

        qr_front_path = os.path.join(work_dir_path, FILE_QR_BEERAPP_NAME)
        qr_back_path = os.path.join(work_dir_path, FILE_QR_PUBKEY_NAME)
        pdf_front_path = os.path.join(work_dir_path, FILE_PDF_FRONT_NAME)
        pdf_back_path = os.path.join(work_dir_path, FILE_PDF_BACK_NAME)

        # generate qr code for beer app
        self.qr_img(qr_front_path, url)
        # generate qr code for public key
        self.qr_img(qr_back_path, address)

        # first front
        watermark_file = os.path.join(work_dir_path, 'watermark_front.pdf')
        # Create the watermark from an image
        c = canvas.Canvas(watermark_file)
        # Draw the image at x, y. I positioned the x,y to be where i like here
        # x17  w126
        x = 304
        size = 102
        c.drawImage(qr_front_path, x, 170, size, size, anchor='sw')
        # Add some custom text for good measure
        # c.setFont("Suisse Int’l Mono", 10)
        c.setFont("Roboto", 8)
        c.drawString(x, 156, url.replace(
            'https://', '').replace('http://', ''))
        c.save()
        # Get the watermark file you just created
        watermark = PdfFileReader(open(watermark_file, "rb"))
        # Get our files ready
        output_file = PdfFileWriter()
        input_file = PdfFileReader(open(self.pdf_front_template_path, "rb"))

        input_page = input_file.getPage(0)
        input_page.mergePage(watermark.getPage(0))
        # add page from input file to output document
        output_file.addPage(input_page)

        # finally, write "output" to document-output.pdf
        with open(pdf_front_path, "wb") as outputStream:
            output_file.write(outputStream)
        # cleanup
        os.remove(watermark_file)
        os.remove(qr_front_path)

        # now do the back
        watermark_file = os.path.join(work_dir_path, 'watermark_back.pdf')
        # Create the watermark from an image
        c = canvas.Canvas(watermark_file)
        # Draw the image at x, y. I positioned the x,y to be where i like here
        # x17  w126
        x = 31
        size = 102
        c.drawImage(qr_back_path, x, 155, size, size, anchor='sw')
        # Add some custom text for good measure
        # c.setFont("Suisse Int’l Mono", 10)
        c.setFont("Roboto", 8)
        c.drawString(x, 52, name)
        c.drawString(x, 141, address[0:21])
        c.drawString(x, 128, address[21:42])
        c.drawString(x, 116, address[42:63])
        c.drawString(x, 102, address[63:84])
        c.drawString(x, 90, address[84:])
        c.save()
        # Get the watermark file you just created
        watermark = PdfFileReader(open(watermark_file, "rb"))
        # Get our files ready
        output_file = PdfFileWriter()
        input_file = PdfFileReader(open(self.pdf_back_template_path, "rb"))

        input_page = input_file.getPage(0)
        input_page.mergePage(watermark.getPage(0))
        # add page from input file to output document
        output_file.addPage(input_page)

        # finally, write "output" to document-output.pdf
        with open(pdf_back_path, "wb") as outputStream:
            output_file.write(outputStream)

        # remove what is not useful
        # cleanup
        os.remove(watermark_file)
        os.remove(qr_back_path)


class Windex(object):

    def __init__(self, db_path='republica_wallets.sqlite'):
        self.db = sqlite3.connect(db_path)

        def dict_factory(cursor, row):
            d = {}
            for idx, col in enumerate(cursor.description):
                d[col[0]] = row[idx]
            return d

        self.db.row_factory = dict_factory

    def db_update(self, q, p):
        c = self.db.cursor()
        # Insert a row of data
        c.execute(q, p)
        # Save (commit) the changes
        self.db.commit()
        c.close()

    # statuses are
    # - created (just the private/public keys)
    # - filled (the account as been filled)
    # - named (the account name has been registered)
    # -
    def insert_wallet(self, private, public, name=None, path=None, short_url=None, long_url=None, id=None):
        """"
        Insert a wallet inside a sqlite database

        :param private: the private key hex encoded
        :param public: the public address base58 encoded
        :param name: the wallet name without extension
        :param path: the relative path of the wallet fodder
        :param short_url: the short url of the wallet 
        :param long_url: the long url of the wallet
        :param id: the short_id of the wallet
        """
        c = self.db.cursor()
        # Insert a row of data
        c.execute("insert into wallets(private_key,public_key,wallet_name,path,short_url,long_url,id) values (?,?,?,?,?,?,?)",
                  (private, public, name, path, short_url, long_url, id))
        # Save (commit) the changes
        self.db.commit()
        c.close()

    def update_wallet_name(self, public_key, name):
        self.db_update(
            "update wallets set wallet_name = ?, updated_at = ? where public_key = ?",
            (name, datetime.datetime.now(), public_key)
            )

    def update_wallet_balance(self, public_key, balance):
        self.db_update(
            "update wallets set balance = ?, updated_at = ? where public_key = ?",
            (balance, datetime.datetime.now(), public_key)
        )

    def set_status(self, public_key, new_status):
        """update the status of a wallet"""
        self.db_update(
            'update wallets set wallet_status = ?, updated_at = ? where public_key = ?',
            (new_status, datetime.datetime.now(), public_key)
        )

    def insert_tx(self, sender_public_key, recipient_public_key, amount, tx_hash, fee=1):
        c = self.db.cursor()
        # Insert a row of data
        c.execute("insert into txs(public_key_from, public_key_to, amount, fee, ts, tx_hash) values(?,?,?,?,?,?)",
                  (sender_public_key, recipient_public_key, amount, fee, datetime.datetime.now(), tx_hash))
        # Save (commit) the changes
        self.db.commit()
        c.close()

    def get_wallets(self, status=None, operator='=', offset=0, limit=0):
        """retrieve the list of wallets
        :param status: filter wallets with status
        :param operator: can be '=': only take the wallets with the exacts status, '>=': with status equal or greather, '<': with status less then
        :returns: 
        """
        c = self.db.cursor()
        q, p = 'SELECT * FROM wallets', ()
        if status is not None:
            if operator not in ['=', '<', '>', '>=', '<=']:
                operator = '='
            q += f' WHERE wallet_status {operator} ?'
            p = (status,)
        #  order by id
        q = f'{q} order by id'
        # set the limit
        if limit > 0:
            q = f'{q} limit {limit}'
        # set the offset
        if offset > 0:
            q = f'{q} offset {offset}'

        c.execute(q, p)
        rows = c.fetchall()
        c.close()
        return rows

    def get_txs(self, public_key):
        """get the transactions that involve a public key"""
        c = self.db.cursor()
        q, p = 'SELECT * FROM txs WHERE public_key_from = ? OR public_key_to = ?', (
            public_key, public_key)
        c.execute(q, p)
        rows = c.fetchall()
        c.close()
        return rows

    def wallets2json(self, status=None):
        """crete a json dump of a wallet in the wallet folder"""
        for w in self.get_wallets(status=status):
            if not os.path.exists(w['path']):
                os.makedirs(w['path'], exist_ok=True)
            # folder name
            w['txs'] = self.get_txs(w['public_key'])
            wallet_path = os.path.join(w['path'], FILE_WALLET_NAME)
            # save data
            write_json(wallet_path, w)

    def close(self):
        self.db.close()


def now():
    """return the current date as a string in iso format or in a specified format"""
    return datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc).isoformat()


def getcfg(args):
    """utility function to get config"""
    if args is None or args.config is None:
        raise Exception('config is empty')
    return args.config


def get_aeternity(config):
    """get the epoch client and the genesis keypair from config"""
    # configure epoch client in case we need it
    epoch = EpochClient(configs=Config(
        external_host=config['aeternity'].get('node_host'),
        internal_host=config['aeternity'].get(
            'node_host_internal'),  # + '/internal'
        secure_connection=config['aeternity'].get('node_use_https', False)
    ))
    # load the genesis keypair
    gp = config['aeternity']['genesis_public_key']
    gk = config['aeternity']['genesis_private_key']
    genesis = KeyPair.from_public_private_key_strings(gp, gk)

    return epoch, genesis


def write_json(path, data):
    """utility method to write json files"""
    with open(path, 'w') as fp:
        json.dump(data, fp, indent=2)


def cmd_gen(args=None):
    config = getcfg(args)

    target_folder = config.get('target_folder', DEFAULT_TARGET_FOLDER)
    dry_run = False  # TODO: remove or fix this parameter

    # create target folder if not exists
    if not os.path.exists(target_folder):
        os.mkdir(target_folder)

    if dry_run:
        print("-- RUNNING AS SIMULATION --")

    # wallet index
    windex = Windex()

    # if just dump run only the dump
    if args.dump_json:
        windex.wallets2json()
        return

    # number of wallet to generate
    n = config['n']
    if args.n is not None:
        n = int(args.n)
    print(f'will generate {n} wallets')
    for _ in range(n):
        # generate a new keypair
        keypair = KeyPair.generate()

        windex.insert_wallet(
            keypair.get_private_key(),
            keypair.get_address(),
        )
        print(keypair.get_address())


def cmd_makeurls(args=None):
    """"assign names to the wallets and generate the urls """
    # if is update names then do the update
    # shortener client
    kutt = KuttCli(config['kutt_apikey'], base_url=config['short_baseurl'])
    # name generator
    namer = Namer()
    # wallet index
    windex = Windex()
    #
    long_host = config['long_baseurl']
    target_folder = config.get('target_folder', DEFAULT_TARGET_FOLDER)

    limit = int(args.limit)
    offset = int(args.offset)

    windex.reset_wallet_names()
    for i, w in enumerate(windex.get_wallets(offset=offset, limit=limit)):
        wallet_name = namer.get_city(i)

        # generate the url params
        url_params = {
            'p': w['public_key'],
            'k': w['private_key'],
            'n': wallet_name,
        }
        req = requests.Request('GET', long_host, params=url_params)
        long_url = req.prepare().url

        # generate the short link
        short_id, short_url = kutt.shorten(long_url)
        # path
        wallet_folder = os.path.join(
            target_folder,
            short_id[0:1],
            short_id).lower()

        windex.update_wallet(w['public_key'],
                             wallet_name, wallet_folder, short_url, long_url, short_id)

        print(f'name {wallet_name} for {short_id} - {w["public_key"]}')


def cmd_postcards(args=None):
    """generate the postcards that """
    # wallet index
    windex = Windex()

    # postcards printer
    printer = Printer(
        config['postcard_template_path']['front'],
        config['postcard_template_path']['back']
    )

    limit = int(args.limit)
    offset = int(args.offset)

    wallets = windex.get_wallets(
        status=STATUS_CREATED, operator='>=',
        offset=offset, limit=limit)
    for w in wallets:
        printer.pdf(
            w['path'],
            w['public_key'],
            w['wallet_name'],
            w['short_url']
        )


def cmd_fill(args=None):
    """command to scan the wallets and fill them with money"""
    config = getcfg(args)
    # get the epoch client and the genesis keypair
    epoch, genesis = get_aeternity(config)
    # amount to charget
    amount = config['aeternity']['wallet_credit']

    limit = int(args.limit)
    offset = int(args.offset)

    # wallet index
    windex = Windex()

    # get the wallets
    wallets = windex.get_wallets(
        status=STATUS_CREATED,
        operator='=',
        offset=offset,
        limit=limit)
    for w in wallets:
        recipient_address = w['public_key']

        print(f'fill {amount} to wallet {w["id"]}, {recipient_address}')
        tx_hash = fill(epoch, genesis, recipient_address, amount,
                       ensure_balance=args.ensure_balance)
        # update the status
        windex.set_status(recipient_address, STATUS_FILLED)
        # record the transaction
        windex.insert_tx(
            genesis.get_address(),
            recipient_address,
            amount, tx_hash)


def fill(epoch_cli, sender_keypair, recipient_address, amount, ensure_balance=False):
    """fill a wallet with some amount, read the amount from the provided file"""
    tx_hash = None
    try:
        amount_to_fill = amount
        if ensure_balance:
            balance = 0
            try:
                balance = epoch_cli.get_balance(recipient_address)
            except Exception as x:
                print('account empty')

            if balance >= amount:
                print(
                    f'sufficient funds for {recipient_address} requested: {balance}/{amount}')
            else:
                amount_to_fill = amount - balance
                print(
                    f'will fill {amount_to_fill} tokens to {recipient_address}')
                resp, tx_hash = epoch_cli.spend(keypair=sender_keypair,
                                                recipient_pubkey=recipient_address,
                                                amount=amount_to_fill)
    except Exception as e:
        print(
            f'error running transaction on wallet {recipient_address} , {e}')
        raise e

    return tx_hash


def cmd_claim(args=None):
    """command to scan the wallets and fill them with money"""
    config = getcfg(args)
    # get the epoch client and the genesis keypair
    epoch, genesis = get_aeternity(config)

    limit = int(args.limit)
    offset = int(args.offset)

    # wallet index
    windex = Windex()
    # get the wallets
    wallets = windex.get_wallets(operator='>=', offset=offset, limit=limit)

    
    name_x_thread = 500
    n_threads = int(math.ceil(len(wallets) / name_x_thread))
    print(f"will run {n_threads} workers for name claiming")

    name_queue = Queue()

    def process_queue():
        while True:
            print(f"{threading.current_thread().name}")
            p = name_queue.get()
            claim(epoch, p['account'], p['name'])
            # claim the wallet
            # claim(epoch, account, account_name)
            # update the status
            #windex.set_status(p['account'].get_address(), STATUS_CLAIMED)
            name_queue.task_done()

    for _ in range(n_threads):
        t = threading.Thread(target=process_queue)
        t.daemon = True
        t.start()

    for w in wallets:
        account = KeyPair.from_public_private_key_strings(
            w['public_key'], w['private_key'])
        account_name = f"{w['wallet_name']}.aet"
        # claim(epoch, account, account_name)
        name_queue.put({'account': account, 'name': account_name})

    name_queue.join()


def claim(epoch_cli, account, account_name):
    """ claim the wallet name in the chain """
    name = AEName(account_name, client=epoch_cli)

    do_claim = True

    try:
        if not name.is_available():
            do_claim = False
    except AException as e:
        print(f'name {account_name} {e} for {account.get_address()}')

    if do_claim:
        print(f"name {account_name} is available")
        name.preclaim(account)
        name.claim_blocking(account)
        name.update(account, 
          target=account.get_address(),
                    ttl=36000)
        print(f"name {account_name} claimed")
    else:
        print(
            f'name {account_name} already taken for {account.get_address()}')


def cmd_verify(args=None):

    limit = int(args.limit)
    offset = int(args.offset)

    epoch, genesis = get_aeternity(config)
    # wallet index
    windex = Windex()
  
    required_balance = config['aeternity']['wallet_credit']
    
    wallets = windex.get_wallets(operator='>=', offset=offset, limit=limit)
    for w in wallets:
        
        wallet_address = w['public_key']
        wallet_name = f"{w['wallet_name']}.aet"
        balance = -1

        # verifiy teh balance
        try:
            balance = epoch.get_balance(account_pubkey=wallet_address)
        except Exception:
            balance = 0
        if balance < required_balance:
            windex.set_status(wallet_address, STATUS_CREATED)
        windex.update_wallet_balance(wallet_address, balance)
        
        # verify the name
        name = AEName(wallet_name, client=epoch)
        name_status = 'not claimed'
        try:
            if not name.is_available():
                name_status = 'claimed'
        except AException as e:
            name_status = e.payload['reason']
            
        account_status = 'wallet {:5}, name {:20}:{:11}, balance: {:4} - {}'.format(
          w['id'],
          wallet_name,
          name_status,
          balance,
          wallet_address
        )

        print(account_status)

        
    


def cmd_purge(args=None):

    config = getcfg(args)

    kutt = KuttCli(config['kutt_apikey'], base_url=config['short_baseurl'])
    # wallet index
    windex = Windex()
    if args.kutt_shorturl:
        kutt.purge()
    # delete the wallets
    for w in windex.get_wallets():
        if args.shorturl and w['id'] is not None:
            kutt.delete(w['id'])
            windex.update_wallet(w['public_key'],
                                 w['wallet_name'], w['path'], None, w['long_url'], None)

        if args.workspace and w['path'] is not None:
            if not os.path.exists(w['path']):
                continue
            print(f"delete {w['path']}")
            shutil.rmtree(w['path'])


if __name__ == '__main__':

    cmds = [
        {
            'name': 'gen',
            'help': 'generate wallets',
            'opts': [
                {
                    'names': ['-n'],
                    'help':'number of wallet to generate (overrides the config file)'
                },
                {
                    'names': ['-d', '--dump-json'],
                    'help': 'do not generate but create the json of the existing wallets',
                    'action': 'store_true',
                    'default': False
                },
                {
                    'names': ['-m', '--update-names'],
                    'help': 'only update the wallets with names from a json file',
                    'action': 'store_true',
                    'default': False
                },

            ]
        },
        {
            'name': 'makeurls',
            'help': 'create short and long urls for the wallets',
            'opts': [
                {
                    'names': ['-o', '--offset'],
                    'help':'the offset in the list of wallets to create postcards of',
                    'default': 0
                },
                {
                    'names': ['-l', '--limit'],
                    'help':'limit the number of wallet to create postcards of, 0 means all',
                    'default': 0
                }
            ]
        },
        {
            'name': 'postcards',
            'help': 'generate and postcards pdf files pdf print ',
            'opts': [
                {
                    'names': ['-o', '--offset'],
                    'help':'the offset in the list of wallets to create postcards of',
                    'default': 0
                },
                {
                    'names': ['-l', '--limit'],
                    'help':'limit the number of wallet to create postcards of, 0 means all',
                    'default': 0
                }
            ]
        },
        {
            'name': 'claim',
            'help': 'claim the wallets names',
            'opts': [
                {
                    'names': ['-v', '--verify-only'],
                    'help':'only verify that the name has been claimed',
                    'action': 'store_true',
                    'default': False
                },
                {
                    'names': ['-o', '--offset'],
                    'help':'the offset in the list of wallets to create postcards of',
                    'default': 0
                },
                {
                    'names': ['-l', '--limit'],
                    'help':'limit the number of wallet to create postcards of, 0 means all',
                    'default': 0
                }
            ]
        },
        {
            'name': 'fill',
            'help': 'fill the accounts generated with gen command with the amount specified in config',
            'opts': [
                {
                    'names': ['-b', '--ensure-balance'],
                    'help':'ensure that the balance of the account is > than the wallet fill from config',
                    'action': 'store_true',
                    'default': True
                },
                {
                    'names': ['-v', '--verify-only'],
                    'help':'only verify the balance and the transactions, do not fill',
                    'action': 'store_true',
                    'default': False
                },
                {
                    'names': ['-o', '--offset'],
                    'help':'the offset in the list of wallets to start filling from',
                    'default': 0
                },
                {
                    'names': ['-l', '--limit'],
                    'help':'limit the number of wallet to fill, 0 means no limit',
                    'default': 0
                }
            ]
        },
        {
            'name': 'purge',
            'help': 'delete all the short urls and gnerated wallets',
            'opts': [
                {
                    'names': ['-s', '--shorturl'],
                    'help':'purge the short url service',
                    'action': 'store_true',
                    'default': False
                },
                {
                    'names': ['-k', '--kutt-shorturl'],
                    'help':'purge the short url service using remote api',
                    'action': 'store_true',
                    'default': False
                },
                {
                    'names': ['-w', '--workspace'],
                    'help':'delete folder in the workdspace',
                    'action': 'store_true',
                    'default': False
                },
            ]
        },
        {
            'name': 'verify',
            'help': 'verify the accounts',
            'opts': [
                {
                    'names': ['-o', '--offset'],
                    'help':'the offset in the list of wallets to create postcards of',
                    'default': 0
                },
                {
                    'names': ['-l', '--limit'],
                    'help':'limit the number of wallet to create postcards of, 0 means all',
                    'default': 0
                }
            ]
        }
    ]
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-c', '--cfg', help='path to configruatino file ', default='republica.config.json')
    subparsers = parser.add_subparsers()
    subparsers.required = True
    subparsers.dest = 'command'
    # register all the commands
    for c in cmds:
        subp = subparsers.add_parser(c['name'], help=c['help'])
        # add the sub arguments
        for sa in c.get('opts', []):
            subp.add_argument(*sa['names'],
                              help=sa['help'],
                              action=sa.get('action'),
                              default=sa.get('default'))

    # parse the arguments
    args = parser.parse_args()

    # exit if there is no config file
    if not os.path.exists(args.cfg):
        print('cannot find config file "%s"' % args.cfg)
        parser.print_help()
        exit(1)
    # load setting from config file
    with open(args.cfg, 'r') as fp:
        config = json.load(fp)
    args.__setattr__('config', config)
    # call the command with our args
    ret = getattr(sys.modules[__name__], 'cmd_{0}'.format(
        args.command.replace('-', '_')))(args)
    sys.exit(ret)
