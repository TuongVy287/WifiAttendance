#from pymongo import MongoClient
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime


# ====== KẾT NỐI MONGODB ======
client = AsyncIOMotorClient("mongodb+srv://admin:Cisco%40c302@cluster0.vmxlvao.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
db = client["Wifi"]

# Collections
sinhvien_col = db["SinhVien"]
thietbi_col = db["ThietBi"]
caidat_col = db["CaiDat"]
diemdanh_col = db["DiemDanh"]
dangnhap_col = db["DangNhap"]

# ====== HÀM CHUYỂN OBJECTID SANG STRING ======
def to_json(data):
    """Chuyển ObjectId, datetime sang string để JSON không lỗi"""
    if isinstance(data, list):
        return [to_json(item) for item in data]
    if isinstance(data, dict):
        new_data = {}
        for key, value in data.items():
            if isinstance(value, ObjectId):
                new_data[key] = str(value)
            elif isinstance(value, datetime):
                new_data[key] = value.strftime("%Y-%m-%d %H:%M:%S")
            else:
                new_data[key] = to_json(value)
        return new_data
    return data

#id = sinhvien_col.find()
#for i in id:
#   print(i["_id"])

# ====== CRUD BẤT ĐỒNG BỘ ======
async def get_all(collection):
    result = []
    async for doc in collection.find():
        result.append(to_json(doc))
    return result

async def get_by_id(collection, id):
    doc = await collection.find_one({"_id": ObjectId(id)})
    if doc:
        return to_json(doc)  

async def insert_one(collection, data):
    #data["TD_Tao"] = datetime.now()
    result = await collection.insert_one(data)
    return str(result.inserted_id)

async def update_one(collection, id, data):
    #data["TD_CapNhat"] = datetime.now()
    await collection.update_one({"_id": ObjectId(id)}, {"$set": data})
    return True

async def delete_one(collection, id):
    await collection.delete_one({"_id": ObjectId(id)})
    return True

