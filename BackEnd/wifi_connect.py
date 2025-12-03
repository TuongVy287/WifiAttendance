import asyncio
import ipaddress
import platform
import re
from datetime import datetime, timedelta
from bson import ObjectId
from db_connect import sinhvien_col, thietbi_col, diemdanh_col, caidat_col

# ----------------- CẤU HÌNH -----------------
NETWORK_CIDR = "192.168.1.0/24"
PING_TIMEOUT_MS = 1000
CONCURRENCY = 100
SCAN_INTERVAL = 5  # giây

# ----------------- REGEX -----------------
RE_ARP_WIN = re.compile(r"^\s*([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)\s+([0-9A-Fa-f\-:]{17})\s+", re.M)
RE_ARP_UNIX = re.compile(r"^\s*([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)\s+\S+\s+((?:[0-9A-Fa-f]{2}[:\-]){5}[0-9A-Fa-f]{2})", re.M)


# ----------------- HÀM PHỤ TRỢ -----------------
def xac_dinh_buoi():
    """Xác định buổi học theo giờ hiện tại"""
    gio = datetime.now().hour
    if 6 <= gio < 12:
        return "Sáng"
    elif 12 <= gio < 17:
        return "Chiều"
    else:
        return "Tối"


def parse_arp_output(text):
    mapping = {}
    for m in RE_ARP_WIN.finditer(text):
        ip, mac = m.group(1), m.group(2).replace("-", ":").upper()
        mapping[ip] = mac
    if not mapping:
        for m in RE_ARP_UNIX.finditer(text):
            ip, mac = m.group(1), m.group(2).replace("-", ":").upper()
            mapping[ip] = mac
    return mapping


async def get_arp_table():
    cmd = ["arp", "-a"] if platform.system().lower() == "windows" else ["arp", "-n"]
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    out, _ = await proc.communicate()
    return parse_arp_output(out.decode(errors="ignore"))


async def ping_ip(ip, sem):
    async with sem:
        system = platform.system().lower()
        if system == "windows":
            cmd = ["ping", "-n", "1", "-w", str(PING_TIMEOUT_MS), ip]
        else:
            cmd = ["ping", "-c", "1", "-W", "1", ip]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL
        )
        await proc.communicate()
        return proc.returncode == 0


async def ping_subnet(network_cidr):
    net = ipaddress.ip_network(network_cidr, strict=False)
    hosts = [str(ip) for ip in net.hosts()]
    sem = asyncio.Semaphore(CONCURRENCY)
    tasks = [ping_ip(ip, sem) for ip in hosts]
    results = await asyncio.gather(*tasks)
    return [ip for ip, ok in zip(hosts, results) if ok]


# ----------------- XỬ LÝ CHECK-IN -----------------
async def checkin(mac, now):
    mac = mac.upper()
    thietbi = await thietbi_col.find_one({"MAC": mac})
    if not thietbi or not thietbi.get("Is_active", False):
        return

    sinhvien = await sinhvien_col.find_one({"_id": thietbi["SinhVien_id"]}) if thietbi.get("SinhVien_id") else None
    ten_sv = sinhvien["Ten"] if sinhvien else "Khách"

    buoi = xac_dinh_buoi()
    caidat = await caidat_col.find_one({"Buoi": buoi, "Is_active": True})
    if not caidat:
        print(f"[⚠️] Không có cài đặt cho buổi {buoi}. Bỏ qua điểm danh.")
        return

    TD_BatDau = datetime.combine(datetime.today(), datetime.strptime(caidat["TD_BatDau"], "%H:%M").time())
    TG_DiTre = timedelta(minutes=int(caidat.get("TG_DiTre", 0))) if caidat.get("TG_DiTre") else timedelta(minutes=0)

    # === Kiểm tra đã có điểm danh trong buổi hôm nay chưa ===
    existing = await diemdanh_col.find_one({
        "MAC": mac,
        "Buoi": buoi,
        "TD_Vao": {"$gte": datetime.combine(datetime.today(), datetime.min.time())}
    })

    if existing:
        print(f"[CHECK-IN] {ten_sv} ({mac}) đã có điểm danh buổi {buoi}, bỏ qua ghi mới.")
        return

    # === Xác định trạng thái ===
    if now <= TD_BatDau:
        trangthai = "Có mặt"
    elif now <= (TD_BatDau + TG_DiTre):
        trangthai = "Đi trễ"
    else:
        trangthai = "Vắng"

    new_record = {
        "TD_Vao": now,
        "TD_Ra": None,
        "Buoi": buoi,
        "Ngay": datetime.today().strftime("%Y-%m-%d"),
        "MAC": mac,
        "Ten_SinhVien": ten_sv,
        "TrangThai": trangthai
    }
    await diemdanh_col.insert_one(new_record)
    print(f"[CHECK-IN] {ten_sv} ({mac}) - {trangthai} ({buoi})")


