from aiohttp import web
from datetime import datetime, timedelta
from bson import ObjectId
from db_connect import (
    sinhvien_col, thietbi_col, caidat_col, diemdanh_col, dangnhap_col,
    get_all, get_by_id, insert_one, update_one, delete_one
)
from wifi_connect import xac_dinh_buoi  # ← THÊM IMPORT NÀY

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
    inserted_id = await insert_one(sinhvien_col, sinhvien)
    
    # ### SỬA MỚI: Sinh viên mới thêm mặc định True, nên nếu có thiết bị (thường không), set true
    sv_obj_id = ObjectId(inserted_id)
    await thietbi_col.update_many({"SinhVien_id": sv_obj_id}, {"$set": {"Is_active": True}})

    return web.json_response({"message": "Thêm sinh viên thành công"}, status=201)

@routes.put("/sinhvien/{id}")
async def update_sinhvien(request):
    id = request.match_info["id"]
    data = await request.json()
    await update_one(sinhvien_col, id, data)
    
    # ### SỬA MỚI: Lấy sinh viên sau update để biết Is_active mới
    sv = await sinhvien_col.find_one({"_id": ObjectId(id)})
    if sv:
        new_active = sv.get("Is_active", False)
        sv_obj_id = ObjectId(id)
        await thietbi_col.update_many({"SinhVien_id": sv_obj_id}, {"$set": {"Is_active": new_active}})
    
    return web.json_response({"message": "Cập nhật thành công"})

