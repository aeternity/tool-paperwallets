#!/usr/bin/env python3
import argparse
import json
import pyqrcode
import getpass

import os
import sys

import sqlite3
import subprocess
from contextlib import contextmanager

import datetime

from queue import Queue
import threading
import math

# pdf
from reportlab.pdfgen import canvas
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.graphics import renderPDF
from reportlab.lib.units import mm
from svglib.svglib import svg2rlg

from aeternity.config import Config
from aeternity.signing import Account
from aeternity.epoch import EpochClient


DEFAULT_TARGET_FOLDER = 'wallets'

STATUS_CREATED = 10
STATUS_FILLED = 20
STATUS_CLAIMED = 30
STATUS_BROADCASTED = 40


FILE_QR_BEERAPP_NAME = 'qr_beerapp.svg'
FILE_QR_PUBKEY_NAME = 'qr_pubkey.svg'
FILE_PDF_FRONT_NAME = 'front.pdf'
FILE_PDF_BACK_NAME = 'back.pdf'
FILE_WALLET_NAME = 'wallet.json'


class Printer(object):
    """class repsonisible to do the pdf printing"""

    def __init__(self, pdf_front_template_path, pdf_back_template_path):
        """

        """
        # template paths
        #
        self.pdf_front_template_path = pdf_front_template_path
        #
        self.pdf_back_template_path = pdf_back_template_path

    def qr_img(self, output_path, data, scale=8.6):
        """generate a qr code from a path"""
        # qr_cli = qrcode.QRCode(
        #     error_correction=qrcode.constants.ERROR_CORRECT_L,
        #     border=0,
        #     box_size=35,
        # )
        # qr_cli.clear()
        # qr_cli.add_data(data)
        # qr_cli.make(fit=True)
        # img = qr_cli.make_image(fill_color="black", back_color="transparent", image_factory=qrcode.image.svg.SvgImage)
        # img.save(output_path)
        x = pyqrcode.create(data)
        x.svg(output_path, scale=scale, quiet_zone=0, module_color="#000")

    def pdf(self, watermark_file, output_file):
        """render the final pdf"""
        # the template path (background)
        pdf_front_template_path_abs = os.path.abspath(self.pdf_front_template_path)
        # the watermark file (foreground)
        watermark_file_abs = os.path.abspath(watermark_file)
        watermark_file_abs_clean = os.path.abspath(f"{watermark_file}.clean.pdf")
        # the final output file
        pdf_front_path_abs = os.path.abspath(output_file)
        # run ghostscript
        cmd = ["gs",
               "-sDEVICE=pdfwrite",
               "-sProcessColorModel=DeviceCMYK",
               "-sColorConversionStrategy=CMYK",
               "-dOverrideICC",
               "-o",
               watermark_file_abs_clean,
               "-f",
               watermark_file_abs
               ]
        subprocess.run(cmd, shell=False, check=True, stdout=subprocess.DEVNULL)
        # run pdftk
        cmd = ["pdftk",
               watermark_file_abs_clean,
               "background",
               pdf_front_template_path_abs,
               "output",
               pdf_front_path_abs
               ]
        subprocess.run(cmd, shell=False, check=True, stdout=subprocess.DEVNULL)

        os.remove(watermark_file_abs_clean)
        os.remove(watermark_file_abs)

    def watermark(self,
                  outfile,
                  pubkey,
                  prvkey,
                  font):
        """generates the pdf with the wallet qr, name and address"""

        # make the target directory
        # if not os.path.exists(work_dir_path):
        #     os.makedirs(work_dir_path, exist_ok=True)

        _specs = {
            "w": 70,
            "h": 148,
            "priv_k": {
                "qr_w": 50,
                "qr_h": 50,
                "qr_x": 9.619,
                "qr_y": 148 - 50 - 76,
            },
            "pub_k": {
                "color": [68, 0, 39, 0],
                "font-size": 7,
                "1st_line_x": 9.619,
                "1st_line_y": 148 - 2.5 - 134.2,
                "2nd_line_x": 9.619,
                "2nd_line_y": 148 - 2.5 - 137.75,
            }
        }

        print(f'generate watermkark at {outfile}')
        # generate qr for the pubkey
        qr_pubkey = f"{outfile}.pub"
        # generate qr code for beer app
        self.qr_img(qr_pubkey, pubkey)

        # generate qr for the prvkey
        qr_prvkey = f"{outfile}.priv"
        # generate qr code for beer app
        self.qr_img(qr_prvkey, prvkey, scale=2.3)

        # Create the watermark from an image
        c = canvas.Canvas(outfile, pagesize=(_specs.get("w") * mm, _specs.get("h") * mm))

        # Draw the image at x, y. I positioned the x,y to be where i like here
        # DRAW PUBKEY
        # x17  w126
        # SVG
        # TODO: currently non necessary
        # _d = svg2rlg(qr_pubkey)
        # _d.width, _d.height = size, size
        # renderPDF.draw(_d, c, x, y)

        
        
        font_name = os.path.basename(font)
        pdfmetrics.registerFont(TTFont(font_name, font))

        # TEXT
        _1st_line_text = f"{pubkey[0:3]}  {pubkey[3:5]} {pubkey[5:8]} {pubkey[8:11]} {pubkey[11:14]} {pubkey[14:17]} {pubkey[17:20]} {pubkey[20:23]} {pubkey[23:26]}"
        _2nd_line_text = f"{pubkey[26:29]} {pubkey[29:32]} {pubkey[32:35]} {pubkey[35:38]} {pubkey[38:41]} {pubkey[41:44]} {pubkey[44:47]} {pubkey[47:50]} {pubkey[50:]: >3}"

        textobject = c.beginText()
        textobject.setTextOrigin(_specs.get("pub_k", {}).get("1st_line_x") * mm,
                                 _specs.get("pub_k", {}).get("1st_line_y") * mm)
        textobject.setFont(font_name, _specs.get("pub_k", {}).get("font-size"))

        _c, m, y, k = _specs.get("pub_k", {}).get("color")
        # textobject.setFillColorCMYK(_c, m, y, k)

        textobject.textLine(_1st_line_text)
        textobject.textLine(_2nd_line_text)

        c.drawText(textobject)

        # DRAW PRIVATE KEY
        # x17  w126
        # SVG
        _d = svg2rlg(qr_prvkey)
        _d.width, _d.height = _specs.get("priv_k", {}).get("qr_w") * mm, _specs.get("priv_k", {}).get("qr_h") * mm
        renderPDF.draw(_d, c, _specs.get("priv_k", {}).get("qr_x") * mm, _specs.get("priv_k", {}).get("qr_y") * mm)
        # save
        c.save()
        # cleanup
        os.remove(qr_pubkey)
        os.remove(qr_prvkey)
        # outfile
        return outfile


