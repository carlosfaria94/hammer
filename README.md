# Hammer

Fork from https://github.com/drandreaskrueger/chainhammer to work with Pantheon.

## Requirements

- Python >= 3.6

## Install dependencies using virtualenv

```
sudo pip3 install virtualenv
virtualenv -p python3 venv
source venv/bin/activate
pip3 install -r requirements.txt
```

## Configuration

Create a `.env` with the following environment variables:

- Set the `MNEMONIC`; used to initiate accounts and sign transactions
- Set the `RPC_NODE_SEND`; node used to flood the network with transactions
- Set the `RPC_NODE_WATCH`; node used to observe and analyze each block TPS (transactions per second)

## Quickstart

0. Node up and running?

```
source venv/bin/activate
hammer/is_up.py
```

1. Deploy `Storage` contract:

```
hammer/deploy.py
```

2. Start TPS measuring

**NOTE:** Start a new terminal session.

```
source venv/bin/activate
hammer/measure_tps.py
```

3. Flood the network with transactions

Use the first 3 accounts to broadcast 100 transactions.

**NOTE:** The first account (index 0) needs to have funds. It will then send 5 ETH to each new account.

```
source venv/bin/activate
hammer/send.py 100 accounts 3
```
