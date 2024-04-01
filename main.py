import asyncio
import logging
import toml

from lib.database import Database 
from lib.commandHandler import CommandHandler
from lib.clientHandler import handleClient

async def main():
    config = toml.load('etc/ConfigServerCalculator.toml')
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(name)s] [%(levelname)s] > %(message)s')

    db = Database(config)
    await db.createPool()

    processed_users = {}
    
    command_handler = CommandHandler(db, processed_users)
    
    server = await asyncio.start_server(
        lambda r, w: handleClient(r, w, command_handler),
        config['SERVER']['host'],
        config['SERVER']['port']
    )

    logging.info(f'Server started. Listening on port {config["SERVER"]["port"]}...')

    try:
        await server.serve_forever()
    except KeyboardInterrupt:
        logging.info('Server shutting down...')
        server.close()
        await server.wait_closed()

if __name__ == '__main__':
    asyncio.run(main())