class Windex(object):

    def __init__(self, db_path='republica_wallets.sqlite', overwrite=False):

        do_create = overwrite if os.path.exists(db_path) else True

        self.db_path = db_path
        self.db = sqlite3.connect(db_path)

        def dict_factory(cursor, row):
            d = {}
            for idx, col in enumerate(cursor.description):
                d[col[0]] = row[idx]
            return d

        self.db.row_factory = dict_factory

        if do_create:
            self.execute('DROP TABLE IF EXISTS "wallets"')
            self.execute('''CREATE TABLE wallets(
        private_key varchar PRIMARY KEY
        , public_key varchar not null
        , wallet_name varchar
        , balance_ae float not null default '0'
        , path varchar
        , wallet_status int not null default '10'
        , id varchar
        , short_url varchar
        , long_url varchar
        , nonce int not null default 0
        , created_at datetime default CURRENT_TIMESTAMP
        , updated_at datetime default CURRENT_TIMESTAMP
        , tag varchar);''')
            self.execute('''DROP TABLE IF EXISTS "txs";''')
            self.execute('''CREATE TABLE txs(
        tx varchar PRIMARY_KEY
        , tx_signed varchar
        , tx_hash varchar
        , sender_id varchar not null
        , recipient_id varchar not null
        , amount_ae float not null default '0'
        , fee int not null default 0
        , ttl int not null default 0
        , nonce int not null default 0
        , payload varchar
        , created_at datetime not null default CURRENT_TIMESTAMP
        , published_at datetime
        , status int not null default '10'
        , broadcast_response text default null
            );''')

    @contextmanager
    def getcursor(self):
        """retrieve a cursor from the database"""
        try:
            yield self.db.cursor()
        finally:
            self.db.commit()

    def execute(self, query, params=()):
        """run a database update
        :param query: the query string
        :param params: the query parameteres
        """
        with self.getcursor() as c:
            try:
                c.execute(query, params)
                # logging.debug(c.query)
            except Exception as e:
                # logging.error(e)
                print(e)

    def select(self, query, params=(), many=False):
        """
        run a database update
        :param query: the query string
        :param params: the query parameteres
        :param many: if True returns a list of rows, otherwise just on row
        """
        with self.getcursor() as c:
            try:
                # Insert a row of data
                c.execute(query, params)
                if many:
                    return c.fetchall()
                else:
                    return c.fetchone()
            except Exception as e:
                # logging.error(e)\
                print(e)
    # statuses are
    # - created (just the private/public keys)
    # - filled (the account as been filled)
    # - named (the account name has been registered)
    # -

    def insert_wallet(self, private, public, name=None, path=None, short_url=None, long_url=None, id=None, tag=None):
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
        # Insert a row of data
        self.execute("insert into wallets(private_key,public_key,wallet_name,path,short_url,long_url,id,tag) values (?,?,?,?,?,?,?,?)",
                     (private, public, name, path, short_url, long_url, id, tag))

    def update_wallet(self, public_key, name, path, short_url, long_url, id):
        self.execute(
            "update wallets set wallet_name = ?, path = ?, id = ?, short_url = ?, long_url = ?, updated_at = ? where public_key = ?",
            (name, path, id, short_url, long_url,
             datetime.datetime.now(), public_key)
        )

    def update_wallet_balance(self, public_key, balance):
        self.execute(
            "update wallets set balance_ae = ?, updated_at = ? where public_key = ?",
            (balance, datetime.datetime.now(), public_key)
        )

    def set_status(self, public_key, new_status):
        """update the status of a wallet"""
        self.execute(
            'update wallets set wallet_status = ?, updated_at = ? where public_key = ?',
            (new_status, datetime.datetime.now(), public_key)
        )

    def reset_wallet_names(self):
        """set the wallet_name to null"""
        self.execute('update wallets set wallet_name = ?', (None,))

    def insert_tx(self, tx, sender_id, recipient_id, amount, payload, fee, ttl, nonce,
                  tx_signed=None,
                  tx_hash=None,
                  created_at=datetime.datetime.now(),
                  published_at=None):
        # Insert a row of data
        self.execute("""insert into txs
        (tx, sender_id, recipient_id, amount_ae, payload, fee, ttl, nonce, tx_hash, tx_signed, created_at, published_at) 
        values(?,?,?,?,?,?,?,?,?,?,?,?)""",
                     (tx, sender_id, recipient_id, amount, payload, fee, ttl, nonce, tx_hash, tx_signed, datetime.datetime.now(), published_at))

    def update_tx(self, tx, **kwargs):
        fields, values, ph = [], [], []
        for k, v in kwargs.items():
            fields.append(k)
            values.append(v)
            ph.append('?')
        values.append(tx)
        # Insert a row of data
        self.execute(f"update txs set  ({','.join(fields)}) = ({','.join(ph)}) where tx = ?", values)

    def get_wallets(self, status=None, operator='=', offset=0, limit=-1, tag=None):
        """retrieve the list of wallets
        :param status: filter wallets with status
        :param operator: can be '=': only take the wallets with the exacts status, '>=': with status equal or greather, '<': with status less then
        :returns:
        """
        q, p = 'SELECT * FROM wallets', ()

        where_clauses = []
        where_params = []

        if status is not None:
            if operator not in ['=', '<', '>', '>=', '<=']:
                operator = '='
            where_clauses.append(f' wallet_status {operator} ?')
            where_params.append(status)
        if tag is not None:
            where_clauses.append(f' tag = ?')
            where_params.append(tag)

        if len(where_clauses) > 0:
            q = f"{q} WHERE {' AND '.join(where_clauses)}"
            p = tuple(where_params)

        #  order by id
        q = f'{q} order by public_key'
        # set the limit
        if limit > 0:
            q = f'{q} limit {limit}'
        # set the offset
        if offset > 0:
            q = f'{q} offset {offset}'

        rows = self.select(q, p, many=True)
        print(f"fetched {len(rows)} wallets")
        return rows

    def get_txs(self, public_key):
        """get the transactions that involve a public key"""
        q, p = 'SELECT * FROM txs WHERE sender_id = ? OR recipient_id = ?', (public_key, public_key)
        return self.select(q, p, many=True)

    def get_txs_by_status(self, status, offset=0, limit=-1):
        """get the transactions that involve a public key"""
        q, p = 'SELECT * FROM txs WHERE status = ? order by published_at limit ? offset ?', (status, limit, offset)
        return self.select(q, p, many=True)

    def wallets2json(self, status=None):
        """crete a json dump of a wallet in the wallet folder"""
        accounts = []
        for w in self.get_wallets(status=status):
            # if not os.path.exists(w['path']):
            #     os.makedirs(w['path'], exist_ok=True)
            accounts.append(w)
            # folder name
            # w['txs'] = self.get_txs(w['public_key'])
            # wallet_path = os.path.join(w['path'], FILE_WALLET_NAME)
            # save data
            # write_json(wallet_path, w)
        with open(f"{self.db_path}.json", "w") as fp:
            json.dump(accounts, fp)

    def close(self):
        self.db.close()


