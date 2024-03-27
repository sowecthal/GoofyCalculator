import asyncio
import toml

async def main():
    config = toml.load('ConfigServerCalculator.toml')
    host = config['SERVER']['host'] 
    port = config['SERVER']['port']

    reader, writer = await asyncio.open_connection(host, port)

    while True:
        try:
            command = input('Enter your command: ')
            writer.write(command.encode('ascii'))
            await writer.drain()

            response = await reader.read(1024)
            print(response.decode('ascii'))
        except KeyboardInterrupt:
            print('Client stopped working')
            break

if __name__ == '__main__':
    asyncio.run(main())
