from flask import Flask, request, jsonify
import db_helper as db

app = Flask(__name__)

# ========== 1. ĐĂNG NHẬP ==========
@app.route("/dangnhap", methods=["POST"])
def dangnhap():
    data = request.json
    if db.check_login(data["mssv"], data["matkhau"]):
        return jsonify({"message": "Đăng nhập thành công"}), 200
    return jsonify({"message": "Sai MSSV hoặc mật khẩu"}), 401

# ========== 2. THÀNH VIÊN ==========
@app.route("/thanhvien", methods=["POST"])
def add_thanhvien():
    data = request.json
    db.add_thanhvien(data["mssv"], data["hoten"], data["email"], data["tenthietbi"])
    return jsonify({"message": "Thêm thành viên thành công!"}), 201

@app.route("/thanhvien", methods=["GET"])
def get_thanhvien():
    return jsonify(db.get_all_thanhvien()), 200

# ========== 3. ĐIỂM DANH ==========
@app.route("/diemdanh", methods=["POST"])
def add_diemdanh():
    data = request.json
    db.add_diemdanh(data["tenthietbi"], data["trangthai"])
    return jsonify({"message": "Ghi nhận điểm danh thành công!"}), 201

@app.route("/diemdanh", methods=["GET"])
def get_diemdanh():
    return jsonify(db.get_all_diemdanh()), 200

# ========== 4. LỊCH TRỰC ==========
@app.route("/lichtruc", methods=["POST"])
def add_lichtruc():
    data = request.json
    db.add_lichtruc(data["ngay"], data["buoi"], data["hoten"], data["trangthai"])
    return jsonify({"message": "Thêm lịch trực thành công!"}), 201

@app.route("/lichtruc", methods=["GET"])
def get_lichtruc():
    return jsonify(db.get_all_lichtruc()), 200


if __name__ == "__main__":
    app.run(debug=True)