def write_json(path, data):
    """utility method to write json files"""
    with open(path, 'w') as fp:
        json.dump(data, fp, indent=2)


#     ______  ____    ____  ______     ______
#   .' ___  ||_   \  /   _||_   _ `. .' ____ \
#  / .'   \_|  |   \/   |    | | `. \| (___ \_|
#  | |         | |\  /| |    | |  | | _.____`.
#  \ `.___.'\ _| |_\/_| |_  _| |_.' /| \____) |
#   `.____ .'|_____||_____||______.'  \______.'
#

# --output-db-file (paperwallets/data.db.sqlite)
# --dump_json (False)
# --tag
def cmd_gen(args=None):

    # dry_run = False  # TODO: remove or fix this parameter
    # create target folder if not exists
    os.makedirs(os.path.dirname(args.output_db_file), exist_ok=True)

    overwrite = False
    if os.path.exists(args.output_db_file):
        txt = input("Database file already exists, overwrite? y/n  [y]: ")
        overwrite = True if txt == 'y' else overwrite
    # if dry_run:
    #     print("-- RUNNING AS SIMULATION --")

    # wallet index
    windex = Windex(args.output_db_file, overwrite=overwrite)
    # if just dump run only the dump
    if args.dump_json:
        windex.wallets2json()
        return
    # number of wallet to generate
    n = int(args.n)
    print(f'will generate {n} accounts')
    for _ in range(n):
        # generate a new keypair
        keypair = Account.generate()
        windex.insert_wallet(
            keypair.get_private_key(),
            keypair.get_address(),
            tag=args.tag
        )
        print(keypair.get_address())


