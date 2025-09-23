from pymongo import MongoClient
from datetime import datetime

# ====== KẾT NỐI MONGODB ======
client = MongoClient("mongodb://localhost:27017/")
db = client["diemdanh_wifi"]

# ====== HÀM DÙNG CHUNG ======

# 1. Đăng nhập
def check_login(mssv, matkhau):
    user = db["dangnhap"].find_one({"mssv": mssv, "matkhau": matkhau})
    return user is not None

# 2. Thành viên
def add_thanhvien(mssv, hoten, email, tenthietbi):
    data = {
        "mssv": mssv,
        "hoten": hoten,
        "email": email,
        "tenthietbi": tenthietbi
    }
    db["danhsachthanhvien"].insert_one(data)
    return True

def get_all_thanhvien():
    return list(db["danhsachthanhvien"].find({}, {"_id": 0}))

# 3. Điểm danh
def add_diemdanh(tenthietbi, trangthai):
    data = {
        "thoigian": datetime.now().isoformat(),
        "tenthietbi": tenthietbi,
        "trangthai": trangthai
    }
    db["diemdanh"].insert_one(data)
    return True

def get_all_diemdanh():
    return list(db["diemdanh"].find({}, {"_id": 0}))

# 4. Lịch trực
def add_lichtruc(ngay, buoi, hoten, trangthai):
    data = {
        "ngay": ngay,
        "buoi": buoi,
        "hoten": hoten,
        "trangthai": trangthai
    }
    db["lichtruc"].insert_one(data)
    return True

def get_all_lichtruc():
    return list(db["lichtruc"].find({}, {"_id": 0}))
