-- Reference schema for PostgreSQL. manage.py init-db creates it automatically.

CREATE TABLE challenges (
	id VARCHAR(64) NOT NULL, 
	contact VARCHAR(254) NOT NULL, 
	purpose VARCHAR(20) NOT NULL, 
	digest VARCHAR(64) NOT NULL, 
	payload JSON NOT NULL, 
	tries INTEGER NOT NULL, 
	expires FLOAT NOT NULL, 
	created FLOAT NOT NULL, 
	used BOOLEAN NOT NULL, 
	PRIMARY KEY (id)
)

;


CREATE TABLE oauth_flows (
	state VARCHAR(64) NOT NULL, 
	poll_hash VARCHAR(64) NOT NULL, 
	expires FLOAT NOT NULL, 
	challenge VARCHAR(64) NOT NULL, 
	used BOOLEAN NOT NULL, 
	PRIMARY KEY (state)
)

;


CREATE TABLE rate_limits (
	key VARCHAR(64) NOT NULL, 
	start FLOAT NOT NULL, 
	count INTEGER NOT NULL, 
	PRIMARY KEY (key)
)

;


CREATE TABLE users (
	id VARCHAR(12) NOT NULL, 
	username VARCHAR(24) NOT NULL, 
	name VARCHAR(80) NOT NULL, 
	email VARCHAR(254), 
	phone VARCHAR(20), 
	password VARCHAR(128) NOT NULL, 
	gender VARCHAR(30) NOT NULL, 
	avatar VARCHAR NOT NULL, 
	timezone VARCHAR(64) NOT NULL, 
	admin BOOLEAN NOT NULL, 
	coins INTEGER NOT NULL, 
	diamonds INTEGER NOT NULL, 
	unlocked INTEGER NOT NULL, 
	streak INTEGER NOT NULL, 
	last_play VARCHAR(10) NOT NULL, 
	daily_claim VARCHAR(10) NOT NULL, 
	created FLOAT NOT NULL, 
	seen FLOAT NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (username), 
	UNIQUE (email), 
	UNIQUE (phone)
)

;


CREATE TABLE attempts (
	id VARCHAR(64) NOT NULL, 
	user_id VARCHAR(12) NOT NULL, 
	level INTEGER NOT NULL, 
	board JSON NOT NULL, 
	lives INTEGER NOT NULL, 
	collisions INTEGER NOT NULL, 
	purchases INTEGER NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	started FLOAT NOT NULL, 
	finished FLOAT, 
	seconds FLOAT NOT NULL, 
	stars FLOAT NOT NULL, 
	reward VARCHAR(20) NOT NULL, 
	events JSON NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
)

;


CREATE TABLE reviews (
	user_id VARCHAR(12) NOT NULL, 
	stars INTEGER NOT NULL, 
	text VARCHAR(2000) NOT NULL, 
	updated FLOAT NOT NULL, 
	PRIMARY KEY (user_id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
)

;


CREATE TABLE rewards (
	id SERIAL NOT NULL, 
	user_id VARCHAR(12) NOT NULL, 
	key VARCHAR(100) NOT NULL, 
	coins INTEGER NOT NULL, 
	diamonds INTEGER NOT NULL, 
	created FLOAT NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (user_id, key), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
)

;


CREATE TABLE sessions (
	token VARCHAR(64) NOT NULL, 
	user_id VARCHAR(12) NOT NULL, 
	expires FLOAT NOT NULL, 
	PRIMARY KEY (token), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
)

;