CREATE TABLE users (
	id serial PRIMARY KEY,
	login varchar(32) NOT NULL UNIQUE,
	pass_hash varchar(32) NOT NULL,
	balance int8 DEFAULT 100,
	role varchar(32) NOT NULL,
	created_at timestamptz DEFAULT now()
);

CREATE TABLE calc_history (
	id serial PRIMARY KEY,
	ts timestamptz DEFAULT now(),
	user_id integer NOT NULL,
	expression text NOT NULL,
	result real NOT NULL,
	FOREIGN KEY (user_id) REFERENCES users 
);
