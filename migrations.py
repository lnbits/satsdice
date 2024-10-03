async def m001_initial(db):
    """
    Creates an improved satsdice table and migrates the existing data.
    """
    await db.execute(
        f"""
        CREATE TABLE satsdice.satsdice_pay (
            id TEXT PRIMARY KEY,
            wallet TEXT,
            title TEXT,
            min_bet INTEGER,
            max_bet INTEGER,
            amount {db.big_int} DEFAULT 0,
            served_meta INTEGER NOT NULL,
            served_pr INTEGER NOT NULL,
            multiplier FLOAT,
            haircut FLOAT,
            chance FLOAT,
            base_url TEXT,
            open_time INTEGER
        );
    """
    )


async def m002_initial(db):
    """
    Creates an improved satsdice table and migrates the existing data.
    """
    await db.execute(
        f"""
        CREATE TABLE satsdice.satsdice_withdraw (
            id TEXT PRIMARY KEY,
            satsdice_pay TEXT,
            value {db.big_int} DEFAULT 1,
            unique_hash TEXT UNIQUE,
            k1 TEXT,
            open_time INTEGER,
            used INTEGER DEFAULT 0
        );
    """
    )


async def m003_initial(db):
    """
    Creates an improved satsdice table and migrates the existing data.
    """
    await db.execute(
        f"""
        CREATE TABLE satsdice.satsdice_payment (
            payment_hash TEXT PRIMARY KEY,
            satsdice_pay TEXT,
            value {db.big_int},
            paid BOOL DEFAULT FALSE,
            lost BOOL DEFAULT FALSE
        );
    """
    )


async def m004_make_hash_check(db):
    """
    Creates a hash check table.
    """
    await db.execute(
        """
        CREATE TABLE satsdice.hash_checkw (
            id TEXT PRIMARY KEY,
            lnurl_id TEXT
        );
    """
    )


################
### Coinflip ###
################

async def m005_add_coinflip_settings(db):
    """
    Creates a hash check table.
    """
    await db.execute(
        """
        CREATE TABLE satsdice.settings (
            id TEXT PRIMARY KEY,
            page_id TEXT NOT NULL,
            wallet_id TEXT NOT NULL,
            haircut INTEGER NOT NULL,
            max_players INTEGER NOT NULL,
            max_bet INTEGER NOT NULL,
            enabled BOOLEAN NOT NULL
        );
        """
    )

async def m006_add_coinflip(db):
    """
    Creates a hash check table.
    """
    await db.execute(
        """
        CREATE TABLE satsdice.coinflip (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            number_of_players INTEGER NOT NULL,
            buy_in INTEGER NOT NULL,
            players TEXT NOT NULL,
            page_id TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT """
        + db.timestamp_now
        + """
        );
        """
    )