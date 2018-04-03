#!/usr/bin/env python3
import argparse
import json
import logging

import os
import requests
import sys

import qrcode
import qrcode.image.svg

import shutil

import nanoid

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


DEFAULT_TARGET_FOLDER = 'wallets'

FILE_QR_BEERAPP_NAME = ''

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
        pass

    def shorten(self, original_url):
        """returns a short url string"""
        data = {'target': original_url}
        headers = {'X-API-Key': self.api_key}
        endp = '%s/api/url/submit' % self.kuttit_baseurl
        r = requests.post(endp, data=data, headers=headers)
        # see https://github.com/thedevs-network/kutt#types
        url_object = r.json()
        return url_object['id'], url_object['shortUrl']

    def purge(self):
        has_urls = True
        while has_urls:
            headers = {'X-API-Key': self.api_key}
            endp = '%s/api/url/geturls' % self.kuttit_baseurl
            r = requests.get(endp, headers=headers)
            urls = r.json()
            print('REMOVING %d URLS' % urls['countAll'])
            # loop trought the urls and delete them
            endp = '%s/api/url/deleteurl' % self.kuttit_baseurl
            for u in urls['list']:
                print('remove [%s] %s ' % (u['id'], u['shortUrl']))
                requests.post(endp, headers=headers, data={'id': u['id']})
            if urls['countAll'] <= 0:
                has_urls = False


def pdf(template_front_path,
        qr_front_path,
        template_back_path,
        qr_back_path,
        work_dir_path,
        pdf_front_path,
        pdf_back_path,
        address='',
        name='',
        url=''):
    """generates the pdf with the wallet qr, name and address"""

    # first front
    watermark_file = os.path.join(work_dir_path, 'watermark_front.pdf')
    # Create the watermark from an image
    c = canvas.Canvas(watermark_file)
    # Draw the image at x, y. I positioned the x,y to be where i like here
    # x17  w126
    x = 31
    c.drawImage(qr_front_path, x, 163, 96, 96)
    # Add some custom text for good measure
    # c.setFont("Suisse Int’l Mono", 10)
    c.setFont("Roboto", 8)
    c.drawString(x, 133, name)
    c.drawString(x, 103, address[0:21])
    c.drawString(x, 90, address[21:42])
    c.drawString(x, 78, address[42:63])
    c.drawString(x, 64, address[63:84])
    c.drawString(x, 52, address[84:])
    c.save()
    # Get the watermark file you just created
    watermark = PdfFileReader(open(watermark_file, "rb"))
    # Get our files ready
    output_file = PdfFileWriter()
    input_file = PdfFileReader(open(template_front_path, "rb"))

    input_page = input_file.getPage(0)
    input_page.mergePage(watermark.getPage(0))
    # add page from input file to output document
    output_file.addPage(input_page)

    # finally, write "output" to document-output.pdf
    with open(pdf_front_path, "wb") as outputStream:
        output_file.write(outputStream)

    # now do the back
    watermark_file = os.path.join(work_dir_path, 'watermark_back.pdf')
    # Create the watermark from an image
    c = canvas.Canvas(watermark_file)
    # Draw the image at x, y. I positioned the x,y to be where i like here
    # x17  w126
    x = 314
    c.drawImage(qr_back_path, x, 182, 93, 93)
    # Add some custom text for good measure
    # c.setFont("Suisse Int’l Mono", 10)
    c.setFont("Roboto", 8)
    c.drawString(x, 170, url)
    c.save()
    # Get the watermark file you just created
    watermark = PdfFileReader(open(watermark_file, "rb"))
    # Get our files ready
    output_file = PdfFileWriter()
    input_file = PdfFileReader(open(template_back_path, "rb"))

    input_page = input_file.getPage(0)
    input_page.mergePage(watermark.getPage(0))
    # add page from input file to output document
    output_file.addPage(input_page)

    # finally, write "output" to document-output.pdf
    with open(pdf_back_path, "wb") as outputStream:
        output_file.write(outputStream)


def qr_img(qr_cli, output_path, data):
    """generate a qr code from a path"""
    qr_cli.clear()
    qr_cli.add_data(data)
    qr_cli.make(fit=True)
    img = qr_cli.make_image(fill_color="black", back_color="white")
    img.save(output_path)


def getcfg(args):
    """utility function to get config"""
    if args is None or args.config is None:
        raise Exception('config is empty')
    return args.config