# --input_db_file (paperwallets/data.db.sqlite)
# --template-front
# --template-back
def cmd_paperwallets(args=None):
    """generate the postcards that """
    # wallet index
    windex = Windex(args.input_db_file)
    # limit / offset
    limit = -1  # int(args.limit)
    offset = 0  # int(args.offset)

    wallets = windex.get_wallets(offset=offset, limit=limit, tag=args.tag)
    # calculate the number of threads
    name_x_thread = 300
    n_threads = int(math.ceil(len(wallets) / name_x_thread))
    print(f"will run {n_threads} workers for name claiming")

    # output folder
    out_folder = args.output_folder

    # printing queue
    queue_pdf = Queue()

    def process_watermark_queue():
        # postcards printer
        printer = Printer(
            args.template_front,
            args.template_back
        )
        # create a tmp dir
        workspace = out_folder
        os.makedirs(workspace, exist_ok=True)
        # go trough the queue

        while True:
            print(f"{threading.current_thread().name}")
            w = queue_pdf.get()

            # generate qr for public key
            pubkey = w.get("public_key")
            privkey = w.get("private_key")
            watermark_path = os.path.join(workspace, f"{pubkey}.watermark.pdf")
            printer.watermark(
                watermark_path,
                pubkey,
                privkey,
                args.font
            )
            # priv key
            paperwallet = os.path.join(workspace, f"{pubkey}.pdf")
            # create it
            printer.pdf(watermark_path, paperwallet)
            # cleanup
            # done
            queue_pdf.task_done()

    # generate the watermark
    for _ in range(n_threads):
        t = threading.Thread(target=process_watermark_queue)
        t.daemon = True
        t.start()

    for w in wallets:
        # claim(epoch, account, account_name)
        queue_pdf.put(w)

    queue_pdf.join()


