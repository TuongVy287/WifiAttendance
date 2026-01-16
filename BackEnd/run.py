# run.py - Đặt trong thư mục BackEnd/
import os
import asyncio
import webbrowser
from aiohttp import web

# === Kiểm tra file cần thiết ===
required = ['api.py', 'db_connect.py', 'wifi_connect.py']
missing = [f for f in required if not os.path.exists(f)]
if missing:
    print("LỖI: Thiếu file trong BackEnd/:")
    for f in missing:
        print(f"  - {f}")
    exit(1)

# === Import từ cùng thư mục ===
from api import routes
from wifi_connect import periodic_scan

# === Đường dẫn đến index.html ===
FRONTEND_PATH = os.path.join(os.path.dirname(__file__), "..", "FrontEnd", "index.html")

if not os.path.exists(FRONTEND_PATH):
    print(f"LỖI: Không tìm thấy index.html tại {FRONTEND_PATH}")
    exit(1)

# === CORS Middleware ===
@web.middleware
async def cors_middleware(request, handler):
    if request.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type,Authorization'
        }
        return web.Response(status=200, headers=headers)
    response = await handler(request)
    response.headers.update({
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type,Authorization'
    })
    return response

# === Serve frontend ===
async def serve_index(request):
    return web.FileResponse(FRONTEND_PATH)

# === Background tasks ===
async def start_background_tasks(app):
    app["wifi_task"] = asyncio.create_task(periodic_scan())

async def cleanup_background_tasks(app):
    if "wifi_task" in app:
        app["wifi_task"].cancel()
        try:
            await app["wifi_task"]
        except asyncio.CancelledError:
            pass

# === Chạy server ===
if __name__ == "__main__":
    print("Khởi động WiFi Attendance System...")
    print("Frontend: file://..." + FRONTEND_PATH.replace("\\", "/"))
    print("API: http://192.168.10.29:5000")
    print("Mở trình duyệt ngay lập tức...\n")

    # Tạo app
    app = web.Application(middlewares=[cors_middleware])
    app.add_routes(routes)
    app.router.add_get('/', serve_index)
    app.router.add_get('/index.html', serve_index)
    app.on_startup.append(start_background_tasks)
    app.on_cleanup.append(cleanup_background_tasks)

    # Mở trình duyệt NGAY LẬP TỨC
    webbrowser.open('http://192.168.10.29:5000')

    try:
        web.run_app(app, port=5000)
    except KeyboardInterrupt:
        print("\nDừng server...")