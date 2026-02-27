

# import asyncio
# import ipaddress
# import platform
# import re
# from datetime import datetime, timedelta
# from bson import ObjectId
# from db_connect import sinhvien_col, thietbi_col, diemdanh_col, caidat_col

# # ----------------- CẤU HÌNH -----------------
# NETWORK_CIDR = "192.168.1.0/24"  # Thay đổi theo mạng WiFi của bạn
# PING_TIMEOUT_MS = 1000
# CONCURRENCY = 100
# SCAN_INTERVAL = 5  # giây

# # ----------------- REGEX -----------------
# RE_ARP_WIN = re.compile(r"^\s*([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)\s+([0-9A-Fa-f\-:]{17})\s+", re.M)
# RE_ARP_UNIX = re.compile(r"^\s*([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)\s+\S+\s+((?:[0-9A-Fa-f]{2}[:\-]){5}[0-9A-Fa-f]{2})", re.M)

# # ----------------- HÀM PHỤ TRỢ -----------------
# async def xac_dinh_buoi(now):
#     """Xác định buổi học dựa trên dữ liệu từ bảng caidat (Is_active: True)."""
#     now_time = now.time()
#     active_caidat = []
#     async for cd in caidat_col.find({"Is_active": True}):
#         try:
#             batdau = datetime.strptime(cd["TD_BatDau"], "%H:%M").time()
#             ketthuc = datetime.strptime(cd["TD_KetThuc"], "%H:%M").time()
#             reset_time = datetime.strptime(cd["TD_Reset"], "%H:%M").time() if cd.get("TD_Reset") else None
#             active_caidat.append({
#                 "Buoi": cd["Buoi"],
#                 "batdau_time": batdau,
#                 "ketthuc_time": ketthuc,
#                 "reset_time": reset_time,
#                 "TG_DiTre": int(cd.get("TG_DiTre", 0))
#             })
#         except (KeyError, ValueError) as e:
#             print(f"[LỖI] Bản ghi caidat không hợp lệ: {cd.get('_id')}, lỗi: {e}")

#     if not active_caidat:
#         print("[CẢNH BÁO] Không có cài đặt active nào.")
#         return None

#     for cd in active_caidat:
#         if cd["batdau_time"] <= now_time <= cd["ketthuc_time"]:
#             return cd["Buoi"]

#     active_caidat.sort(key=lambda x: x["batdau_time"])
#     next_buoi = None
#     min_diff = float('inf')
#     for cd in active_caidat:
#         if cd["batdau_time"] > now_time:
#             diff = (datetime.combine(now.date(), cd["batdau_time"]) - now).total_seconds()
#             if diff < min_diff:
#                 min_diff = diff
#                 next_buoi = cd["Buoi"]

#     if next_buoi:
#         print(f"[INFO] Giờ {now_time} không trong buổi nào, gán vào buổi gần nhất tiếp theo: {next_buoi}")
#         return next_buoi
#     else:
#         print(f"[CẢNH BÁO] Không tìm thấy buổi phù hợp hoặc gần nhất cho giờ {now_time}")
#         return None

# def parse_arp_output(text):
#     mapping = {}
#     for m in RE_ARP_WIN.finditer(text):
#         ip, mac = m.group(1), m.group(2).replace("-", ":").upper()
#         mapping[ip] = mac
#     if not mapping:
#         for m in RE_ARP_UNIX.finditer(text):
#             ip, mac = m.group(1), m.group(2).replace("-", ":").upper()
#             mapping[ip] = mac
#     return mapping

# async def get_arp_table():
#     cmd = ["arp", "-a"] if platform.system().lower() == "windows" else ["arp", "-n"]
#     proc = await asyncio.create_subprocess_exec(
#         *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
#     )
#     out, _ = await proc.communicate()
#     return parse_arp_output(out.decode(errors="ignore"))

# async def ping_ip(ip, sem):
#     async with sem:
#         system = platform.system().lower()
#         if system == "windows":
#             cmd = ["ping", "-n", "1", "-w", str(PING_TIMEOUT_MS), ip]
#         else:
#             cmd = ["ping", "-c", "1", "-W", "1", ip]
#         proc = await asyncio.create_subprocess_exec(
#             *cmd,
#             stdout=asyncio.subprocess.DEVNULL,
#             stderr=asyncio.subprocess.DEVNULL
#         )
#         await proc.communicate()
#         return proc.returncode == 0