# --amount
# --keystore
# --payload ("")
# --ttl (0)
# --nonce
# --input_db_file (paperwallets/data.db.sqlite)
# --network/id
def cmd_txs_prepare(args):
    """command to scan the wallets and fill them with money"""
    epoch = EpochClient(offline=True, configs=Config(network_id=args.network_id))
    # amount to charget
    amount = int(args.amount)
    nonce = int(args.nonce)
    fee = int(args.fee)
    payload = args.payload
    keystore = args.keystore
    ttl = args.ttl
    # load the sign account
    if not os.path.exists(keystore):
        print(f"keystore file not found at {keystore}")
        return
    pwd = getpass.getpass("Enter the keystore password:")
    sign_account = Account.from_keystore(keystore, pwd)
    # tx signer
    print(f"Using {args.network_id} and {sign_account.get_address()} for signing transactions")
    # wallet index
    windex = Windex(args.input_db_file)

    # get the wallets
    wallets = windex.get_wallets(
        status=STATUS_CREATED,
        operator='=',
        tag=args.tag)
    for w in wallets:
        recipient_id = w['public_key']
        # create the transaction
        tx = epoch.tx_builder.tx_spend(
            sign_account.get_address(),
            recipient_id,
            amount * 1000000000000000000 + 20000, # plus fee
            payload,
            fee,
            ttl,
            nonce
        )
        # sign the transaction
        tx_signed, signature, tx_hash = epoch.sign_transaction(sign_account, tx)
        windex.insert_tx(tx,
                         sign_account.get_address(),
                         recipient_id,
                         amount,
                         payload,
                         fee,
                         ttl,
                         nonce,
                         tx_hash=tx_hash,
                         tx_signed=tx_signed)
        nonce += 1
        print(f'top up {amount}AE to account {recipient_id}')


# --epoch-url ("https://sdk-mainnet.aepps.com")
# --tag
# --input_db_file (paperwallets/data.db.sqlite)
def cmd_txs_broadcast(args):
    epoch = EpochClient(configs=Config(args.epoch_url))
    # wallet index
    windex = Windex(args.input_db_file)
    # get the wallets
    txs = windex.get_txs_by_status(STATUS_CREATED)
    for t in txs:
        try:
            reply = epoch.broadcast_transaction(t.get("tx_signed"), t.get("tx_hash"))

            tx = t.get("tx")
            up = dict(broadcast_response=reply, status=STATUS_BROADCASTED)

            windex.update_tx(tx, **up)
            print(f"tx hash {t.get('tx_hash')} broadcasted: {reply}")
        except Exception as e:
            print(f"tx hash {t.get('tx_hash')} broadcast error: {e}")


# --epoch-url ("https://sdk-mainnet.aepps.com")
# --input_db_file (paperwallets/data.db.sqlite)
def cmd_verify(args=None):
    limit = int(args.limit)
    offset = int(args.offset)
    epoch = EpochClient(configs=Config(args.epoch_url))
    # wallet index
    windex = Windex(args.input_db_file)

    txs = windex.get_txs_by_status(STATUS_BROADCASTED, limit=limit, offset=offset)
    for t in txs:
        executed = epoch.get_transaction_by_hash(hash=t.get("tx_hash"))
        print(f"tx {t.get('tx_hash')} from {t.get('sender_id')} to {t.get('recipient_id')}, amount {t.get('amount')} height: {executed.block_height}")


