from pymongo import MongoClient
from datetime import datetime, time

# ====== KẾT NỐI MONGODB ======
client = MongoClient("mongodb://localhost:27017/")
db = client["diemdanh_wifi"]

# ====== HÀM DÙNG CHUNG ======

# 1. Đăng nhập
def check_login(mssv, matkhau):
    user = db["dangnhap"].find_one({"mssv": mssv, "matkhau": matkhau})
    return user is not None

# 2. Thành viên
def add_thanhvien(mssv, hoten, email, mac):
    data = {
        "mssv": mssv,
        "hoten": hoten,
        "email": email,
        "mac": mac
    }
    db["danhsachthanhvien"].insert_one(data)
    return True

def get_all_thanhvien():
    return list(db["danhsachthanhvien"].find({}, {"_id": 0}))

# 3. Điểm danh
def get_trangthai_diemdanh():
    now = datetime.now().time()
    # Buổi sáng
    if time(7, 0) <= now <= time(7, 30):
        return "có mặt"
    elif time(7, 31) <= now <= time(9, 0):
        return "trễ"
    elif time(9, 1) <= now <= time(11, 30):
        return "vắng"
    # Buổi chiều
    elif time(12, 50) <= now <= time(13, 30):
        return "có mặt"
    elif time(13, 31) <= now <= time(14, 0):
        return "trễ"
    elif time(14, 1) <= now <= time(16, 30):
        return "vắng"
    # Buổi tối
    elif time(17, 0) <= now <= time(18, 30):
        return "có mặt"
    elif time(18, 31) <= now <= time(19, 0):
        return "trễ"
    elif time(19, 1) <= now <= time(20, 0):
        return "vắng"
    else:
        return "ngoài giờ"

def add_diemdanh(mac):
    trangthai = get_trangthai_diemdanh()
    data = {
        "thoigian": datetime.now().isoformat(),
        "mac": mac,
        "trangthai": trangthai
    }
    db["diemdanh"].insert_one(data)
    return trangthai


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