@routes.delete("/sinhvien/{id}")
async def delete_sinhvien(request):
    id = request.match_info["id"]
    sv_obj_id = ObjectId(id)
    
    # ### SỬA MỚI: Trước khi xóa, set tất cả thiết bị false (vì sinh viên bị xóa ≡ không active)
    await thietbi_col.update_many({"SinhVien_id": sv_obj_id}, {"$set": {"Is_active": False}})
    
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

    # ### SỬA MỚI: Deactivate các thiết bị khác, nhưng set new_tb theo Is_active của sinh viên
    await thietbi_col.update_many({"SinhVien_id": sv_obj_id}, {"$set": {"Is_active": False}})
    
    sv_active = sinhvien.get("Is_active", False)  # Theo trạng thái sinh viên
    new_tb = {
        "SinhVien_id": sv_obj_id,
        "MAC": mac,
        "TD_Them_ThietBi": datetime.now(),
        "Ten_ThietBi": ten_tb,
        "Is_active": sv_active  # ### SỬA MỚI: Theo sinh viên, không mặc định True
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

    sinhvien_id = tb["SinhVien_id"]
    await thietbi_col.update_many({"SinhVien_id": sinhvien_id, "_id": {"$ne": ObjectId(id)}},
                                  {"$set": {"Is_active": False}})

    data["TD_Them_ThietBi"] = datetime.now()
    
    # ### SỬA MỚI: Set Is_active theo sinh viên hiện tại, không mặc định True
    sinhvien = await sinhvien_col.find_one({"_id": sinhvien_id})
    if sinhvien:
        data["Is_active"] = sinhvien.get("Is_active", False)
    else:
        data["Is_active"] = False  # Nếu sinh viên không tồn tại

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

# =============================== 
# 🔹 3. CÀI ĐẶT 
# =============================== 

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

@routes.post("/caidat") 
async def add_caidat(request): 
    data = await request.json() 
    buoi = data.get("Buoi") 
    td_batdau = data.get("TD_BatDau") 
    td_ketthuc = data.get("TD_KetThuc") 
    tg_ditre = data.get("TG_DiTre") 

    if not buoi or not td_batdau or not td_ketthuc: 
        return web.json_response({"message": "Thiếu dữ liệu!"}, status=400) 

    existing = await caidat_col.find_one({"Buoi": buoi}) 
    if existing: 
        return web.json_response({"message": f"Buổi '{buoi}' đã tồn tại!"}, status=409) 

    caidat = { 
        "Buoi": buoi, 
        "TD_BatDau": td_batdau, 
        "TD_KetThuc": td_ketthuc, 
        "TG_DiTre": tg_ditre, 
        "Is_active": True 
    } 
    await insert_one(caidat_col, caidat) 
    return web.json_response({"message": "Thêm cài đặt thành công!"}, status=201) 

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
    return web.json_response({"message": "Không tìm thấy điểm danh!"}, status=404) 

@routes.put("/diemdanh/{id}")
async def update_diemdanh(request):
    id = request.match_info["id"]
    data = await request.json()

    # Kiểm tra ID hợp lệ
    try:
        obj_id = ObjectId(id)
    except:
        return web.json_response({"message": "ID không hợp lệ!"}, status=400)

    # Lấy bản ghi hiện tại
    record = await diemdanh_col.find_one({"_id": obj_id})
    if not record:
        return web.json_response({"message": "Không tìm thấy bản ghi điểm danh!"}, status=404)

    # Lấy dữ liệu mới từ request
    td_vao_str = data.get("TD_Vao")  # format: "HH:MM"
    td_ra_str = data.get("TD_Ra")    # có thể null
    buoi = record["Buoi"]

    # Sửa lỗi: Lấy ngày từ "Ngay" hoặc từ "TD_Vao" nếu thiếu
    ngay = record.get("Ngay")
    if not ngay:
        if "TD_Vao" in record and record["TD_Vao"]:
            ngay = record["TD_Vao"].strftime("%Y-%m-%d")
        else:
            ngay = datetime.today().strftime("%Y-%m-%d")

    # Tìm cài đặt buổi
    caidat = await caidat_col.find_one({"Buoi": buoi, "Is_active": True})
    if not caidat:
        return web.json_response({"message": f"Không có cài đặt cho buổi {buoi}!"}, status=400)

    TD_BatDau = datetime.strptime(caidat["TD_BatDau"], "%H:%M").time()
    TD_KetThuc = datetime.strptime(caidat["TD_KetThuc"], "%H:%M").time()
    TG_DiTre = timedelta(minutes=int(caidat.get("TG_DiTre", 0)))

    # Chuyển đổi thời gian
    try:
        td_vao_time = datetime.strptime(td_vao_str, "%H:%M").time() if td_vao_str else None
        td_ra_time = datetime.strptime(td_ra_str, "%H:%M").time() if td_ra_str else None
    except:
        return web.json_response({"message": "Định dạng giờ không hợp lệ! Dùng HH:MM"}, status=400)

    # Tạo datetime đầy đủ
    today = datetime.strptime(ngay, "%Y-%m-%d").date()
    td_vao_dt = datetime.combine(today, td_vao_time) if td_vao_time else None
    td_ra_dt = datetime.combine(today, td_ra_time) if td_ra_time else None

    # Tính trạng thái Check-in
    batdau_dt = datetime.combine(today, TD_BatDau)
    ketthuc_dt = datetime.combine(today, TD_KetThuc)

    trangthai_vao = "Có mặt"
    if td_vao_dt < batdau_dt + TG_DiTre:
        trangthai_vao = "Đi trễ"
    elif td_vao_dt < ketthuc_dt:
        trangthai_vao = "Vắng"

    # Tính trạng thái Check-out
    trangthai_ra = ""
    if td_ra_dt:
        if td_ra_dt < ketthuc_dt and trangthai_vao not in ["Vắng"]:
            trangthai_ra = "Về sớm"
        else:
            trangthai_ra = ""  # Không thêm nếu ra đúng giờ hoặc muộn

    # Kết hợp trạng thái
    trangthai_ket_hop = trangthai_vao
    if trangthai_ra:
        trangthai_ket_hop += f" - {trangthai_ra}"

    # Cập nhật bản ghi
    update_data = {
        "TD_Vao": td_vao_dt,
        "TD_Ra": td_ra_dt,
        "TrangThai": trangthai_ket_hop
    }

    await diemdanh_col.update_one({"_id": obj_id}, {"$set": update_data})

    return web.json_response({
        "message": "Cập nhật điểm danh thành công!",
        "Ten_SinhVien": record["Ten_SinhVien"],
        "TD_Vao": td_vao_str or "",
        "TD_Ra": td_ra_str or "Chưa ra",
        "TrangThai": trangthai_ket_hop,
        "Buoi": buoi
    })

@routes.delete("/diemdanh/{id}")
async def delete_diemdanh(request):
    id = request.match_info["id"]
    await delete_one(diemdanh_col, id)
    return web.json_response({"message": "Xóa thành công!"})

@routes.post("/diemdanh") 
async def diemdanh(request): 
    data = await request.json() 
    mac = data.get("MAC") 
    ly_do = data.get("LyDo")   # ← THÊM MỚI: Lý do thủ công 

    if not mac: 
        return web.json_response({"message": "Thiếu địa chỉ MAC!"}, status=400) 

    thietbi = await thietbi_col.find_one({"MAC": mac}) 
    if not thietbi: 
        return web.json_response({ 
            "message": "Thiết bị không hợp lệ hoặc đã bị vô hiệu hóa!", 
            "Ten_SinhVien": "Khách" 
        }, status=403) 

    sinhvien = await sinhvien_col.find_one({"_id": thietbi["SinhVien_id"]}) 
    ten_sv = sinhvien["Ten"] if sinhvien else "Khách" 

    now = datetime.now()  # ← DI CHUYỂN LÊN ĐÂY 

    buoi = await xac_dinh_buoi(now)  # ← FIX: AWAIT VÀ THAM SỐ NOW 
    if not buoi: 
        return web.json_response({"message": "Không xác định được buổi học!"}, status=400)  # ← THÊM KIỂM TRA 

    caidat = await caidat_col.find_one({"Buoi": buoi, "Is_active": True}) 
    if not caidat: 
        return web.json_response({"message": f"Không có cài đặt cho buổi {buoi}!"}, status=404) 

    try: 
        TD_BatDau = datetime.combine(datetime.today(), datetime.strptime(caidat["TD_BatDau"], "%H:%M").time()) 
        TD_KetThuc = datetime.combine(datetime.today(), datetime.strptime(caidat["TD_KetThuc"], "%H:%M").time()) 
    except Exception: 
        return web.json_response({"message": "Dữ liệu thời gian không hợp lệ!"}, status=500) 

    TG_DiTre = timedelta(minutes=int(caidat.get("TG_DiTre", 0))) if caidat.get("TG_DiTre") else timedelta(minutes=0) 
    today = datetime.now().date() 
    start_of_today = datetime(today.year, today.month, today.day) 

    record = await diemdanh_col.find_one({ 
        "MAC": mac, 
        "Buoi": buoi, 
        "TD_Vao": {"$gte": start_of_today} 
    }) 

    # ==================== ĐIỂM DANH THỦ CÔNG ==================== 
    if not record and ly_do:   # ← Chỉ áp dụng khi có LyDo (thủ công) 
        new_record = { 
            "TD_Vao": now, 
            "TD_Ra": TD_KetThuc,           # ← Mặc định giờ ra = TD_Kết thúc buổi 
            "Buoi": buoi, 
            "MAC": mac, 
            "Ten_SinhVien": ten_sv, 
            "TrangThai": "Có mặt",         # ← Mặc định "Có mặt" 
            "LyDo": ly_do                  # ← Lưu lý do 
        } 
        await insert_one(diemdanh_col, new_record)   
        return web.json_response({ 
            "Ten_SinhVien": ten_sv, 
            "TrangThai": "Có mặt", 
            "Buoi": buoi, 
            "TD_Vao": now.strftime("%H:%M:%S"), 
            "TD_Ra": TD_KetThuc.strftime("%H:%M:%S"), 
            "LyDo": ly_do, 
            "message": "Điểm danh thủ công thành công!" 
        }, status=201) 

    # ==================== LOGIC CŨ (TỰ ĐỘNG WIFI) - KHÔNG THAY ĐỔI ==================== 
    # TRƯỜNG HỢP 1: CHƯA CÓ BẢN GHI (CHECK-IN LẦN ĐẦU) 
    if not record: 
        trangthai_checkin = "" 
        if now <= TD_BatDau: 
            trangthai_checkin = "Có mặt" 
        elif now <= (TD_BatDau + TG_DiTre): 
            trangthai_checkin = "Đi trễ" 
        else: 
            trangthai_checkin = "Vắng" 

        new_record = { 
            "TD_Vao": now, 
            "TD_Ra": None, 
            "Buoi": buoi, 
            "MAC": mac, 
            "Ten_SinhVien": ten_sv, 
            "TrangThai": trangthai_checkin, 
        } 
        await insert_one(diemdanh_col, new_record)   
        return web.json_response({ 
            "Ten_SinhVien": ten_sv, 
            "TrangThai": trangthai_checkin, 
            "Buoi": buoi, 
            "TD_Vao": now.strftime("%H:%M:%S"), 
            "TD_Ra": now.strftime("%H:%M:%S"), 
            "message": "Điểm danh lần đầu thành công!" 
        }, status=201) 

    # TRƯỜNG HỢP 2: ĐÃ CÓ BẢN GHI (CHECK-OUT) - GIỮ NGUYÊN LOGIC CŨ 
    else: 
        trangthai_hien_tai = record.get("TrangThai", "") 
        if " - " in trangthai_hien_tai: 
            trangthai_checkin_truoc = trangthai_hien_tai.split(" - ")[0] 
            trangthai_checkout_hien_tai = trangthai_hien_tai.split(" - ")[1] 
        else: 
            trangthai_checkin_truoc = trangthai_hien_tai 
            trangthai_checkout_hien_tai = trangthai_hien_tai 

        # Điều kiện để gán trạng thái "Về sớm" cho Check-out: 
        # 1. Thời gian hiện tại phải sớm hơn giờ kết thúc. 
        # 2. Trạng thái Check-out hiện tại KHÔNG PHẢI là "Về sớm" hoặc "Vắng". 
        #    (Trạng thái "Vắng" khi check-in sẽ được coi là Vắng luôn, không cập nhật về sớm) 
        is_first_time_early_leave = ( 
            now < TD_KetThuc and 
            trangthai_checkout_hien_tai not in ["Vắng", "Về sớm"]  
        ) 

        update_fields = {"TD_Ra": now} 
        message = f"Đã cập nhật giờ ra (buổi {buoi})!" 

        if is_first_time_early_leave: 
            # Lần đầu check-out sớm và chưa bị gán Vắng 
            trangthai_checkout_moi = "Về sớm" 
            message = "Sinh viên đã về sớm!" 
        elif trangthai_checkout_hien_tai == "Vắng": 
            # Nếu Check-in Vắng, Check-out cũng là Vắng (không thay đổi) 
            trangthai_checkout_moi = "Vắng" 
        elif trangthai_checkout_hien_tai == "Về sớm": 
            # Nếu đã bị gán Về sớm ở lần check-out trước, giữ nguyên Về sớm 
            trangthai_checkout_moi = "Về sớm" 
        else: 
             # Nếu Check-out sau giờ kết thúc, trạng thái Check-out là trạng thái Check-in 
             trangthai_checkout_moi = trangthai_checkin_truoc 
        
        # Cập nhật cột TrangThai thành chuỗi kết hợp 
        trangthai_ket_hop = f"{trangthai_checkin_truoc} - {trangthai_checkout_moi}" 
        update_fields["TrangThai"] = trangthai_ket_hop 
        
        await diemdanh_col.update_one( 
            {"_id": record["_id"]}, 
            {"$set": update_fields} 
        ) 
        
        
        return web.json_response({ 
            "Ten_SinhVien": ten_sv, 
            "TrangThai": trangthai_ket_hop, # Trả về trạng thái kết hợp 
            "Buoi": buoi, 
            "TD_Vao": record.get("TD_Vao").strftime("%H:%M:%S"), 
            "TD_Ra": now.strftime("%H:%M:%S"), 
            "message": message 
        }, status=200) 

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

    user = {"username": username, "password": password, "Is_active": True}
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


# Endpoint đăng nhập (xác thực)
@routes.post("/login")
async def login(request):
    data = await request.json()
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return web.json_response({"message": "Vui lòng nhập username và password!"}, status=400)

    user = await dangnhap_col.find_one({"username": username, "password": password})
    if not user:
        return web.json_response({"message": "Tên đăng nhập hoặc mật khẩu không đúng"}, status=401)

    # Trả về thông tin tối thiểu cho client (không gửi password)
    return web.json_response({"message": "Đăng nhập thành công", "username": username}, status=200)