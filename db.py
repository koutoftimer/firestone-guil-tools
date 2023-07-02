import logging
import sqlite3
from typing import Iterable

DB_FILENAME = './guild.db'


def save_donations_to_db(data: dict[str, int]):
    logging.info(f'Updating donations: {data}')
    update_member_status(data.keys())
    create_table = '''
    CREATE TABLE IF NOT EXISTS donations (
        user_id INTEGER NOT NULL,
        donation INTEGER NOT NULL,
        timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
        id INTEGER PRIMARY KEY ASC,
        FOREIGN KEY(user_id) REFERENCES user(id)
    )
    '''
    conn = sqlite3.connect(DB_FILENAME)
    cur = conn.cursor()
    cur.execute(create_table)
    cur.executemany(
        '''
        INSERT INTO donations (user_id, donation)
        VALUES ((SELECT id FROM users WHERE nickname = ?), ?)
        ''',
        tuple(data.items()),
    )
    conn.commit()


def update_member_status(active_members: Iterable[str]):
    create_table = '''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY ASC,
        nickname TEXT UNIQUE NOT NULL,
        status TEXT NOT NULL,
        changed_at NOT NULL DEFAULT CURRENT_TIMESTAMP,
        created_at NOT NULL DEFAULT CURRENT_TIMESTAMP,
        comment TEXT
    )
    '''
    conn = sqlite3.connect(DB_FILENAME)
    cur = conn.cursor()
    cur.execute(create_table)

    # mark active member as leavers
    user_list = ','.join(f'"{v}"' for v in active_members)
    cur.execute(
        'UPDATE users SET status = "left" '
        f'WHERE users.status = "active" AND users.nickname NOT IN ({user_list})'
    )
    # add new members
    cur.executemany(
        'INSERT OR IGNORE INTO users (nickname, status) VALUES (?, "active")',
        zip(active_members),
    )
    # activate existing members
    cur.executemany(
        'UPDATE users SET status = "active" WHERE users.nickname = ?',
        zip(active_members),
    )
    conn.commit()


# Migrations


def alter_users_table():
    migration = '''
    -- Add changed_at and created_at columns to users table
    BEGIN;

    -- Create temporary table
    CREATE TABLE IF NOT EXISTS users_new (
        id INTEGER PRIMARY KEY ASC,
        nickname TEXT UNIQUE NOT NULL,
        status TEXT NOT NULL,
        changed_at NOT NULL DEFAULT CURRENT_TIMESTAMP,
        created_at NOT NULL DEFAULT CURRENT_TIMESTAMP,
        comment TEXT
    );

    -- Data migration
    INSERT INTO users_new (id, nickname, status, comment)
        SELECT * FROM users;

    -- Replace temporary table with original
    DROP TABLE users;
    ALTER TABLE users_new RENAME TO users;

    -- Set correct creation time (this is correct only now)
    UPDATE users
       SET created_at = (SELECT min(timestamp) FROM donations WHERE user_id = users.id),
           changed_at = ifnull(
               (SELECT min(timestamp)
                 FROM donations
                WHERE timestamp > (
                    SELECT max(timestamp)
                      FROM (
                         SELECT timestamp, group_concat('<' || user_id || '>') as members
                           FROM donations
                         GROUP BY timestamp
                      )
                     WHERE members NOT LIKE '%<' || users.id || '>%'
                )),
                (SELECT min(timestamp) FROM donations WHERE user_id = users.id)
           );

    -- changed_at differes for those who left
    UPDATE users
       SET changed_at = (
           SELECT max(timestamp) FROM donations WHERE user_id = users.id
       )
     WHERE status = "left";


    -- Add trigger to update changed_at field
    CREATE TRIGGER IF NOT EXISTS update_users_changed_at
           BEFORE UPDATE
               ON users
    BEGIN
        UPDATE users
           SET changed_at = CURRENT_TIMESTAMP
         WHERE old.id = id;
    END;

    END;
    '''
    conn = sqlite3.connect(DB_FILENAME)
    cur = conn.cursor()
    cur.executescript(migration)


if __name__ == "__main__":
    alter_users_table()