# async def ping_subnet(network_cidr):
#     net = ipaddress.ip_network(network_cidr, strict=False)
#     hosts = [str(ip) for ip in net.hosts()]
#     sem = asyncio.Semaphore(CONCURRENCY)
#     tasks = [ping_ip(ip, sem) for ip in hosts]
#     results = await asyncio.gather(*tasks)
#     return [ip for ip, ok in zip(hosts, results) if ok]

# # ----------------- XỬ LÝ AUTO CHECK-OUT TẠI TD_RESET -----------------
# async def auto_checkout_at_reset(now, buoi):
#     caidat = await caidat_col.find_one({"Buoi": buoi, "Is_active": True})
#     if not caidat or not caidat.get("TD_Reset"):
#         return

#     reset_time = datetime.combine(now.date(), datetime.strptime(caidat["TD_Reset"], "%H:%M").time())
#     if now < reset_time:
#         return

#     today = now.strftime("%Y-%m-%d")
#     async for record in diemdanh_col.find({
#         "Buoi": buoi,
#         "Ngay": today,
#         "TD_Ra": None
#     }):
#         mac = record["MAC"]
#         await checkout(mac, reset_time, is_auto=True)
#     print(f"[AUTO CHECK-OUT] Đã force check-out tất cả tại TD_Reset cho buổi {buoi}")

# # ----------------- XỬ LÝ CHECK-IN -----------------
# async def checkin(mac, now):
#     mac = mac.upper()
#     thietbi = await thietbi_col.find_one({"MAC": mac})
#     if not thietbi or not thietbi.get("Is_active", False):
#         print(f"[DEBUG CHECK-IN] Thiết bị {mac} không tồn tại hoặc không active. Bỏ qua.")
#         return

#     sinhvien = await sinhvien_col.find_one({"_id": thietbi["SinhVien_id"]}) if thietbi.get("SinhVien_id") else None
#     ten_sv = sinhvien["Ten"] if sinhvien else "Khách"

#     buoi = await xac_dinh_buoi(now)
#     if not buoi:
#         print(f"[⚠️] Không xác định được buổi cho giờ {now}. Bỏ qua điểm danh.")
#         return

#     caidat = await caidat_col.find_one({"Buoi": buoi, "Is_active": True})
#     if not caidat:
#         print(f"[⚠️] Không có cài đặt cho buổi {buoi}. Bỏ qua điểm danh.")
#         return

#     TD_BatDau = datetime.combine(now.date(), datetime.strptime(caidat["TD_BatDau"], "%H:%M").time())
#     TG_DiTre = timedelta(minutes=int(caidat.get("TG_DiTre", 0)))
#     print(f"[DEBUG CHECK-IN] TD_BatDau: {TD_BatDau}, TG_DiTre: {TG_DiTre}, now: {now}")

#     today = now.strftime("%Y-%m-%d")
#     existing = await diemdanh_col.find_one({
#         "MAC": mac,
#         "Buoi": buoi,
#         "Ngay": today
#     })

#     if existing:
#         print(f"[DEBUG CHECK-IN] Tìm thấy record existing cho {mac}: TD_Ra = {existing.get('TD_Ra')}, TrangThai = {existing.get('TrangThai')}")
#         if existing.get("TD_Ra") is None:
#             print(f"[CHECK-IN] {ten_sv} ({mac}) đã check-in, bỏ qua (đang kết nối).")
#             return
#         else:
#             # Reconnect: Reset TD_Ra về None và TrangThai về trạng thái check-in gốc từ TrangThai_CheckIn
#             trangthai_goc = existing.get("TrangThai_CheckIn", existing.get("TrangThai", "").split(" - ")[0])
#             await diemdanh_col.update_one(
#                 {"_id": existing["_id"]},
#                 {"$set": {"TD_Ra": None, "TrangThai": trangthai_goc}}
#             )
#             print(f"[RECONNECT] {ten_sv} ({mac}) reconnect - Reset TD_Ra về None và TrangThai về '{trangthai_goc}' ({buoi})")
#             return