def get_aeternity(config):
    """get the epoch client and the genesis keypair from config"""
    # configure epoch client in case we need it
    epoch = EpochClient(configs=Config(
        external_host=config['aeternity']['node_url'],
        internal_host=config['aeternity']['node_url'] + '/internal',
        secure_connection=True
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
    # TODO random prefix to avoid overwriting values by concurrent executions

    long_host = config['long_baseurl']
    short_host = config['short_baseurl']
    target_folder = config.get('target_folder', DEFAULT_TARGET_FOLDER)
    dry_run = args.simulate
    # template paths
    pdf_front_template_path = config['postcard_template_path']['front']
    pdf_back_template_path = config['postcard_template_path']['back']

    # create target folder if not exists
    if not os.path.exists(target_folder):
        os.mkdir(target_folder)

    if dry_run:
        print("-- RUNNING AS SIMULATION --")

    # QR code generation
    qr_cli = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=0,
    )

    # pdf fonts
    pdfmetrics.registerFont(
        TTFont('Roboto', 'fonts/RobotoMono-Regular.ttf')
        )

    # shortener client
    kutt = KuttCli(config['kutt_apikey'], base_url=config['short_baseurl'])
    # mnemonic key generator BIP-0039: Mnemonic code for generating deterministic keys
    # mnem = mnemonic.Mnemonic('english')

    # get the epoch client and the genesis keypair
    epoch, genesis = get_aeternity(config)

    # number of wallet to generate
    n = config['n']
    if args.n is not None:
        n = int(args.n)
    print(f'will generate {n} wallets')
    for x in range(n):
        # generate a new keypair
        keypair = KeyPair.generate()

        # TODO save the current time
        # d = datetime.datetime.now(tzlocal())
        # generate the url params
        url_params = {
            'p': keypair.get_address(),
            'k': keypair.get_private_key(),
            'n': keypair.get_name(),
        }

        long_url = requests.Request(
            'GET', long_host, params=url_params).prepare().url
        # generate the short link
        short_id = nanoid.generate(size=5)
        short_url = f'{short_host}/{short_id}'
        if not dry_run:
            short_id, short_url = kutt.shorten(long_url)

        # folder name
        wallet_folder = os.path.join(target_folder, short_id)
        qr_beerapp_path = os.path.join(wallet_folder, FILE_QR_BEERAPP_NAME)
        qr_pubkey_path = os.path.join(wallet_folder, FILE_QR_PUBKEY_NAME)
        pdf_front_path = os.path.join(wallet_folder, FILE_PDF_FRONT_NAME)
        pdf_back_path = os.path.join(wallet_folder, FILE_PDF_BACK_NAME)
        wallet_path = os.path.join(wallet_folder, FILE_WALLET_NAME)

        # prepare data to be saved locally
        data = {
            'id': short_id,
            'long_url': long_url,
            'short_url': short_url,
            'wallet': url_params,
            'txs': []
        }

        # if simulate just print the data
        if dry_run:
            print(json.dumps(data, indent=2))
            continue

        # make the target directory
        os.mkdir(wallet_folder)
        # generate qr code for beer app
        qr_img(qr_cli, qr_beerapp_path, short_url)
        # generate qr code for public key
        qr_img(qr_cli, qr_pubkey_path, keypair.get_address())
        # save data
        write_json(wallet_path, data)
        # create pdfs
        pdf(pdf_front_template_path,
            qr_beerapp_path,
            pdf_back_template_path,
            qr_pubkey_path,
            wallet_folder,
            pdf_front_path,
            pdf_back_path,
            data['wallet']['p'],
            data['wallet']['n'],
            data['short_url'][8:]) # do not include the 'https://'
        # done
        print(data['short_url'])

        if args.fill:
            # fill the account
            amount = config['aeternity']['wallet_credit']
            tx = fill(epoch, genesis, keypair.get_address(),
                      amount, ensure_balance=args.ensure_balance)
            if tx is not None:
                data['txs'].append('tx_hash')
                write_json(wallet_path, data)


def cmd_fill(args=None):
    """command to scan the wallets and fill them with money"""
    config = getcfg(args)
    # read all the wallet json files
    target_folder = config.get('target_folder', DEFAULT_TARGET_FOLDER)
    # get the epoch client and the genesis keypair
    epoch, genesis = get_aeternity(config)
    # amount to charget
    amount = config['aeternity']['wallet_credit']
    # search all
    with os.scandir(target_folder) as it:
        for entry in it:
            if entry.is_dir():
                wallet_path = os.path.join(entry.path, FILE_WALLET_NAME)
                with open(wallet_path, 'r') as fp:
                    data = json.load(fp)
                    recipient_address = data['wallet']['p']
                    print(
                        f'fill wallet at path {wallet_path}, {recipient_address}')
                    tx_hash = fill(epoch, genesis, recipient_address,
                                   amount, ensure_balance=args.ensure_balance)
                    if tx_hash is not None:
                        data['txs'].append(tx_hash)


def fill(epoch_cli, sender_keypair, recipient_address, amount, ensure_balance=False):
    """fill a wallet with some amount, read the amount from the provided file"""
    tx_hash = None
    try:
        amount_to_fill = amount
        if ensure_balance:
            balance = epoch_cli.get_balance(recipient_address)
            if balance >= amount:
                print(
                    f'sufficient funds for {recipient_address} requested: {balance}/{amount}')
            else:
                amount_to_fill = amount - balance

        resp, tx_hash = epoch_cli.spend(keypair=sender_keypair,
                                        recipient_pubkey=recipient_address,
                                        amount=amount_to_fill)
    except Exception as e:
        print(
            f'error running transaction on wallet {recipient_address} , {e}')

    return tx_hash


def cmd_purge(args=None):

    config = getcfg(args)

    # remove the short links
    kutt = KuttCli(config['kutt_apikey'], base_url=config['short_baseurl'])
    kutt.purge()
    # delete the wallets
    target_folder = config.get('target_folder', None)
    if target_folder is None or target_folder == '.':
        print(f"invalid target folder {target_folder}")
        return
    if not os.path.exists(target_folder):
        print(f"target folder '{target_folder}' does not exists")
        return
    shutil.rmtree(target_folder)

    # recreate the wallet folder
    os.mkdir(target_folder)


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
                    'names': ['-s', '--simulate'],
                    'help': 'only simulate the process, do not generate wallets or pdfs',
                    'action': 'store_true',
                    'default': False
                },
                {
                    'names': ['--fill'],
                    'help': 'fill the account (overrides the config file)',
                    'action': 'store_true',
                    'default': False
                },
                {
                    'names': ['-b', '--ensure-balance'],
                    'help':'ensure that the balance of the account is > than the wallet fill from config (valid only with --fill)',
                    'action': 'store_true',
                    'default': False
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
                    'default': False
                }
            ]
        },
        {
            'name': 'purge',
            'help': 'delete all the short urls and gnerated wallets'
        },
        {
            'name': 'verify',
            'help': 'verify transactions created with the fill command',
            'opts': [
                {
                    'names': ['-t', '--transaction'],
                    'help':'verify a single transaction'
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
