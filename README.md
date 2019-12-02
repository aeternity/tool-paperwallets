# TUTORIAL: Creating æternity Paper Wallets

## Tutorial Overview
This tutorial will walk you through the steps of creating your own æternity paper wallet(s), including generation of accounts, broadcasting multiple transactions at once and generating QR codes.

## Wait... what is a paper wallet?
Paper wallets are useful tools for securing and sending AE tokens. A paper wallet is simply a pair of QR codes (a public and a private key) printed on a piece of paper that users can use to store and send AE tokens. It is possible to use a paper wallet to quickly claim a reward in AE tokens by simply scanning a QR code. As such, AE paper wallets can be used for various promotional campaigns, bounties, event-related usecases, or for simply storing your AE in secure, off-line environemnt.

## Prerequisites
- Docker
- Installed Aecli - For installation steps refer to [this tutorial](account-creation-in-ae-cli.md#installing-aecli)

## Step 1. Prepare your environment

First things first, we need to setup our working directories. Lets create a directory named `paper-wallets`. We will use this directory to execute all the following commands.
```
mkdir paper-wallets && cd paper-wallets
```

We would also need one more directory `data` - data where the various artifacts of the paper wallets will be created.
```
mkdir data
```

to set the node url for the network you want to use create the an `.env` file with the following content:

```
NODE_URL='http://localhost:3013'
```

this url will be automatically used across the whole process.

## Step 2. Create funding account
In order to create paper wallets we need an AE account to fund them. Lets create a `sdk-testnet` account and get some test AE. Alternatively you can use your own testnet/mainnet accounts and skip this section or ask for some actual AE in [the Forum](https://forum.aeternity.com/t/get-some-aettos-for-testing-purposes/1754): 

### 2.1 Generating the funding account
The following command will create an AE account and save it in `sender.json` file inside `data`
```
aecli account create data/sender.json -P my_example_password
```

Your result will look something like this:
```
    Wallet saved
    Wallet address________________ ak_254JeRHzmiNVse7KFsqDG7L3WWEZXvCXkbSKK7hmBapWq9Uua8
    Wallet path___________________ /Users/my_user/paper-wallets/data/sender.json
```

> WARNING there is a limit related to nonces that can be submitted without errors to a node, for a successfull paperwallet session it is important to run your own node and configure the node parameter:
> ```
> mempool:
>   nonce_offset: 1000 # number of wallets you plan to create
> ``` 


### 2.2 Add some funds to your account
In order to add some funds to your account head to https://testnet.faucet.aepps.com/. Paste your wallet address (ex. `ak_254JeRHzmiNVse7KFsqDG7L3WWEZXvCXkbSKK7hmBapWq9Uua8`) and you will be given 5 AE. Do that 2-3 times.

Verify that you have your AE in your account using:
```
aecli account balance data/sender.json
```

You should see something like:
```
Enter the account password: 
<account>
  Balance ___________________________________________ 15AE
  Id ________________________________________________ ak_254JeRHzmiNVse7KFsqDG7L3WWEZXvCXkbSKK7hmBapWq9Uua8
  Kind ______________________________________________ basic
  Nonce _____________________________________________ 0
  Payable ___________________________________________ True
</account>

```

### 2.3 Get and write down your nonce
At a later stage we would need the nonce of this account. Verify that it is 0 by adjusting and running the following command:
```
aecli inspect ak_254JeRHzmiNVse7KFsqDG7L3WWEZXvCXkbSKK7hmBapWq9Uua8
```

***Note*** Change the address to your own. You can skip the -u argument for mainnet.

You should see something like this:
```
<account>
  Balance ___________________________________________ 15AE
  Id ________________________________________________ ak_254JeRHzmiNVse7KFsqDG7L3WWEZXvCXkbSKK7hmBapWq9Uua8
  Kind ______________________________________________ basic
  Nonce _____________________________________________ 0
  Payable ___________________________________________ True
</account>
```

## Step 3. Creating and funding accounts for the paper wallets
### 3.1 Create paper wallet accounts
Every paper wallet is an account itself. We need to create these paper wallet accounts first. For this we will use docker and the image `aeternity/paperwallets`. The following command will automatically download the image and create 5 accounts for your 5 paper wallets.

```
docker run -it \
--volume=$PWD/data:/data/paperw \
aeternity/paperwallets \
gen \
-n 5 \
-f /data/paperw/data.db.sqlite
```

You can easily create more/less accounts by changing the `-n` argument value.

### 3.2 Generate and broadcast paper-wallet transactions
Lets fund our paper-wallets through the wallet we created in the previous step. We need to do that in two steps - first generating fund transactions and then broadcasting them.

We will again use docker for generation of the fund transactions:

```
docker run -it \
--volume=$PWD/data:/data/paperw \
--network="host" \
--env-file .env \
aeternity/paperwallets \
txs-prepare \
-f /data/paperw/data.db.sqlite \
--amount 1ae \
--keystore /data/paperw/sender.json
```

This command will ask for your account password. If you have followed this step by step it should be `my_example_password`.

The amount parameter is how much each paper-wallet will have denominated in AE. In our case each wallet will have 1 AE

The nonce parameter should be the nonce you saw when you inspected your wallet plus one. If you want to use this on **mainnet** skip the --network-id parameter.

The result of this command should look like this:
```
top up 1AE to account ak_2nRHEtmFgmzpDBEDbceG92am1vwyaeyQSx7LHFiLrce8MXbaBk
top up 1AE to account ak_2th5G8yRaPUeSpJc3N2StwhBvnwqhGDzRmbTUSQ1aN2RVp7fC2
top up 1AE to account ak_WkjvoGDHKwMidWaTH3Z385yLAe6cx4rX5UwQUtuePMEE5KKMn
top up 1AE to account ak_pQZLHFEGgC6pNwA9KK82uEtVgme2EvxYFMhLB8pBnbyepXP3N
top up 1AE to account ak_z6QGgGpSCFc7QdV9qidH3MLpSnjT72DgcLtnjWhSnSRw5VSjM
```

The only thing we are left to do is broadcast these transactions. Docker is going to help us again here:

```
docker run -it \
--volume=$PWD/data:/data/paperw \
--network="host" \
--env-file .env \
aeternity/paperwallets \
txs-broadcast \
-f /data/paperw/data.db.sqlite
```

***Note***: If you want to use this on **mainnet** skip the --node-url parameter.

Your paper wallet accounts are funded now. The result should look something like this:

```
broadcast tx with hash: th_FBAnftx8SiiZMF55aKJwenA5mNPDHELvQRE47hT5PQtypR3DJ
broadcast tx with hash: th_um615QvmjQpM1HrBRd98rTbjj6eSoUV8oPFq7bJoxYQUZ5sGe
broadcast tx with hash: th_2fTZw8YLZMCrFP8bv7skJzt1G53BGuK55CZoVgkXAfWFheve9f
broadcast tx with hash: th_NvjdctwNtoz3j9o5RftH92jxrajYVtXb7mrm5zuDWqUh1Pptb
broadcast tx with hash: th_267ZDnT4F9yGXYoEumTuWwFUouKbybH1Nhmac2zYgNWkY3SqPt
broadcast tx with hash: th_2jCSwe9MgSkyME1SzVG989QnXEHM8imTCjXXsvX7QovEUKWoYH
broadcast tx with hash: th_2vqy5uLiMa5satF59r8szLUekCFwXbBz1HEKcWVNUfGV8L2K19
```

now you can verify that the transaction have been successful

```
docker run -it \
--volume=$PWD/data:/data/paperw \
--network="host" \
--env-file .env \
aeternity/paperwallets \
txs-verify \
-f /data/paperw/data.db.sqlite
```

that will check the balance of each account and will print something like 

```
account ak_r53SDc7BzZhxB51xT1UdA8VeQT1UywthnQvAamNQtvWi9hL1q balance: 1AE
account ak_upEwfgAER64NvJFE3WmHJzHEn7aFiHVhYhpPS3joHVNU2r2Ms balance: 1AE
account ak_wUzD2SqLRNUD93yFQrpcc2sn6M3PGSUN366cKtCZhcYu8eemQ balance: 1AE
account ak_wcFkTpSERLLxAMjPdzZi3zojLZt2VCPhBMuB9EZLXGU5xL6kf balance: 1AE
account ak_wccMom46hzqgYcQ7UmtG9SiFehfm8ynKkkubwtZYpJrhiyi5M balance: 1AE
account ak_xJUW3AFy7ZwegndbrcMMXeRFENQRAFzLoUyZyZotscTYW2U3b balance: 1AE
account ak_xh8YcbzdcBbcTyGVgzbKKTqA2QNxjbudY8Bi82RXTMEw5tM5G balance: 1AE
account ak_ypmtrdqKbC55euhUk5n3pF8giGcWspefy7U4br8i3CdMKuBSW balance: 1AE
```

## Step 4. Generate the paper wallets

### 4.1 Generate the paper wallet fronts
In order to generate the PDF paper wallets out of these accounts you can execute the following command
```
docker run -it \
--volume=$PWD/data:/data/paperw \
aeternity/paperwallets \
-f /data/paperw/data.db.sqlite \
-o /data/paperw/pdfs
```

In your `data/pdfs` directory you can now see the 5 pdf paper wallets ready to be claimed.

### 4.2 Generate the paper wallet backs
As this is only the frontside of the paper-wallets, you can find and the back-sides of the paper-wallets [here](https://github.com/aeternity/tool-paperwallets/raw/master/assets/paper-wallet-back.pdf)

## Redeeming a paper wallet
In order to redeem a paper wallet you can head to https://redeem.aepps.com/#/ or use the AirGap Vault app. You will be asked to scan the QR code and following the instructions you will be able to redeem the paper wallet.

## Conclusion
Paper wallets are a great tool to create physical wallets (existing in the real world) and use them for promotional, exchange, bounty or security purposes. Following this easy guide you can create your own unique usable AE paper wallets. The æpps team plans to enable paper wallet generation and management in an æpp. If you want this to happen faster - your are interested in developing the æpps - get in touch by sending us a mail at info@aetenrity.com or send a DM to Edward from the æpps team in the [Forum](https://forum.aeternity.com/u/edward.dikgale/summary).

*The æternity team will keep this tutorial updated. If you encounter any problems please contract us through the [æternity dev Forum category](https://forum.aeternity.com/c/development).*