#     # Tạo mới nếu chưa có (giữ logic gốc: muộn > TD_BatDau + TG_DiTre = "Vắng")
#     print(f"[DEBUG CHECK-IN] Không tìm thấy record, tạo mới.")
#     if now <= TD_BatDau:
#         trangthai = "Có mặt"
#     elif now <= (TD_BatDau + TG_DiTre):
#         trangthai = "Đi trễ"
#     else:
#         trangthai = "Vắng"

#     new_record = {
#         "TD_Vao": now,
#         "TD_Ra": None,
#         "Buoi": buoi,
#         "Ngay": today,
#         "MAC": mac,
#         "Ten_SinhVien": ten_sv,
#         "TrangThai": trangthai,
#         "TrangThai_CheckIn": trangthai  # Lưu trạng thái gốc
#     }
#     await diemdanh_col.insert_one(new_record)
#     print(f"[CHECK-IN] {ten_sv} ({mac}) - {trangthai} ({buoi})")

# # ----------------- XỬ LÝ CHECK-OUT -----------------
# async def checkout(mac, now, is_auto=False):
#     mac = mac.upper()
#     buoi = await xac_dinh_buoi(now)
#     if not buoi:
#         print(f"[⚠️] Không xác định được buổi cho giờ {now}. Bỏ qua checkout.")
#         return

#     today = now.strftime("%Y-%m-%d")
#     record = await diemdanh_col.find_one({
#         "MAC": mac,
#         "Buoi": buoi,
#         "Ngay": today
#     })

#     if not record or record.get("TD_Ra") is not None:
#         print(f"[CHECK-OUT] {mac} không có record đang check-in, bỏ qua.")
#         return

#     caidat = await caidat_col.find_one({"Buoi": buoi, "Is_active": True})
#     if not caidat:
#         print(f"[⚠️] Không tìm thấy cài đặt buổi {buoi}.")
#         return

#     TD_KetThuc = datetime.combine(now.date(), datetime.strptime(caidat["TD_KetThuc"], "%H:%M").time())
#     trangthai_checkin = record.get("TrangThai_CheckIn", record.get("TrangThai", ""))  # Sử dụng TrangThai_CheckIn nếu có, fallback TrangThai
#     td_vao = record["TD_Vao"]
#     TG_DiTre = timedelta(minutes=int(caidat.get("TG_DiTre", 0)))

#     # Tính thời gian ở lớp
#     time_in_class = now - td_vao

#     # Logic mới: Nếu thời gian ở lớp < TG_DiTre → override thành "Vắng"
#     if time_in_class < TG_DiTre:
#         trangthai_ket_hop = "Vắng"
#         print(f"[CHECK-OUT] {record['Ten_SinhVien']} ({mac}) - Thời gian ở lớp {time_in_class} < TG_DiTre → override thành 'Vắng'")
#     else:
#         # Logic cũ: Chỉ thêm "Về sớm" nếu áp dụng
#         trangthai_checkout = trangthai_checkin
#         if now < TD_KetThuc and trangthai_checkin not in ["Vắng"]:
#             trangthai_checkout = "Về sớm"

#         if is_auto:
#             trangthai_checkout = "Kết thúc buổi" if trangthai_checkout != "Về sớm" else "Về sớm"

#         if trangthai_checkout != trangthai_checkin:
#             trangthai_ket_hop = f"{trangthai_checkin} - {trangthai_checkout}"
#         else:
#             trangthai_ket_hop = trangthai_checkin

#     await diemdanh_col.update_one(
#         {"_id": record["_id"]},
#         {"$set": {"TD_Ra": now, "TrangThai": trangthai_ket_hop}}
#     )

#     prefix = "[AUTO CHECK-OUT]" if is_auto else "[CHECK-OUT]"
#     print(f"{prefix} {record['Ten_SinhVien']} ({mac}) - {trangthai_ket_hop} ({buoi})")

# # ----------------- QUÉT & CẬP NHẬT -----------------
# async def update_from_scan():
#     now = datetime.now()
#     buoi = await xac_dinh_buoi(now)
#     if buoi:
#         await auto_checkout_at_reset(now, buoi)

#     online_ips = await ping_subnet(NETWORK_CIDR)
#     arp_table = await get_arp_table()
#     online_macs = {arp_table[ip].upper() for ip in online_ips if ip in arp_table}

#     async for tb in thietbi_col.find({"Is_active": True}):
#         mac = tb.get("MAC", "").upper()
#         if not mac:
#             continue

