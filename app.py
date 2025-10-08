from flask import Flask, request, jsonify
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime, timedelta

app = Flask(__name__)

# ====== KẾT NỐI MONGODB ======
client = MongoClient("mongodb+srv://admin:Cisco%40c302@cluster0.vmxlvao.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
db = client["Wifi"]

# Collections
sinhvien_col = db["SinhVien"]
thietbi_col = db["ThietBi"]
caidat_col = db["CaiDat"]
diemdanh_col = db["DiemDanh"]
dangnhap_col = db["DangNhap"]

# ===============================
# Hàm convert ObjectId -> str
# ===============================
def convert_id(doc):
    doc["_id"] = str(doc["_id"])
    return doc


# ===============================
# 1. SINH VIÊN
# ===============================

@app.route("/sinhvien", methods=["POST"])
def add_sinhvien():
    data = request.json
    ten = data.get("Ten")
    mssv = data.get("MSSV")

    # Kiểm tra dữ liệu đầu vào
    if not ten or not mssv:
        return jsonify({"message": "Vui lòng nhập đầy đủ tên và MSSV!"}), 400

    # Kiểm tra MSSV đã tồn tại hay chưa
    existing_sinhvien = sinhvien_col.find_one({"MSSV": mssv})
    if existing_sinhvien:
        return jsonify({"message": f"MSSV '{mssv}' đã tồn tại, vui lòng nhập MSSV khác!"}), 409

    # Thêm mới nếu MSSV chưa tồn tại
    sinhvien = {
        "Ten": ten,
        "MSSV": mssv,
        "Is_active": True
    }
    sinhvien_col.insert_one(sinhvien)

    return jsonify({"message": "Thêm sinh viên thành công!"}), 201

@app.route("/sinhvien", methods=["GET"])
def get_all_sinhvien():
    result = [convert_id(sv) for sv in sinhvien_col.find()]
    return jsonify(result), 200

@app.route("/sinhvien/<id>", methods=["GET"])
def get_sinhvien(id):
    sv = sinhvien_col.find_one({"_id": ObjectId(id)})
    return jsonify(convert_id(sv)) if sv else (jsonify({"error": "Không tìm thấy"}), 404)

@app.route("/sinhvien/<id>", methods=["PUT"])
def update_sinhvien(id):
    data = request.json
    sinhvien_col.update_one({"_id": ObjectId(id)}, {"$set": data})
    return jsonify({"message": "Cập nhật thành công!"}), 200

@app.route("/sinhvien/<id>", methods=["DELETE"])
def delete_sinhvien(id):
    sinhvien_col.delete_one({"_id": ObjectId(id)})
    return jsonify({"message": "Xóa thành công!"}), 200


# ===============================
# 2. THIẾT BỊ
# ===============================
@app.route("/thietbi", methods=["POST"])
def add_thietbi():
    data = request.json
    sinhvien_id = data.get("SinhVien_id")
    mac = data.get("MAC")
    ten_thietbi = data.get("Ten_ThietBi")

    if not sinhvien_id or not mac or not ten_thietbi:
        return jsonify({"message": "Vui lòng nhập đầy đủ SinhVien_id, MAC và Tên thiết bị!"}), 400
    try:
        sinhvien_obj_id = ObjectId(sinhvien_id)
    except:
        return jsonify({"message": "SinhVien_id không hợp lệ!"}), 400

    
    sinhvien = sinhvien_col.find_one({"_id": sinhvien_obj_id})
    if not sinhvien:
        return jsonify({"message": "Không tồn tại sinh viên với SinhVien_id này, vui lòng nhập lại!"}), 404

   
    existing_mac = thietbi_col.find_one({"MAC": mac})
    if existing_mac:
        return jsonify({"message": f"Địa chỉ MAC '{mac}' đã tồn tại, vui lòng nhập MAC khác!"}), 409

    
    thietbi_col.update_many(
        {"SinhVien_id": sinhvien_obj_id},
        {"$set": {"Is_active": False}}
    )

    thietbi = {
        "SinhVien_id": sinhvien_obj_id,
        "MAC": mac,
        "TD_Them_ThietBi": datetime.now(),
        "Ten_ThietBi": ten_thietbi,
        "Is_active": True
    }
    thietbi_col.insert_one(thietbi)

    return jsonify({"message": "Thêm thiết bị thành công và đã cập nhật trạng thái hoạt động!"}), 201
@app.route("/thietbi", methods=["GET"])
def get_all_thietbi():
    thietbis = list(thietbi_col.find())
    result = []
    for tb in thietbis:
        result.append({
            "_id": str(tb["_id"]),
            "SinhVien_id": str(tb["SinhVien_id"]),
            "MAC": tb["MAC"],
            "TD_Them_ThietBi": tb["TD_Them_ThietBi"].strftime("%Y-%m-%d %H:%M:%S"),
            "Ten_ThietBi": tb["Ten_ThietBi"],
            "Is_active": tb["Is_active"]
        })
    return jsonify(result), 200

@app.route("/thietbi/<id>", methods=["GET"])
def get_thietbi(id):
    try:
        obj_id = ObjectId(id)
    except:
        return jsonify({"message": "ID không hợp lệ!"}), 400

    thietbi = thietbi_col.find_one({"_id": obj_id})
    if not thietbi:
        return jsonify({"message": "Không tìm thấy thiết bị!"}), 404

    result = {
        "_id": str(thietbi["_id"]),
        "SinhVien_id": str(thietbi["SinhVien_id"]),
        "MAC": thietbi["MAC"],
        "TD_Them_ThietBi": thietbi["TD_Them_ThietBi"].strftime("%Y-%m-%d %H:%M:%S"),
        "Ten_ThietBi": thietbi["Ten_ThietBi"],
        "Is_active": thietbi["Is_active"]
    }
    return jsonify(result), 200
@app.route("/thietbi/<id>", methods=["PUT"])
def update_thietbi(id):
    data = request.json

    try:
        thietbi_id = ObjectId(id)
    except:
        return jsonify({"message": "ID thiết bị không hợp lệ!"}), 400
    thietbi = thietbi_col.find_one({"_id": thietbi_id})
    if not thietbi:
        return jsonify({"message": "Không tìm thấy thiết bị!"}), 404
    sinhvien_id = thietbi["SinhVien_id"]
    if "SinhVien_id" in data:
        return jsonify({"error": "Không được phép sửa mã sinh viên!"}), 400

    data["TD_Them_ThietBi"] = datetime.now()
    data["Is_active"] = True
    thietbi_col.update_many(
        {"SinhVien_id": sinhvien_id, "_id": {"$ne": thietbi_id}},
        {"$set": {"Is_active": False}}
    )
    thietbi_col.update_one({"_id": thietbi_id}, {"$set": data})

    return jsonify({"message": "Cập nhật thiết bị thành công và đã cập nhật trạng thái hoạt động!"}), 200

@app.route("/thietbi/<id>", methods=["DELETE"])
def delete_thietbi(id):
    thietbi = thietbi_col.find_one({"_id": ObjectId(id)})
    if not thietbi:
        return jsonify({"error": "Không tìm thấy thiết bị!"}), 404

    sinhvien_id = thietbi["SinhVien_id"]
    thietbi_col.delete_one({"_id": ObjectId(id)})

    latest_device = thietbi_col.find_one(
        {"SinhVien_id": sinhvien_id},
        sort=[("TD_Them_ThietBi", -1)]  # sắp xếp giảm dần theo thời gian
    )

    if latest_device:
        thietbi_col.update_one(
            {"_id": latest_device["_id"]},
            {"$set": {"Is_active": True}}
        )

    return jsonify({"message": "Xóa thiết bị thành công!"}), 200

# ===============================
# 3. CÀI ĐẶT
# ===============================
@app.route("/caidat", methods=["POST"])
def add_caidat():
    data = request.json
    buoi = data.get("Buoi")
    # Chỉ cập nhật Is_active=False cho các bản ghi cùng buổi
    caidat_col.update_many({"Buoi": buoi}, {"$set": {"Is_active": False}})

    caidat = {
        "Buoi": buoi,
        "TD_BatDau": data.get("TD_BatDau"),
        "TD_KetThuc": data.get("TD_KetThuc"),
        "TD_Reset": data.get("TD_Reset"),
        "TD_Setting": datetime.now(),
        "Mail": data.get("Mail"),
        "Is_active": True,
        "TG_DiTre": data.get("TG_DiTre"),
    }
    caidat_col.insert_one(caidat)
    return jsonify({"message": "Thêm cài đặt thành công!"}), 201

@app.route("/caidat", methods=["GET"])
def get_all_caidat():
    result = [convert_id(cd) for cd in caidat_col.find()]
    return jsonify(result), 200

@app.route("/caidat/<id>", methods=["GET"])
def get_caidat(id):
    cd = caidat_col.find_one({"_id": ObjectId(id)})
    return jsonify(convert_id(cd)) if cd else (jsonify({"error": "Không tìm thấy"}), 404)

@app.route("/caidat/<id>", methods=["PUT"])
def update_caidat(id):
    data = request.json
    caidat_col.update_one({"_id": ObjectId(id)}, {"$set": data})
    return jsonify({"message": "Cập nhật thành công!"}), 200

@app.route("/caidat/<id>", methods=["DELETE"])
def delete_caidat(id):
    caidat_col.delete_one({"_id": ObjectId(id)})
    return jsonify({"message": "Xóa thành công!"}), 200


# ===============================
# 4. ĐIỂM DANH
# ===============================
def xac_dinh_buoi():
    hour = datetime.now().hour
    if hour < 12:
        return "Sáng"
    elif hour < 18:
        return "Chiều"
    else:
        return "Tối"

# ====== API ĐIỂM DANH ======
@app.route("/diemdanh", methods=["POST"])
def diemdanh():
    data = request.json
    mac = data.get("MAC")
    thietbi = thietbi_col.find_one({"MAC": mac})

    if not thietbi:
        ten_sv = "Khách"
        return jsonify({"message": "Thiết bị khách - chưa đăng ký trong hệ thống!", "Ten_SinhVien": ten_sv}), 403

    # === 2. KIỂM TRA TRẠNG THÁI THIẾT BỊ ===
    if not thietbi.get("Is_active", False):
        ten_sv = "Khách"
        return jsonify({"message": "Thiết bị đã bị vô hiệu hóa!", "Ten_SinhVien": ten_sv}), 403

    # === 3. LẤY THÔNG TIN SINH VIÊN ===
    sinhvien = sinhvien_col.find_one({"_id": thietbi["SinhVien_id"]})
    ten_sv = sinhvien["Ten"] if sinhvien else "Khách"
    if not mac:
        return jsonify({"message": "Thiếu địa chỉ MAC!"}), 400

    # 1️⃣ Xác định buổi và lấy cấu hình cài đặt buổi đó
    buoi = xac_dinh_buoi()
    caidat = caidat_col.find_one({"Buoi": buoi, "Is_active": True})
    if not caidat:
        return jsonify({"message": f"Không có cài đặt cho buổi {buoi}!"}), 404

    # Lấy các mốc thời gian từ cấu hình
    TD_BatDau = datetime.combine(datetime.today(), datetime.strptime(caidat["TD_BatDau"], "%H:%M").time())
    TD_KetThuc = datetime.combine(datetime.today(), datetime.strptime(caidat["TD_KetThuc"], "%H:%M").time())
    TG_DiTre = timedelta(minutes=int(caidat["TG_DiTre"])) if caidat.get("TG_DiTre") else timedelta(minutes=0)

    now = datetime.now()

    # 2️⃣ Xác định sinh viên từ MAC
    ten_sv = "Khách"
    thietbi = thietbi_col.find_one({"MAC": mac})
    if thietbi:
        sinhvien = sinhvien_col.find_one({"_id": thietbi["SinhVien_id"]})
        if sinhvien:
            ten_sv = sinhvien["Ten"]

    # 3️⃣ Kiểm tra có bản ghi điểm danh buổi này chưa
    today = datetime.now().date()
    record = diemdanh_col.find_one({
        "MAC": mac,
        "Buoi": buoi,
        "TD_Vao": {"$gte": datetime(today.year, today.month, today.day)}
    })

    # 4️⃣ Nếu chưa có → TẠO MỚI (ghi nhận giờ vào)
    if not record:
        TD_Vao = now
        TD_Ra = now

        # --- Xác định trạng thái vào ---
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
        diemdanh_col.insert_one(new_record)

        return jsonify({
            
            "Ten_SinhVien": ten_sv,
            "TrangThai": trangthai,
            "Buoi": buoi
        }), 201

    # 5️⃣ Nếu đã có → CẬP NHẬT GIỜ RA
    else:
        TD_Ra = now
        trangthai = record["TrangThai"]

        # Nếu không vắng → kiểm tra về sớm
        if trangthai != "Vắng" and TD_Ra < TD_KetThuc:
            trangthai += " - Về sớm"

        diemdanh_col.update_one(
            {"_id": record["_id"]},
            {"$set": {"TD_Ra": TD_Ra, "TrangThai": trangthai}}
        )

        return jsonify({
            "message": f"Đã cập nhật giờ ra (buổi {buoi})!",
            "Ten_SinhVien": ten_sv,
            "TrangThai": trangthai,
            "Buoi": buoi
        }), 200
@app.route("/diemdanh", methods=["GET"])
def get_all_diemdanh():
    result = [convert_id(dd) for dd in diemdanh_col.find()]
    return jsonify(result), 200

@app.route("/diemdanh/<id>", methods=["GET"])
def get_diemdanh(id):
    dd = diemdanh_col.find_one({"_id": ObjectId(id)})
    return jsonify(convert_id(dd)) if dd else (jsonify({"error": "Không tìm thấy"}), 404)

@app.route("/diemdanh/<id>", methods=["PUT"])
def update_diemdanh(id):
    data = request.json
    diemdanh_col.update_one({"_id": ObjectId(id)}, {"$set": data})
    return jsonify({"message": "Cập nhật thành công!"}), 200

@app.route("/diemdanh/<id>", methods=["DELETE"])
def delete_diemdanh(id):
    diemdanh_col.delete_one({"_id": ObjectId(id)})
    return jsonify({"message": "Xóa thành công!"}), 200


# ===============================
# 5. ĐĂNG NHẬP
# ===============================
@app.route("/dangnhap", methods=["POST"])
def add_user():
    data = request.json
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"message": "Vui lòng nhập đầy đủ username và password!"}), 400

    existing_user = dangnhap_col.find_one({"username": username})
    if existing_user:
        return jsonify({"message": "Username đã tồn tại, vui lòng chọn username khác!"}), 409

    user = {
        "username": username,
        "password": password,
        "Is_active": True
    }
    dangnhap_col.insert_one(user)

    return jsonify({"message": "Tạo tài khoản thành công!"}), 201

@app.route("/dangnhap", methods=["GET"])
def get_all_user():
    result = [convert_id(u) for u in dangnhap_col.find()]
    return jsonify(result), 200

@app.route("/dangnhap/<id>", methods=["GET"])
def get_user(id):
    user = dangnhap_col.find_one({"_id": ObjectId(id)})
    return jsonify(convert_id(user)) if user else (jsonify({"error": "Không tìm thấy"}), 404)

@app.route("/dangnhap/<id>", methods=["PUT"])
def update_user(id):
    data = request.json
    dangnhap_col.update_one({"_id": ObjectId(id)}, {"$set": data})
    return jsonify({"message": "Cập nhật thành công!"}), 200

@app.route("/dangnhap/<id>", methods=["DELETE"])
def delete_user(id):
    dangnhap_col.delete_one({"_id": ObjectId(id)})
    return jsonify({"message": "Xóa thành công!"}), 200


if __name__ == "__main__":
    app.run(debug=True)