if __name__ == '__main__':

    cmds = [
        {
            'name': 'gen',
            'help': 'generate accounts',
            'opts': [
                {
                    'names': ['-n'],
                    'help':'number of accounts to generate (overrides the config file)',
                    'required': True
                },
                {
                    'names': ['-d', '--dump-json'],
                    'help': 'do not generate but create the json of the existing accounts',
                    'action': 'store_true',
                    'default': False
                },
                {
                    'names': ['-t', '--tag'],
                    'help': 'tag the accounts with the tag',
                    'default': None
                },
                {
                    'names': ['-f', '--output-db-file'],
                    'help': 'sqlite db file name to generate',
                    'default': 'paperwallets/data.db.sqlite'
                },

            ]
        },
        {
            'name': 'paperwallets',
            'help': 'generate and postcards pdf files pdf print ',
            'opts': [
                {
                    'names': ['-f', '--input-db-file'],
                    'help': 'sqlite db file name to load',
                    'default': 'paperwallets/data.db.sqlite'
                },
                {
                    'names': ['-o', '--output-folder'],
                    'help':'the folder where all the pdf will be stored',
                    'required': True
                },
                {
                    'names': ['-t', '--tag'],
                    'help': 'filter wallets by tag',
                    'default': None
                },
                {
                    'names': ['--template-front'],
                    'help': 'the template to use for the front',
                    'default': '/data/assets/paper-wallet-blank-front.pdf'
                },
                {
                    'names': ['--template-back'],
                    'help': 'the template to use for the back',
                    'default': '/data/assets/paper-wallet-back.pdf'
                },
                {
                    'names': ['--font'],
                    'help': 'the font ttf file to use (default Roboto)',
                    'default': '/data/assets/IBMPlexMono-Regular.ttf'
                },

            ]
        },
        {
            'name': 'txs-prepare',
            'help': 'create the transactions',
            'opts': [
                {
                    'names': ['-f', '--input-db-file'],
                    'help': 'sqlite db file name to load',
                    'default': 'paperwallets/data.db.sqlite'
                },
                {
                    'names': ['--amount'],
                    'help':'amount to fill',
                    'required': True
                },
                {
                    'names': ['--nonce'],
                    'help':'the starting nonce',
                    'required': True
                },
                {
                    'names': ['--fee'],
                    'help':'the transactions fee (default: 18000)',
                    'default': 18000
                },
                {
                    'names': ['--ttl'],
                    'help':'transaction ttl (default: 0)',
                    'default': 0
                },
                {
                    'names': ['--payload'],
                    'help':'transaction payload (default: empoty)',
                    'default': ''
                },
                {
                    'names': ['--keystore'],
                    'help': 'the keystore to sign the transaction',
                    'required': True
                },
                {
                    'names': ['--network-id'],
                    'help': 'the network id of the chain to use (default ae_mainnet)',
                    'default': 'ae_mainnet'
                },
                {
                    'names': ['-t', '--tag'],
                    'help': 'filter accounts by tag',
                    'default': None
                },

            ]
        },
        {
            'name': 'txs-broadcast',
            'help': 'post the transactions to the chain',
            'opts': [
                {
                    'names': ['-f', '--input-db-file'],
                    'help': 'sqlite db file name to load',
                    'default': 'paperwallets/data.db.sqlite'
                },
                {
                    'names': ['--epoch-url'],
                    'help':'the url of the node to use (default https://sdk-mainnet.aepps.com)',
                    'default': 'https://sdk-mainnet.aepps.com'
                }
            ]
        },
        {
            'name': 'verify',
            'help': 'verify the executed transactions',
            'opts': [
                {
                    'names': ['-f', '--input-db-file'],
                    'help': 'sqlite db file name to load',
                    'default': 'paperwallets/data.db.sqlite'
                },
                {
                    'names': ['-o', '--offset'],
                    'help':'the offset in the list of wallets to create postcards of',
                    'default': 0
                },
                {
                    'names': ['-l', '--limit'],
                    'help':'limit the number of wallet to create postcards of, 0 means all',
                    'default': -1
                },
                {
                    'names': ['-t', '--tag'],
                    'help': 'filter wallets by tag',
                    'default': None
                }
            ]
        }
    ]
    parser = argparse.ArgumentParser()
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
                              default=sa.get('default'),
                              required=sa.get('required', False))

    # parse the arguments
    args = parser.parse_args()
    # call the command with our args
    ret = getattr(sys.modules[__name__], 'cmd_{0}'.format(
        args.command.replace('-', '_')))(args)
    sys.exit(ret)
