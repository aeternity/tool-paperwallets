select count(*) from wallets;

-- wallets
DROP TABLE IF EXISTS wallets;
CREATE TABLE wallets (
	private_key varchar PRIMARY KEY,
	public_key varchar not null,
	wallet_name varchar,
	balance int not null default '0',
	path varchar,
	wallet_status int not null default '10',
	id varchar,
	short_url varchar,
	long_url varchar,
	created_at datetime default CURRENT_TIMESTAMP,
	updated_at datetime default CURRENT_TIMESTAMP
	
);

DROP INDEX IF EXISTS idx1;
CREATE UNIQUE INDEX idx1 ON wallets(public_key);
DROP INDEX IF EXISTS idx2;
CREATE UNIQUE INDEX idx2 ON wallets(wallet_name);
DROP INDEX IF EXISTS idx3;
CREATE INDEX idx3 ON wallets(balance);
DROP INDEX IF EXISTS idx4;
CREATE INDEX idx4 ON wallets(wallet_status);

-- transactions
DROP TABLE IF EXISTS txs;
CREATE TABLE txs(
	public_key_from varchar not null,
	public_key_to varchar not null,
	amount int not null default 0,
	fee int not null default 0,
	ts datetime not null default CURRENT_TIMESTAMP,
	tx_hash varchar
);
DROP INDEX IF EXISTS txs_idx1;
CREATE INDEX txs_idx1 ON txs(public_key_from);
DROP INDEX IF EXISTS txs_idx2;
CREATE INDEX txs_idx2 ON txs(public_key_to);