#         if mac in online_macs:
#             await checkin(mac, now)
#         else:
#             await checkout(mac, now)

#     print(f"[{now.strftime('%H:%M:%S')}] ✅ Quét xong {len(online_ips)} IP online, {len(online_macs)} MAC hợp lệ.")

# # ----------------- CHẠY QUÉT ĐỊNH KỲ -----------------
# async def periodic_scan():
#     while True:
#         try:
#             await update_from_scan()
#         except Exception as e:
#             print("❌ Lỗi khi quét:", e)
#         await asyncio.sleep(SCAN_INTERVAL)
# ------------------------------------------------------------------------------------------------------------------
#                   PHAN CACH 
# ------------------------------------------------------------------------------------------------------------------
import asyncio
import ipaddress
import platform
import re
from datetime import datetime, timedelta
from bson import ObjectId
from db_connect import sinhvien_col, thietbi_col, diemdanh_col, caidat_col

# ----------------- CẤU HÌNH -----------------
NETWORK_CIDR = "192.168.1.0/24"  # Thay đổi theo mạng WiFi của bạn
PING_TIMEOUT_MS = 1000
CONCURRENCY = 100
SCAN_INTERVAL = 5  # giây

# ----------------- REGEX -----------------
RE_ARP_WIN = re.compile(r"^\s*([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)\s+([0-9A-Fa-f\-:]{17})\s+", re.M)
RE_ARP_UNIX = re.compile(r"^\s*([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)\s+\S+\s+((?:[0-9A-Fa-f]{2}[:\-]){5}[0-9A-Fa-f]{2})", re.M)


# ----------------- HÀM PHỤ TRỢ -----------------
async def xac_dinh_buoi(now):
    now_time = now.time()
    active_caidat = []
    async for cd in caidat_col.find({"Is_active": True}):
        try:
            batdau = datetime.strptime(cd["TD_BatDau"], "%H:%M").time()
            ketthuc = datetime.strptime(cd["TD_KetThuc"], "%H:%M").time()
            reset_time = datetime.strptime(cd["TD_Reset"], "%H:%M").time() if cd.get("TD_Reset") else None
            active_caidat.append({
                "Buoi": cd["Buoi"],
                "batdau_time": batdau,
                "ketthuc_time": ketthuc,
                "reset_time": reset_time,
                "TG_DiTre": int(cd.get("TG_DiTre", 0))
            })
        except (KeyError, ValueError) as e:
            print(f"[LỖI] Bản ghi caidat không hợp lệ: {cd.get('_id')}, lỗi: {e}")

    if not active_caidat:
        print("[CẢNH BÁO] Không có cài đặt active nào.")
        return None

    # Ưu tiên: Nếu trong buổi
    for cd in active_caidat:
        if cd["batdau_time"] <= now_time <= cd["ketthuc_time"]:
            return cd["Buoi"]

    # Nếu sau tất cả, tìm buổi gần nhất TRƯỚC ĐÓ (dựa trên TD_KetThuc hoặc TD_Reset)
    active_caidat.sort(key=lambda x: x["ketthuc_time"], reverse=True)  # Sort descending để lấy buổi gần nhất trước
    prev_buoi = None
    min_diff = float('inf')
    for cd in active_caidat:
        if now_time > cd["ketthuc_time"]:
            diff = (now - datetime.combine(now.date(), cd["ketthuc_time"])).total_seconds()
            if diff < min_diff:
                min_diff = diff
                prev_buoi = cd["Buoi"]

    if prev_buoi:
        print(f"[INFO] Giờ {now_time} sau buổi, gán vào buổi gần nhất trước đó: {prev_buoi}")
        return prev_buoi

    # Fallback: Tìm buổi gần nhất tiếp theo (logic cũ)
    active_caidat.sort(key=lambda x: x["batdau_time"])
    next_buoi = None
    min_diff = float('inf')
    for cd in active_caidat:
        if cd["batdau_time"] > now_time:
            diff = (datetime.combine(now.date(), cd["batdau_time"]) - now).total_seconds()
            if diff < min_diff:
                min_diff = diff
                next_buoi = cd["Buoi"]

    if next_buoi:
        print(f"[INFO] Giờ {now_time} không trong buổi nào, gán vào buổi gần nhất tiếp theo: {next_buoi}")
        return next_buoi
    else:
        print(f"[CẢNH BÁO] Không tìm thấy buổi phù hợp hoặc gần nhất cho giờ {now_time}")
        return None

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