# ----------------- XỬ LÝ CHECK-OUT -----------------
async def checkout(mac, now):
    mac = mac.upper()
    buoi = xac_dinh_buoi()
    today = datetime.today().strftime("%Y-%m-%d")

    # === Tìm bản ghi cùng ngày & cùng buổi ===
    record = await diemdanh_col.find_one({
        "MAC": mac,
        "Buoi": buoi,
        "Ngay": today
    })

    if not record:
        # Nếu không có bản ghi cùng buổi hoặc ngày → thêm mới
        await checkin(mac, now)
        print(f"[CHECK-OUT] {mac} chưa có bản ghi hôm nay, tạo bản ghi mới.")
        return

    # Nếu sinh viên vắng thì không cập nhật TD_Ra
    if record.get("TrangThai") == "Vắng":
        print(f"[CHECK-OUT] {record['Ten_SinhVien']} ({mac}) - 'Vắng', không ghi TD_Ra.")
        return

    caidat = await caidat_col.find_one({"Buoi": buoi, "Is_active": True})
    if not caidat:
        print(f"[⚠️] Không tìm thấy cài đặt buổi {buoi}.")
        return

    TD_KetThuc = datetime.combine(datetime.today(), datetime.strptime(caidat["TD_KetThuc"], "%H:%M").time())
    trangthai_checkin = record.get("TrangThai", "")
    trangthai_checkout = trangthai_checkin

    if now < TD_KetThuc and trangthai_checkin not in ["Vắng", "Về sớm"]:
        trangthai_checkout = "Về sớm"

    # === Ghi đè trạng thái thay vì cộng dồn ===
    if trangthai_checkout != trangthai_checkin:
        base_status = trangthai_checkin.split(" - ")[0]
        trangthai_ket_hop = f"{base_status} - {trangthai_checkout}"
    else:
        trangthai_ket_hop = trangthai_checkin

    # === Cập nhật thời gian ra ===
    await diemdanh_col.update_one(
        {"_id": record["_id"]},
        {"$set": {"TD_Ra": now, "TrangThai": trangthai_ket_hop}}
    )

    print(f"[CHECK-OUT] {record['Ten_SinhVien']} ({mac}) - {trangthai_ket_hop} ({buoi})")

# ----------------- QUÉT & CẬP NHẬT -----------------
async def update_from_scan():
    now = datetime.now()
    online_ips = await ping_subnet(NETWORK_CIDR)
    arp_table = await get_arp_table()
    online_macs = {arp_table[ip].upper() for ip in online_ips if ip in arp_table}

    # Online → checkin
    for ip in online_ips:
        mac = arp_table.get(ip)
        if mac:
            thietbi = await thietbi_col.find_one({"MAC": mac})
            if thietbi:
                # Nếu Is_active = False thì chuyển sang True và checkin
                if not thietbi.get("Is_active", False):
                    await thietbi_col.update_one({"_id": thietbi["_id"]}, {"$set": {"Is_active": True}})
                    await checkin(mac, now)

    # Offline → checkout
    async for tb in thietbi_col.find({"Is_active": True}):
        mac = tb.get("MAC", "").upper()
        if mac and mac not in online_macs:
            await thietbi_col.update_one({"_id": tb["_id"]}, {"$set": {"Is_active": False}})
            await checkout(mac, now)

    print(f"[{now.strftime('%H:%M:%S')}] ✅ Quét xong {len(online_ips)} IP online, {len(online_macs)} MAC hợp lệ.")


# ----------------- CHẠY QUÉT ĐỊNH KỲ -----------------
async def periodic_scan():
    while True:
        try:
            await update_from_scan()
        except Exception as e:
            print("❌ Lỗi khi quét:", e)
        await asyncio.sleep(SCAN_INTERVAL)
