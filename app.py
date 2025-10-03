from flask import Flask, request, jsonify
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime

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
    sinhvien = {
        "Ten": data["Ten"],
        "MSSV": data["MSSV"],
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
    thietbi = {
        "SinhVien_id": data["SinhVien_id"],
        "MAC": data["MAC"],
        "TD_Them_ThietBi": datetime.now(),
        "Ten_ThietBi": data["Ten_ThietBi"],
        "Is_active": True
    }
    thietbi_col.insert_one(thietbi)
    return jsonify({"message": "Thêm thiết bị thành công!"}), 201

@app.route("/thietbi", methods=["GET"])
def get_all_thietbi():
    result = [convert_id(tb) for tb in thietbi_col.find()]
    return jsonify(result), 200

@app.route("/thietbi/<id>", methods=["GET"])
def get_thietbi(id):
    tb = thietbi_col.find_one({"_id": ObjectId(id)})
    return jsonify(convert_id(tb)) if tb else (jsonify({"error": "Không tìm thấy"}), 404)

@app.route("/thietbi/<id>", methods=["PUT"])
def update_thietbi(id):
    data = request.json
    thietbi_col.update_one({"_id": ObjectId(id)}, {"$set": data})
    return jsonify({"message": "Cập nhật thành công!"}), 200

@app.route("/thietbi/<id>", methods=["DELETE"])
def delete_thietbi(id):
    thietbi_col.delete_one({"_id": ObjectId(id)})
    return jsonify({"message": "Xóa thành công!"}), 200


# ===============================
# 3. CÀI ĐẶT
# ===============================
@app.route("/caidat", methods=["POST"])
def add_caidat():
    data = request.json
    caidat = {
        "Buoi": data["Buoi"],
        "TD_BatDau": data["TD_BatDau"],
        "TD_KetThuc": data["TD_KetThuc"],
        "TD_Reset": data["TD_Reset"],
        "TD_Setting": datetime.now(),
        "Mail": data["Mail"],
        "Is_active": True
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
@app.route("/diemdanh", methods=["POST"])
def add_diemdanh():
    data = request.json
    diemdanh = {
        "TD_Vao": datetime.now(),
        "TD_Ra": None,
        "Buoi": data["Buoi"],
        "Ten_SinhVien": data["Ten_SinhVien"]
    }
    diemdanh_col.insert_one(diemdanh)
    return jsonify({"message": "Điểm danh thành công!"}), 201

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
    user = {
        "username": data["username"],
        "password": data["password"],
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