# --------------- XỬ LÝ AUTO CHECK-OUT TẠI TD_RESET -----------------
async def auto_checkout_at_reset(now, buoi):
    caidat = await caidat_col.find_one({"Buoi": buoi, "Is_active": True})
    if not caidat or not caidat.get("TD_Reset"):
        return

    reset_time = datetime.combine(now.date(), datetime.strptime(caidat["TD_Reset"], "%H:%M").time())
    if now < reset_time:
        return

    today = now.strftime("%Y-%m-%d")
    async for record in diemdanh_col.find({
        "Buoi": buoi,
        "Ngay": today,
        "TD_Ra": None
    }):
        mac = record["MAC"]
        await checkout(mac, reset_time, is_auto=True)  # Ghi TD_Ra = reset_time
    print(f"[AUTO CHECK-OUT] Đã force check-out tất cả tại TD_Reset cho buổi {buoi} với giờ ra: {reset_time.strftime('%H:%M')}")

# ----------------- XỬ LÝ CHECK-IN -----------------
async def checkin(mac, now):
    mac = mac.upper()
    thietbi = await thietbi_col.find_one({"MAC": mac})
    if not thietbi or not thietbi.get("Is_active", False):
        print(f"[DEBUG CHECK-IN] Thiết bị {mac} không tồn tại hoặc không active. Bỏ qua.")
        return

    sinhvien = await sinhvien_col.find_one({"_id": thietbi["SinhVien_id"]}) if thietbi.get("SinhVien_id") else None
    ten_sv = sinhvien["Ten"] if sinhvien else "Khách"

    buoi = await xac_dinh_buoi(now)
    if not buoi:
        print(f"[⚠️] Không xác định được buổi cho giờ {now}. Bỏ qua điểm danh.")
        return

    caidat = await caidat_col.find_one({"Buoi": buoi, "Is_active": True})
    if not caidat:
        print(f"[⚠️] Không có cài đặt cho buổi {buoi}. Bỏ qua điểm danh.")
        return

    TD_BatDau = datetime.combine(now.date(), datetime.strptime(caidat["TD_BatDau"], "%H:%M").time())
    TG_DiTre = timedelta(minutes=int(caidat.get("TG_DiTre", 0)))
    print(f"[DEBUG CHECK-IN] TD_BatDau: {TD_BatDau}, TG_DiTre: {TG_DiTre}, now: {now}")

    today = now.strftime("%Y-%m-%d")
    existing = await diemdanh_col.find_one({
        "MAC": mac,
        "Buoi": buoi,
        "Ngay": today
    })

    if existing:
        print(f"[DEBUG CHECK-IN] Tìm thấy record existing cho {mac}: TD_Ra = {existing.get('TD_Ra')}, TrangThai = {existing.get('TrangThai')}")
        if existing.get("TD_Ra") is None:
            print(f"[CHECK-IN] {ten_sv} ({mac}) đã check-in, bỏ qua (đang kết nối).")
            return
        else:
            # Reconnect: Reset TD_Ra về None và TrangThai về trạng thái check-in gốc từ TrangThai_CheckIn
            trangthai_goc = existing.get("TrangThai_CheckIn", existing.get("TrangThai", "").split(" - ")[0])
            await diemdanh_col.update_one(
                {"_id": existing["_id"]},
                {"$set": {"TD_Ra": None, "TrangThai": trangthai_goc}}
            )
            print(f"[RECONNECT] {ten_sv} ({mac}) reconnect - Reset TD_Ra về None và TrangThai về '{trangthai_goc}' ({buoi})")
            return

    # Tạo mới nếu chưa có (giữ logic gốc: muộn > TD_BatDau + TG_DiTre = "Vắng")
    print(f"[DEBUG CHECK-IN] Không tìm thấy record, tạo mới.")
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
        "Ngay": today,
        "MAC": mac,
        "Ten_SinhVien": ten_sv,
        "TrangThai": trangthai,
        "TrangThai_CheckIn": trangthai  # Lưu trạng thái gốc
    }
    await diemdanh_col.insert_one(new_record)
    print(f"[CHECK-IN] {ten_sv} ({mac}) - {trangthai} ({buoi})")

