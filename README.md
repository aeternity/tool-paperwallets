# Paperwallets

- Generate accounts
- Topup accounts
- Print paperwallets

## Requirements

- docker 
- python sdk

## Setup

In the example we will be working in the folder `paperw` and using `sdk-testnet` as target network

First step is to build the docker image

```
$ tar xzf paperwallet.tgz
$ cd paperwallets
$ docker build -t paperwallets .
```
Once the image is built you can use the following steps to create the paperwallets

To install the python sdk refer to the instructions on the [sdk readme](https://github.com/aeternity/aepp-sdk-python/tree/develop#installation)

## Step 1 - Create the wallets

Create 100 accounts

```
docker run -it --volume=$PWD/data:/data/paperw paperwallets \
  gen -n 100 -f /data/paperw/data.db.sqlite
```

this will create a sqlite database where all the accounts and transactinos will be stored

## Step 2 - Prepare the transactions

It requires to have access to an account stored in the json keystore format supported by the sdks,
to save the account in the correct format:

```
$ aecli account create data/sender.json
```
after that top up the account with enough tokens.

Verify the current nonce of the sender account:
```
$ aecli account address data/sender.json
Enter the account password
<account>
  Address ___________________________________________ ak_2iBPH7HUz3cSDVEUWiHg76MZJ6tZooVNBmmxcgVK6VV8KAE688
</account>

$ aecli -u https://sdk-testnet.aepps.com inspect ak_2iBPH7HUz3cSDVEUWiHg76MZJ6tZooVNBmmxcgVK6VV8KAE688
<account>
  Balance ___________________________________________ 65667431000000000007157984
  Id ________________________________________________ ak_2iBPH7HUz3cSDVEUWiHg76MZJ6tZooVNBmmxcgVK6VV8KAE688
  Nonce _____________________________________________ 0
</account>
```

⚠️ For mainnet use:
```
$ aecli inspect ak_2iBPH7HUz3cSDVEUWiHg76MZJ6tZooVNBmmxcgVK6VV8KAE688
```

Create then the transactions (the amount is in AE)

```
docker run -it --volume=$PWD/data:/data/paperw paperwallets \
 txs-prepare \
 -f /data/paperw/data.db.sqlite \
 --amount 10 \
 --nonce 1 \
 --keystore /data/paperw/sender.json \
 --network-id ae_uat # remove this parameter for mainnet

Enter the keystore password:
**********
```

⚠️ for mainnet remove the `--network-id` parameter

## Step 3 - Post the transactions to the chain

```
docker run -it --volume=$PWD/data:/data/paperw  paperwallets \
 txs-broadcast \
 -f /data/paperw/data.db.sqlite \
 --epoch-url https://sdk-testnet.aepps.com
```

⚠️ for mainnet remove the `--epoch-url` parameter

## Step 4 - Generate the paper wallets

The last part will generate the actual pdf in the `paperw/pdfs` folder

```
docker run -it --volume=$PWD/data:/data/paperw  paperwallets \
 paperwallets \
 -f /data/paperw/data.db.sqlite \
 -o /data/paperw/pdfs \
 --template-front /data/assets/paper-wallet-blank-front.pdf
```


## Notes

⚠️ Remember to save the sqlite database to recover the private keys later