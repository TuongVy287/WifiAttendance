from aiohttp import web
from datetime import datetime, timedelta
from bson import ObjectId
from db_connect import (
    sinhvien_col, thietbi_col, caidat_col, diemdanh_col, dangnhap_col,
    get_all, get_by_id, insert_one, update_one, delete_one
)

routes = web.RouteTableDef()

# ===============================
# 🔹 1. SINH VIÊN
# ===============================

@routes.get("/sinhvien")
async def get_all_sinhvien(request):
    data = await get_all(sinhvien_col)
    return web.json_response(data)

@routes.get("/sinhvien/{id}")
async def get_sinhvien_by_id(request):
    id = request.match_info["id"]
    sv = await get_by_id(sinhvien_col, id)
    if not sv:
        return web.json_response({"message": "Không tìm thấy"}, status=404)
    return web.json_response(sv)

@routes.post("/sinhvien")
async def add_sinhvien(request):
    data = await request.json()
    ten = data.get("Ten")
    mssv = data.get("MSSV")

    if not ten or not mssv:
        return web.json_response({"message": "Thiếu thông tin tên hoặc MSSV"}, status=400)

    existing = await sinhvien_col.find_one({"MSSV": mssv})
    if existing:
        return web.json_response({"message": f"MSSV '{mssv}' đã tồn tại"}, status=409)

    sinhvien = {"Ten": ten, "MSSV": mssv, "Is_active": True}
    await insert_one(sinhvien_col, sinhvien)
    return web.json_response({"message": "Thêm sinh viên thành công"}, status=201)

@routes.put("/sinhvien/{id}")
async def update_sinhvien(request):
    id = request.match_info["id"]
    data = await request.json()
    await update_one(sinhvien_col, id, data)
    return web.json_response({"message": "Cập nhật thành công"})

@routes.delete("/sinhvien/{id}")
async def delete_sinhvien(request):
    id = request.match_info["id"]
    await delete_one(sinhvien_col, id)
    return web.json_response({"message": "Xóa thành công"})


# ===============================
# 🔹 2. THIẾT BỊ
# ===============================
@routes.post("/thietbi")
async def add_thietbi(request):
    data = await request.json()
    sinhvien_id = data.get("SinhVien_id")
    mac = data.get("MAC")
    ten_tb = data.get("Ten_ThietBi")

    if not sinhvien_id or not mac or not ten_tb:
        return web.json_response({"message": "Thiếu dữ liệu!"}, status=400)

    try:
        sv_obj_id = ObjectId(sinhvien_id)
    except:
        return web.json_response({"message": "SinhVien_id không hợp lệ!"}, status=400)

    sinhvien = await sinhvien_col.find_one({"_id": sv_obj_id})
    if not sinhvien:
        return web.json_response({"message": "Không tồn tại sinh viên!"}, status=404)

    existing_mac = await thietbi_col.find_one({"MAC": mac})
    if existing_mac:
        return web.json_response({"message": f"MAC '{mac}' đã tồn tại!"}, status=409)

    # Tắt các thiết bị cũ
    await thietbi_col.update_many({"SinhVien_id": sv_obj_id}, {"$set": {"Is_active": False}})

    new_tb = {
        "SinhVien_id": sv_obj_id,
        "MAC": mac,
        "TD_Them_ThietBi": datetime.now(),
        "Ten_ThietBi": ten_tb,
        "Is_active": True
    }
    await insert_one(thietbi_col, new_tb)
    return web.json_response({"message": "Thêm thiết bị thành công!"}, status=201)


@routes.get("/thietbi")
async def get_all_thietbi(request):
    data = await get_all(thietbi_col)
    return web.json_response(data)

@routes.get("/thietbi/{id}")
async def get_thietbi(request):
    id = request.match_info["id"]
    tb = await get_by_id(thietbi_col, id)
    if tb:
        return web.json_response(tb)
    return web.json_response({"message": "Không tìm thấy thiết bị!"}, status=404)


@routes.put("/thietbi/{id}")
async def update_thietbi(request):
    id = request.match_info["id"]
    data = await request.json()

    tb = await thietbi_col.find_one({"_id": ObjectId(id)})
    if not tb:
        return web.json_response({"message": "Không tìm thấy thiết bị!"}, status=404)

    if "SinhVien_id" in data:
        return web.json_response({"message": "Không được phép thay đổi SinhVien_id!"}, status=400)

    sinhvien_id = tb["SinhVien_id"]
    await thietbi_col.update_many({"SinhVien_id": sinhvien_id, "_id": {"$ne": ObjectId(id)}},
                                  {"$set": {"Is_active": False}})

    data["TD_Them_ThietBi"] = datetime.now()
    data["Is_active"] = True

    await update_one(thietbi_col, id, data)
    return web.json_response({"message": "Cập nhật thành công!"})


