CREATE TYPE role_type AS ENUM (
    'USER',
    'ADMIN'
);

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    login VARCHAR(32) NOT NULL UNIQUE,
    pass_hash VARCHAR(32) NOT NULL,
    balance INTEGER DEFAULT 100,
    role role_type DEFAULT 'USER',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO users (login, pass_hash, role) VALUES ('admin', '21232f297a57a5a743894a0e4a801fc3', 'ADMIN');

CREATE TABLE calc_history (
    id SERIAL PRIMARY KEY,
    ts TIMESTAMPTZ DEFAULT NOW(),
    user_id INTEGER NOT NULL,
    expression TEXT NOT NULL,
    result REAL NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users
);
