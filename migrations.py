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

async def m005_add_coinflip(db):
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
            house_cut REAL NOT NULL,
            created_at INTEGER NOT NULL
        );
        """
    )

async def m006_add_coinflip_participants(db):
    """
    Creates a hash check table.
    """
    await db.execute(
        """
        CREATE TABLE satsdice.coinflip_participants (
            id TEXT PRIMARY KEY,
            coinflip_id TEXT NOT NULL,
            lnaddress TEXT NOT NULL,
            paid BOOLEAN NOT NULL,
            FOREIGN KEY (coinflip_id) REFERENCES coinflip(id)
        );
        """
    )

async def m007_add_coinflip_settings(db):
    """
    Creates a hash check table.
    """
    await db.execute(
        """
        CREATE TABLE satsdice.settings (
            key TEXT PRIMARY KEY,
            value JSONB
        );
        """
    )