@routes.delete("/thietbi/{id}")
async def delete_thietbi(request):
    id = request.match_info["id"]
    tb = await thietbi_col.find_one({"_id": ObjectId(id)})
    if not tb:
        return web.json_response({"message": "Không tìm thấy thiết bị!"}, status=404)

    sinhvien_id = tb["SinhVien_id"]
    await delete_one(thietbi_col, id)

    latest = await thietbi_col.find_one({"SinhVien_id": sinhvien_id}, sort=[("TD_Them_ThietBi", -1)])
    if latest:
        await thietbi_col.update_one({"_id": latest["_id"]}, {"$set": {"Is_active": True}})

    return web.json_response({"message": "Xóa thiết bị thành công!"})



# ===============================
# 🔹 3. CÀI ĐẶT
# ===============================
@routes.post("/caidat")
async def add_caidat(request):
    data = await request.json()
    buoi = data.get("Buoi")
    if not buoi:
        return web.json_response({"message": "Thiếu thông tin Buổi!"}, status=400)

    # Tắt cấu hình cũ cùng buổi
    await caidat_col.update_many({"Buoi": buoi}, {"$set": {"Is_active": False}})

    new_cd = {
        "Buoi": buoi,
        "TD_BatDau": data.get("TD_BatDau"),
        "TD_KetThuc": data.get("TD_KetThuc"),
        "TD_Reset": data.get("TD_Reset"),
        "Mail": data.get("Mail"),
        "TG_DiTre": data.get("TG_DiTre"),
        "TD_Setting": datetime.now(),
        "Is_active": True
    }
    await insert_one(caidat_col, new_cd)
    return web.json_response({"message": "Thêm cài đặt thành công!"}, status=201)


@routes.get("/caidat")
async def get_all_caidat(request):
    data = await get_all(caidat_col)
    return web.json_response(data)


@routes.get("/caidat/{id}")
async def get_caidat(request):
    id = request.match_info["id"]
    cd = await get_by_id(caidat_col, id)
    if cd:
        return web.json_response(cd)
    return web.json_response({"message": "Không tìm thấy cài đặt!"}, status=404)


@routes.put("/caidat/{id}")
async def update_caidat(request):
    id = request.match_info["id"]
    data = await request.json()
    await update_one(caidat_col, id, data)
    return web.json_response({"message": "Cập nhật thành công!"})


@routes.delete("/caidat/{id}")
async def delete_caidat(request):
    id = request.match_info["id"]
    await delete_one(caidat_col, id)
    return web.json_response({"message": "Xóa thành công!"})

# ===============================
# 🔹 4. ĐIỂM DANH
# ===============================
def xac_dinh_buoi():
    hour = datetime.now().hour
    if hour < 12:
        return "Sáng"
    elif hour < 15:
        return "Chiều"
    else:
        return "Tối"

