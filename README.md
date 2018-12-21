# Paperwallets

- Generate accounts
- Topup accounts
- Print paperwallets

## Requirements

- docker

## Setup

In the example we will be working in the folder `data` and using `sdk-testnet` as target network.


## Step 1 - Create the wallets

Create 100 accounts

```
docker run -it --volume=$PWD/data:/data/paperw aeternity/paperwallets \
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
  Nonce _____________________________________________ 0 #
</account>
```

⚠️ For mainnet use:
```
$ aecli inspect ak_2iBPH7HUz3cSDVEUWiHg76MZJ6tZooVNBmmxcgVK6VV8KAE688
```

Create then the transactions (the amount is in AE).
The nonce to use is the one found in with the previous command + 1, in this case, since the Nonce from the previous command is 0, we need to use for the next command.


```
docker run -it --volume=$PWD/data:/data/paperw aeternity/paperwallets \
 txs-prepare \
 -f /data/paperw/data.db.sqlite \
 --amount 10 \
 --nonce 105 \
 --keystore /data/paperw/sender.json \
 --network-id ae_uat

Enter the keystore password:
**********
```

⚠️ for mainnet remove the `--network-id` parameter

## Step 3 - Post the transactions to the chain

```
docker run -it --volume=$PWD/data:/data/paperw  aeternity/paperwallets \
 txs-broadcast \
 -f /data/paperw/data.db.sqlite \
 --epoch-url https://sdk-testnet.aepps.com # remove this parameter for mainnet
```

⚠️ for mainnet remove the `--epoch-url` parameter

## Step 4 - Generate the paper wallets

The last part will generate the actual pdf in the `paperw/pdfs` folder

```
docker run -it --volume=$PWD/data:/data/paperw  aeternity/paperwallets \
 paperwallets \
 -f /data/paperw/data.db.sqlite \
 -o /data/paperw/pdfs
```

## Step 5 - get the back pdf for the paper wallet

You can download the back side of the template [here](https://github.com/aeternity/tool-paperwallets/raw/develop/assets/paper-wallet-back.pdf) 

## Notes

⚠️ Remember to save the sqlite database to recover the private keys later