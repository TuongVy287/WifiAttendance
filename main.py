import asyncio
from aiohttp import web
from api import routes
from wifi_connect import periodic_scan


async def start_background_tasks(app):
    app["wifi_task"] = asyncio.create_task(periodic_scan())


async def cleanup_background_tasks(app):
    app["wifi_task"].cancel()
    try:
        await app["wifi_task"]
    except asyncio.CancelledError:
        pass


async def init_app():
    app = web.Application()
    app.add_routes(routes)

    # Khi server khởi động → chạy wifi scan
    app.on_startup.append(start_background_tasks)
    # Khi server tắt → dừng wifi scan
    app.on_cleanup.append(cleanup_background_tasks)

    return app


if __name__ == "__main__":
    web.run_app(init_app(), port=5000)
