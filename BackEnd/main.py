import asyncio
from aiohttp import web
from api import routes
from wifi_connect import periodic_scan


@web.middleware
async def cors_middleware(request, handler):
    # Simple CORS middleware to allow requests from the frontend served on another port
    if request.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type,Authorization'
        }
        return web.Response(status=200, headers=headers)

    response = await handler(request)
    # Ensure response has CORS headers
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET,POST,PUT,DELETE,OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
    return response


async def start_background_tasks(app):
    app["wifi_task"] = asyncio.create_task(periodic_scan())


async def cleanup_background_tasks(app):
    app["wifi_task"].cancel()
    try:
        await app["wifi_task"]
    except asyncio.CancelledError:
        pass


async def init_app():
    app = web.Application(middlewares=[cors_middleware])
    app.add_routes(routes)

    # Khi server khởi động → chạy wifi scan
    app.on_startup.append(start_background_tasks)
    # Khi server tắt → dừng wifi scan
    app.on_cleanup.append(cleanup_background_tasks)

    return app


if __name__ == "__main__":
    web.run_app(init_app(), port=5000)
