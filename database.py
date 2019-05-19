import logging
from variables import DB_NAME, DB_USERNAME, DB_PASSWORD
from aiopg.sa import create_engine
from sqlalchemy.schema import CreateTable
import sqlalchemy as sa

logging.basicConfig(level=logging.INFO)


meta = sa.MetaData()

Member = sa.Table(
    'members', meta,
    sa.Column('id', sa.BigInteger, primary_key=True, nullable=False),
    sa.Column('member', sa.BigInteger, nullable=False),
    sa.Column('wallet', sa.BigInteger, default=0, nullable=False),
    sa.Column('last_dailies', sa.DateTime),
    sa.Column('last_reward', sa.DateTime),
    sa.Column('tier', sa.SmallInteger, server_default='0'),
    sa.Column('level', sa.BigInteger, nullable=False, server_default='0')
)

Guild = sa.Table(
    'guild', meta,
    sa.Column('id', sa.BigInteger, primary_key=True, nullable=False),
    sa.Column('guild', sa.BigInteger, nullable=False),
    sa.Column('shop_roles', sa.JSON),
    sa.Column('music_enabled', sa.Boolean),
    sa.Column('coin_drops', sa.Boolean, server_default='f', nullable=False),
    sa.Column('join_leave_channel', sa.BigInteger),
    sa.Column('welcome_str', sa.String(length=60), server_default="Let the madness begin. Hold tight."),
    sa.Column('leave_str', sa.String(length=60), server_default="See you again, in another life."),
    sa.Column('custom_role', sa.BigInteger, server_default="40000"),
)

tables = [Member, Guild]

engine = None


async def prepare_engine():
    global engine
    if engine is None:
        engine = await create_engine(
            database=DB_NAME,
            user=DB_USERNAME,
            password=DB_PASSWORD,
            host='127.0.0.1',
            maxsize=25,
        )
    return engine


async def prepare_tables():
    engine = await prepare_engine()
    async with engine.acquire() as conn:
        for table in tables:
            table_name = table.name
            query = """
            SELECT * FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_NAME = N'{}'""".format(table_name)
            cursor = await conn.execute(query)
            resp = await cursor.fetchall()
            if resp is None or resp == []:
                logging.info("Table {} does not exist; creating.".format(table_name))
                create_expr = CreateTable(table)
                await conn.execute(create_expr)
            else:
                logging.info("Table {} already exists.".format(table_name))


async def make_member_profile(members_list, self_id):
        engine = await prepare_engine()
        async with engine.acquire() as conn:
            create_query_values = []
            for member in members_list:
                if member.id == self_id:
                    continue
                exists_query = Member.select().where(
                    Member.c.member == member.id)
                cursor = await conn.execute(exists_query)
                res = await cursor.fetchall()
                if res is None or res == []:
                    create_query_values.append({
                        'member': member.id,
                        'wallet': 0,
                    })
                    logging.info('Creating profile for member {}.'.format(member.name))
            if len(create_query_values) > 0:
                create_query = Member.insert().values(create_query_values)
                await conn.execute(create_query)


async def make_guild_entry(guilds_list):
        engine = await prepare_engine()
        async with engine.acquire() as conn:
            create_query_values = []
            for guild in guilds_list:
                exists_query = Guild.select().where(
                    Guild.c.guild == guild.id)
                cursor = await conn.execute(exists_query)
                res = await cursor.fetchall()
                if res is None or res == []:
                    create_query_values.append({
                        'guild': guild.id,
                    })
                    logging.info('Creating entry for guild {}.'.format(guild.name))
            if len(create_query_values) > 0:
                create_query = Guild.insert().values(create_query_values)
                await conn.execute(create_query)


"""
async def insert_data(engine, table, values):
    async with engine.acquire() as conn:
        query = table.insert().values(values).returning(table.c.id)
        cursor = await conn.execute(query)
        resp = await cursor.fetchall()
    return [r[0] for r in resp]
"""