# ----------------- XỬ LÝ CHECK-OUT -----------------
async def checkout(mac, now, is_auto=False):
    mac = mac.upper()
    buoi = await xac_dinh_buoi(now)
    if not buoi:
        print(f"[⚠️] Không xác định được buổi cho giờ {now}. Bỏ qua checkout.")
        return

    today = now.strftime("%Y-%m-%d")
    record = await diemdanh_col.find_one({
        "MAC": mac,
        "Buoi": buoi,
        "Ngay": today
    })

    if not record or record.get("TD_Ra") is not None:
        print(f"[CHECK-OUT] {mac} không có record đang check-in, bỏ qua.")
        return

    caidat = await caidat_col.find_one({"Buoi": buoi, "Is_active": True})
    if not caidat:
        print(f"[⚠️] Không tìm thấy cài đặt buổi {buoi}.")
        return

    TD_BatDau = datetime.combine(now.date(), datetime.strptime(caidat["TD_BatDau"], "%H:%M").time())
    TD_KetThuc = datetime.combine(now.date(), datetime.strptime(caidat["TD_KetThuc"], "%H:%M").time())
    trangthai_checkin = record.get("TrangThai_CheckIn", record.get("TrangThai", ""))  # Sử dụng TrangThai_CheckIn nếu có, fallback TrangThai
    td_vao = record["TD_Vao"]
    TG_DiTre = timedelta(minutes=int(caidat.get("TG_DiTre", 0)))

    # ### SỬA MỚI: Tính time_in_class từ TD_BatDau nếu td_vao < TD_BatDau, và cap tại TD_KetThuc nếu now > TD_KetThuc
    effective_start = max(td_vao, TD_BatDau)  # Bắt đầu tính từ TD_BatDau nếu check-in sớm
    effective_end = min(now, TD_KetThuc) if is_auto else now  # Nếu auto, cap tại TD_KetThuc
    time_in_class = effective_end - effective_start

    # Logic mới: Nếu thời gian ở lớp < TG_DiTre → override thành "Vắng"
    if time_in_class < TG_DiTre:
        trangthai_ket_hop = "Vắng"
        print(f"[CHECK-OUT] {record['Ten_SinhVien']} ({mac}) - Thời gian ở lớp {time_in_class} < TG_DiTre → override thành 'Vắng'")
    else:
        # Logic cũ: Chỉ thêm "Về sớm" nếu áp dụng
        trangthai_checkout = trangthai_checkin
        if now < TD_KetThuc and trangthai_checkin not in ["Vắng"]:
            trangthai_checkout = "Về sớm"

        if is_auto:
            trangthai_checkout = "Kết thúc buổi" if trangthai_checkout != "Về sớm" else "Về sớm"

        if trangthai_checkout != trangthai_checkin:
            trangthai_ket_hop = f"{trangthai_checkin} - {trangthai_checkout}"
        else:
            trangthai_ket_hop = trangthai_checkin

    await diemdanh_col.update_one(
        {"_id": record["_id"]},
        {"$set": {"TD_Ra": now, "TrangThai": trangthai_ket_hop}}  # Đảm bảo ghi TD_Ra = now (reset_time cho auto)
    )

    prefix = "[AUTO CHECK-OUT]" if is_auto else "[CHECK-OUT]"
    print(f"{prefix} {record['Ten_SinhVien']} ({mac}) - {trangthai_ket_hop} ({buoi}) với giờ ra: {now.strftime('%H:%M')}, thời gian ở lớp: {time_in_class}")

# ----------------- QUÉT & CẬP NHẬT -----------------
async def update_from_scan():
    now = datetime.now()
    buoi = await xac_dinh_buoi(now)
    if buoi:
        await auto_checkout_at_reset(now, buoi)

    online_ips = await ping_subnet(NETWORK_CIDR)
    arp_table = await get_arp_table()
    online_macs = {arp_table[ip].upper() for ip in online_ips if ip in arp_table}

    async for tb in thietbi_col.find({"Is_active": True}):
        mac = tb.get("MAC", "").upper()
        if not mac:
            continue

        if mac in online_macs:
            await checkin(mac, now)
        else:
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