@routes.post("/diemdanh")
async def diemdanh(request):
    data = await request.json()
    mac = data.get("MAC")

    if not mac:
        return web.json_response({"message": "Thiếu địa chỉ MAC!"}, status=400)

    # Lấy thiết bị theo MAC
    thietbi = await thietbi_col.find_one({"MAC": mac})
    if not thietbi:
        # Thiết bị khách (chưa đăng ký)
        return web.json_response({"message": "Thiết bị khách - chưa đăng ký trong hệ thống!", "Ten_SinhVien": "Khách"}, status=403)

    # Kiểm tra trạng thái thiết bị
    if not thietbi.get("Is_active", False):
        return web.json_response({"message": "Thiết bị đã bị vô hiệu hóa!"}, status=403)

    # Lấy thông tin sinh viên
    sinhvien = await sinhvien_col.find_one({"_id": thietbi["SinhVien_id"]})
    ten_sv = sinhvien["Ten"] if sinhvien else "Khách"

    # Xác định buổi hiện tại và lấy cấu hình đang active cho buổi đó
    buoi = xac_dinh_buoi()
    caidat = await caidat_col.find_one({"Buoi": buoi, "Is_active": True})
    if not caidat:
        return web.json_response({"message": f"Không có cài đặt cho buổi {buoi}!"}, status=404)

    # Chuyển các mốc thời gian từ cấu hình
    try:
        TD_BatDau = datetime.combine(datetime.today(), datetime.strptime(caidat["TD_BatDau"], "%H:%M").time())
        TD_KetThuc = datetime.combine(datetime.today(), datetime.strptime(caidat["TD_KetThuc"], "%H:%M").time())
    except Exception:
        # Nếu dữ liệu thời gian không hợp lệ
        return web.json_response({"message": "Dữ liệu thời gian trong cài đặt không hợp lệ!"}, status=500)

    TG_DiTre = timedelta(minutes=int(caidat.get("TG_DiTre", 0))) if caidat.get("TG_DiTre") is not None else timedelta(minutes=0)
    now = datetime.now()

    # Tìm bản ghi điểm danh cùng MAC + Buổi trong ngày hôm nay (TD_Vao >= ngày hôm nay 00:00)
    today = datetime.now().date()
    start_of_today = datetime(today.year, today.month, today.day)
    record = await diemdanh_col.find_one({
        "MAC": mac,
        "Buoi": buoi,
        "TD_Vao": {"$gte": start_of_today}
    })
    # Nếu chưa có bản ghi → tạo mới (ghi giờ vào + giờ ra = giờ hiện tại)
    if not record:
        TD_Vao = now
        TD_Ra = now
        if TD_Vao <= TD_BatDau:
            trangthai = "Có mặt"
        elif TD_Vao <= (TD_BatDau + TG_DiTre):
            trangthai = "Đi trễ"
        else:
            trangthai = "Vắng"
        new_record = {
            "TD_Vao": TD_Vao,
            "TD_Ra": TD_Ra,
            "Buoi": buoi,
            "MAC": mac,
            "Ten_SinhVien": ten_sv,
            "TrangThai": trangthai
        }
        await insert_one(diemdanh_col, new_record)
        return web.json_response({
            "Ten_SinhVien": ten_sv,
            "TrangThai": trangthai,
            "Buoi": buoi
        }, status=201)

    # Nếu đã có bản ghi → cập nhật giờ ra
    else:
        TD_Ra = now
        trangthai = record.get("TrangThai", "")
        # Nếu không vắng → kiểm tra về sớm
        if trangthai != "Vắng" and TD_Ra < TD_KetThuc:
            trangthai = f"{trangthai} - Về sớm"
        await diemdanh_col.update_one(
            {"_id": record["_id"]},
            {"$set": {"TD_Ra": TD_Ra, "TrangThai": trangthai}}
        )
        return web.json_response({
            "message": f"Đã cập nhật giờ ra (buổi {buoi})!",
            "Ten_SinhVien": ten_sv,
            "TrangThai": trangthai,
            "Buoi": buoi
        }, status=200)

@routes.get("/diemdanh")
async def get_all_diemdanh(request):
    data = await get_all(diemdanh_col)
    return web.json_response(data)

@routes.get("/diemdanh/{id}")
async def get_diemdanh(request):
    id = request.match_info["id"]
    dd = await get_by_id(diemdanh_col, id)
    if dd:
        return web.json_response(dd)
    return web.json_response({"error": "Không tìm thấy"}, status=404)

@routes.put("/diemdanh/{id}")
async def update_diemdanh(request):
    id = request.match_info["id"]
    data = await request.json()
    await update_one(diemdanh_col, id, data)
    return web.json_response({"message": "Cập nhật thành công!"})

@routes.delete("/diemdanh/{id}")
async def delete_diemdanh(request):
    id = request.match_info["id"]
    await delete_one(diemdanh_col, id)
    return web.json_response({"message": "Xóa thành công!"})

# ===============================
# 🔹 5. ĐĂNG NHẬP
# ===============================
@routes.post("/dangnhap")
async def add_user(request):
    data = await request.json()
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return web.json_response({"message": "Vui lòng nhập username và password!"}, status=400)

    exist = await dangnhap_col.find_one({"username": username})
    if exist:
        return web.json_response({"message": "Username đã tồn tại!"}, status=409)

    user = {
        "username": username,
        "password": password,
        "Is_active": True
    }
    await insert_one(dangnhap_col, user)
    return web.json_response({"message": "Tạo tài khoản thành công!"}, status=201)
@routes.get("/dangnhap")
async def get_all_user(request):
    users = await get_all(dangnhap_col)
    return web.json_response(users)
@routes.get("/dangnhap/{id}")
async def get_user(request):
    id = request.match_info["id"]
    user = await get_by_id(dangnhap_col, id)
    if user:
        return web.json_response(user)
    return web.json_response({"message": "Không tìm thấy người dùng!"}, status=404)
@routes.put("/dangnhap/{id}")
async def update_user(request):
    id = request.match_info["id"]
    data = await request.json()
    await update_one(dangnhap_col, id, data)
    return web.json_response({"message": "Cập nhật thành công!"})
@routes.delete("/dangnhap/{id}")
async def delete_user(request):
    id = request.match_info["id"]
    await delete_one(dangnhap_col, id)
    return web.json_response({"message": "Xóa thành công!"})