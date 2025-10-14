from aiohttp import web
from api import routes

app = web.Application()
app.add_routes(routes)

if __name__ == "__main__":
    web.run_app(app, port=5000)
