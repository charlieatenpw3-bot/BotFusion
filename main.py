import asyncio
import os
import random
import time
from threading import Thread

import discord
from discord.ext import commands, tasks
from discord.ui import Button, View
from flask import Flask
import pymongo

# ==========================================
# CẤU HÌNH ADMIN & ĐẾM THỜI GIAN
# ==========================================
ADMIN_IDS = [1184835548897103952]

# ==========================================
# 0. KHỞI TẠO WEB SERVER (KEEP ALIVE)
# ==========================================
app = Flask("")

@app.route("/")
def home():
    return "Bot Discord Fusion đang hoạt động 24/7!"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

def keep_alive():
    t = Thread(target=run_web_server)
    t.daemon = True
    t.start()

# ==========================================
# 1. KẾT NỐI MONGODB
# ==========================================
MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    print("❌ CẢNH BÁO: Chưa cấu hình MONGO_URI!")

cluster = pymongo.MongoClient(MONGO_URI)
db = cluster["fusion_bot"]
users_col = db["users"]
marriages_col = db["marriages"]
guild_settings_col = db["guild_settings"]

def lay_user_data(user_id: int):
    user_data = users_col.find_one({"_id": user_id})
    if not user_data:
        user_data = {
            "_id": user_id,
            "vi_tien": 1000,
            "tien_no": 0,
            "lan_tinh_lai": time.time(),
            "tien_no_xau": 0,
            "lan_tinh_lai_xau": time.time(),
            "lan_diem_danh": 0,
            "da_dung_code": False,
            "lan_cuoi_lam": 0,
            "thoi_gian_bi_bat": 0,
            "thuy_chung": 0,
            "diem_danh_chuoi": 0,
            "ngay_diem_danh_gan_nhat": 0,
            "fish_inventory": [],
            "pet": None,
        }
        users_col.insert_one(user_data)

    now = time.time()
    
    # 1. Tính lãi Ngân Hàng (5%/ngày)
    lan_tinh_lai = user_data.get("lan_tinh_lai", now)
    tien_no = user_data.get("tien_no", 0)
    if tien_no > 0 and (now - lan_tinh_lai) >= 86400:
        so_ngay = int((now - lan_tinh_lai) // 86400)
        tien_no = int(tien_no * (1.05 ** so_ngay))
        lan_tinh_lai_moi = lan_tinh_lai + (so_ngay * 86400)
        user_data["tien_no"] = tien_no
        user_data["lan_tinh_lai"] = lan_tinh_lai_moi
        cap_nhat_user_data(
            user_id,
            {"tien_no": tien_no, "lan_tinh_lai": lan_tinh_lai_moi},
        )

    # 2. Tính lãi Nợ Xấu (30%/giờ)
    lan_tinh_lai_xau = user_data.get("lan_tinh_lai_xau", now)
    tien_no_xau = user_data.get("tien_no_xau", 0)
    if tien_no_xau > 0 and (now - lan_tinh_lai_xau) >= 3600:
        so_gio = int((now - lan_tinh_lai_xau) // 3600)
        tien_no_xau = int(tien_no_xau * (1.30 ** so_gio))
        lan_tinh_lai_xau_moi = lan_tinh_lai_xau + (so_gio * 3600)
        user_data["tien_no_xau"] = tien_no_xau
        user_data["lan_tinh_lai_xau"] = lan_tinh_lai_xau_moi
        cap_nhat_user_data(
            user_id,
            {"tien_no_xau": tien_no_xau, "lan_tinh_lai_xau": lan_tinh_lai_xau_moi},
        )

    return user_data

def cap_nhat_user_data(user_id: int, updates: dict):
    users_col.update_one({"_id": user_id}, {"$set": updates}, upsert=True)

def lay_ban_doi(user_id: int):
    doc = marriages_col.find_one(
        {"$or": [{"user1": user_id}, {"user2": user_id}]}
    )
    if doc:
        return doc["user2"] if doc["user1"] == user_id else doc["user1"]
    return None

def lay_guild_config(guild_id: int):
    config = guild_settings_col.find_one({"_id": guild_id})
    if not config:
        config = {
            "_id": guild_id,
            "allowed_channels": [],
            "command_channels": {},
            "tb_vay_channel": None,
            "tb_trano_channel": None,
            "tb_noxau_channel": None,
        }
        guild_settings_col.insert_one(config)
    return config

# ==========================================
# 2. DỮ LIỆU CÂU HỎI QUIZ & BÓI TOÁN & TÍNH NĂNG VUI
# ==========================================
QUIZ_DATA = [
    {"q": "Thủ đô của Việt Nam là gì?", "a": "hà nội"},
    {"q": "Thủ đô của Pháp là gì?", "a": "paris"},
    {"q": "Châu lục nào lớn nhất thế giới?", "a": "châu á"},
    {"q": "Đại dương nào lớn nhất thế giới?", "a": "thái bình dương"},
    {"q": "Đỉnh núi nào cao nhất thế giới?", "a": "everest"},
    {"q": "Công thức hóa học của nước là gì?", "a": "h2o"},
    {"q": "Kim loại nào dẫn điện tốt nhất?", "a": "bạc"},
    {"q": "Hành tinh nào được gọi là 'Hành tinh Đỏ'?", "a": "sao hỏa"},
    {"q": "Ngày Quốc khánh Việt Nam là ngày nào?", "a": "2/9"},
    {"q": "Bức tranh nàng Mona Lisa do ai vẽ?", "a": "leonardo da vinci"},
]
CURRENT_QUIZ = {}

EIGHTBALL_RESPONSES = [
    "Chắc chắn rồi! ✨", "Không thể nào đâu. ❌", "Hỏi lại sau nhé! 😴",
    "Có vẻ như là có. 👍", "Vũ trụ bảo: Hãy tin vào bản thân! 🌟",
    "Cứ làm đi, đừng ngần ngại! 🚀", "Tỷ lệ thành công là 99.9%! 🎯",
    "Nên cẩn trọng thì hơn! ⚠️", "Mọi chuyện rồi sẽ tốt đẹp thôi. 🌈"
]

GIANG_HO_CHUI = [
    "Thích bùng nợ giang hồ à cháu? Trả ngay không mày xác định với tụi tao! 🤜🔥",
    "Trốn đi đâu? Đã 2 tiếng trôi qua rồi mà không thấy 1 xu nợ xấu nào! Trả tiền mau! 🩸🔪",
    "Có gan vay nợ xấu 30%/h mà không có gan trả à? Giang hồ tới tận nhà tìm mày giờ đó! 😡💀",
    "Alo alo <@{id}>, định bùng nợ đúng không? Đừng để bọn này ra tay nhé! 🚗💥"
]

FISH_LIST = [
    {"name": "🐟 Cá rô phi", "value": 50, "rate": 0.4},
    {"name": "🐠 Cá hề", "value": 100, "rate": 0.3},
    {"name": "🦈 Cá mập con", "value": 500, "rate": 0.15},
    {"name": "🐋 Cá voi khổng lồ", "value": 2000, "rate": 0.04},
    {"name": "🥿 Chiếc dép rách", "value": 5, "rate": 0.1},
    {"name": "💎 Hòm kho báu dưới đáy biển", "value": 5000, "rate": 0.01}
]

# ==========================================
# CẤU HÌNH BOT DISCORD & MIDDLEWARE
# ==========================================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix=".", intents=intents)

@bot.before_invoke
async def check_channel_permissions(ctx):
    if not ctx.guild:
        return

    if ctx.command.name in [
        "setupbot",
        "botchucnangkenh",
        "settb",
        "settbnoxau",
        "taodanhmuc",
        "taokenh",
        "taonhanh",
        "fusion",
        "atendepzai",
    ]:
        return

    config = lay_guild_config(ctx.guild.id)
    allowed_channels = config.get("allowed_channels", [])
    command_channels = config.get("command_channels", {})

    cmd_name = ctx.command.name

    if cmd_name in command_channels:
        target_channel_id = command_channels[cmd_name]
        if ctx.channel.id != target_channel_id:
            msg = await ctx.send(
                f"❌ Lệnh `.{cmd_name}` chỉ được phép dùng tại kênh <#{target_channel_id}>!"
            )
            await asyncio.sleep(3)
            try:
                await ctx.message.delete()
                await msg.delete()
            except Exception:
                pass
            raise commands.CommandError("Sai kênh cho phép chức năng.")

    elif allowed_channels and ctx.channel.id not in allowed_channels:
        str_channels = ", ".join([f"<#{cid}>" for cid in allowed_channels])
        msg = await ctx.send(
            f"❌ Bot chỉ hoạt động trong các kênh: {str_channels}"
        )
        await asyncio.sleep(3)
        try:
            await ctx.message.delete()
            await msg.delete()
        except Exception:
            pass
        raise commands.CommandError("Kênh không nằm trong danh sách cho phép.")

@bot.event
async def on_ready():
    print(f"Bot {bot.user} đã sẵn sàng hoạt động!")
    if not quat_giang_ho_doi_no.is_running():
        quat_giang_ho_doi_no.start()

# --- TASK TỰ ĐỘNG LỌC VÀ CHỬI KHI NỢ XẤU QUÁ 2 TIẾNG ---
@tasks.loop(minutes=30)
async def quat_giang_ho_doi_no():
    now = time.time()
    for user in users_col.find({"tien_no_xau": {"$gt": 0}}):
        user_id = user["_id"]
        lan_tinh_lai = user.get("lan_tinh_lai_xau", now)
        
        # Nếu nợ xấu quá 2 tiếng (7200 giây)
        if (now - lan_tinh_lai) >= 7200:
            for guild in bot.guilds:
                config = lay_guild_config(guild.id)
                tb_noxau_id = config.get("tb_noxau_channel")
                if tb_noxau_id:
                    channel = guild.get_channel(tb_noxau_id)
                    member = guild.get_member(user_id)
                    if channel and member:
                        chui_msg = random.choice(GIANG_HO_CHUI).format(id=user_id)
                        await channel.send(
                            f"🚨 **GIANG HỒ ĐÒI NỢ SỐ LÔ/NỢ XẤU:**\n"
                            f"👉 <@{user_id}> đang nợ **{user['tien_no_xau']} xu** quá 2 tiếng chưa trả!\n"
                            f"💬 *{chui_msg}*"
                        )

# ==========================================
# 🛠️ CÀI ĐẶT & QUẢN LÝ KÊNH (ADMIN)
# ==========================================
@bot.command(name="setupbot")
@commands.has_permissions(manage_guild=True)
async def setupbot(ctx, *channels: discord.TextChannel):
    if not channels:
        guild_settings_col.update_one(
            {"_id": ctx.guild.id}, {"$set": {"allowed_channels": []}}
        )
        return await ctx.send(
            "✅ Đã xóa giới hạn kênh! Bot hiện có thể hoạt động ở **TẤT CẢ** các kênh."
        )

    channel_ids = [c.id for c in channels]
    guild_settings_col.update_one(
        {"_id": ctx.guild.id}, {"$set": {"allowed_channels": channel_ids}}
    )

    str_list = ", ".join([c.mention for c in channels])
    await ctx.send(f"✅ **CÀI ĐẶT THÀNH CÔNG!**\nBot chỉ hoạt động tại các kênh: {str_list}")

@setupbot.error
async def setupbot_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Bạn cần có quyền **Quản lý máy chủ** để dùng lệnh này!")

@bot.command(name="botchucnangkenh")
@commands.has_permissions(manage_guild=True)
async def botchucnangkenh(ctx, cmd_name: str, channel: discord.TextChannel = None):
    cmd_clean = cmd_name.lower().replace(".", "")
    config = lay_guild_config(ctx.guild.id)
    cmd_channels = config.get("command_channels", {})

    if cmd_clean in ["xoa", "off", "clear"]:
        if channel:
            target_cmd = channel.name.lower().replace(".", "")
            if target_cmd in cmd_channels:
                del cmd_channels[target_cmd]
                guild_settings_col.update_one(
                    {"_id": ctx.guild.id},
                    {"$set": {"command_channels": cmd_channels}},
                )
                return await ctx.send(f"✅ Đã hủy bỏ giới hạn kênh cho lệnh `.{target_cmd}`!")
        else:
            guild_settings_col.update_one(
                {"_id": ctx.guild.id}, {"$set": {"command_channels": {}}}
            )
            return await ctx.send("✅ Đã xóa toàn bộ giới hạn kênh chức năng!")

    if not channel:
        return await ctx.send(
            "❌ Cú pháp: `.botchucnangkenh <tên_lệnh> <#kênh>`\n"
            "Ví dụ: `.botchucnangkenh taixiu #kênh-tài-xỉu`"
        )

    cmd_channels[cmd_clean] = channel.id
    guild_settings_col.update_one(
        {"_id": ctx.guild.id}, {"$set": {"command_channels": cmd_channels}}
    )

    await ctx.send(f"🎯 Lệnh `.{cmd_clean}` từ bây giờ chỉ có thể dùng tại kênh {channel.mention}!")

# --- 📢 LỆNH SET KÊNH THÔNG BÁO VAY / TRẢ NỢ THƯỜNG ---
@bot.command(name="settb")
@commands.has_permissions(manage_guild=True)
async def settb(ctx, *, noi_dung: str = None):
    if not noi_dung or "|" not in noi_dung:
        return await ctx.send(
            "❌ Cú pháp chưa đúng!\n"
            "👉 Vay: `.settb vay | #kênh`\n"
            "👉 Trả nợ: `.settb trano | #kênh`"
        )

    parts = noi_dung.split("|", 1)
    loai_tb = parts[0].strip().lower()

    if not ctx.message.channel_mentions:
        return await ctx.send("❌ Vui lòng gắn thẻ kênh! Ví dụ: `.settb vay | #thong-bao-vay`")

    channel = ctx.message.channel_mentions[0]

    if loai_tb == "vay":
        guild_settings_col.update_one(
            {"_id": ctx.guild.id},
            {"$set": {"tb_vay_channel": channel.id}},
            upsert=True
        )
        await ctx.send(f"🏦 Đã cài đặt kênh {channel.mention} làm kênh thông báo **VAY TIỀN**!")
    elif loai_tb in ["trano", "tra"]:
        guild_settings_col.update_one(
            {"_id": ctx.guild.id},
            {"$set": {"tb_trano_channel": channel.id}},
            upsert=True
        )
        await ctx.send(f"💳 Đã cài đặt kênh {channel.mention} làm kênh thông báo **TRẢ NỢ**!")
    else:
        await ctx.send("❌ Loại thông báo không hợp lệ! Dùng `vay` hoặc `trano`.")

@settb.error
async def settb_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Bạn cần có quyền **Quản lý máy chủ** để dùng lệnh này!")

# --- 📢 LỆNH SET KÊNH THÔNG BÁO NỢ XẤU ---
@bot.command(name="settbnoxau")
@commands.has_permissions(manage_guild=True)
async def settbnoxau(ctx, channel: discord.TextChannel = None):
    if not channel:
        return await ctx.send("❌ Cú pháp: `.settbnoxau #kênh`!")

    guild_settings_col.update_one(
        {"_id": ctx.guild.id},
        {"$set": {"tb_noxau_channel": channel.id}},
        upsert=True
    )
    await ctx.send(f"⚠️ Đã cài đặt kênh {channel.mention} làm kênh thông báo **NỢ XẤU (GIANG HỒ)**!")

@settbnoxau.error
async def settbnoxau_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Bạn cần có quyền **Quản lý máy chủ** để dùng lệnh này!")

# --- LỆNH TẠO DANH MỤC & KÊNH ---
@bot.command(name="taodanhmuc")
@commands.has_permissions(manage_channels=True)
async def taodanhmuc(ctx, *, ten_danhmuc: str):
    try:
        category = await ctx.guild.create_category(ten_danhmuc)
        await ctx.send(f"📁 Đã tạo thành công danh mục **{category.name}**!")
    except Exception as e:
        await ctx.send(f"❌ Không thể tạo danh mục: `{e}`")

@bot.command(name="taokenh")
@commands.has_permissions(manage_channels=True)
async def taokenh(ctx, ten_kenh: str, *, ten_danhmuc: str = None):
    target_category = None
    if ten_danhmuc:
        target_category = discord.utils.get(ctx.guild.categories, name=ten_danhmuc)
        if not target_category:
            target_category = await ctx.guild.create_category(ten_danhmuc)

    try:
        new_channel = await ctx.guild.create_text_channel(
            name=ten_kenh, category=target_category
        )
        cat_info = f" trong danh mục **{target_category.name}**" if target_category else ""
        await ctx.send(f"💬 Đã tạo kênh chat {new_channel.mention}{cat_info}!")
    except Exception as e:
        await ctx.send(f"❌ Không thể tạo kênh: `{e}`")

@bot.command(name="taonhanh")
@commands.has_permissions(manage_channels=True)
async def taonhanh(ctx, *, noi_dung: str):
    if "|" not in noi_dung:
        return await ctx.send(
            "❌ Cú pháp chưa đúng! Ví dụ: `.taonhanh Khu Giải Trí | chat-chung, taixiu, xidach`"
        )

    parts = noi_dung.split("|", 1)
    ten_danhmuc = parts[0].strip()
    danh_sach_kenh_str = parts[1].strip()

    if not ten_danhmuc or not danh_sach_kenh_str:
        return await ctx.send("❌ Vui lòng nhập đầy đủ tên danh mục và ít nhất 1 tên kênh!")

    danh_sach_kenh = [k.strip() for k in danh_sach_kenh_str.split(",") if k.strip()]
    target_category = discord.utils.get(ctx.guild.categories, name=ten_danhmuc)
    if not target_category:
        try:
            target_category = await ctx.guild.create_category(ten_danhmuc)
        except Exception as e:
            return await ctx.send(f"❌ Lỗi khi tạo danh mục: `{e}`")

    created_channels = []
    msg_status = await ctx.send(f"⏳ Đang tiến hành tạo {len(danh_sach_kenh)} kênh...")

    for kenh_name in danh_sach_kenh:
        try:
            ch = await ctx.guild.create_text_channel(name=kenh_name, category=target_category)
            created_channels.append(ch.mention)
            await asyncio.sleep(0.5)
        except Exception as e:
            print(f"Lỗi tạo kênh {kenh_name}: {e}")

    str_kenh_da_tao = ", ".join(created_channels)
    await msg_status.edit(
        content=(
            f"✅ **TẠO HÀNG LOẠT THÀNH CÔNG!**\n"
            f"📁 **Danh mục:** {target_category.name}\n"
            f"💬 **Kênh đã tạo ({len(created_channels)}):** {str_kenh_da_tao}"
        )
    )

# ==========================================
# LỆNH ADMIN & MENU FUSION
# ==========================================
@bot.command(name="atendepzai")
async def aten_dep_zai(ctx):
    try:
        await ctx.message.delete()
    except Exception:
        pass

    if ctx.author.id not in ADMIN_IDS:
        return

    user_data = lay_user_data(ctx.author.id)
    tong_tien = user_data.get("vi_tien", 0) + 1000
    cap_nhat_user_data(ctx.author.id, {"vi_tien": tong_tien})

    bot_msg = await ctx.send(f"✨ **{ctx.author.display_name}** đã cộng thành công **+1,000 xu**!")
    await asyncio.sleep(3)
    try:
        await bot_msg.delete()
    except Exception:
        pass

@bot.command(name="fusion")
async def fusion(ctx):
    embed = discord.Embed(
        title="🤖 DANH SÁCH CHỨC NĂNG BOT FUSION (FULL 100+ TÍNH NĂNG VUI)",
        description="Dưới đây là toàn bộ các lệnh cập nhật mở rộng:",
        color=discord.Color.blue(),
    )

    embed.add_field(
        name="💰 Quản Lý & Ngân Hàng",
        value=(
            "• `.vi` : Xem số xu trong ví.\n"
            "• `.thongtin` : Xem hồ sơ cá nhân & các khoản nợ.\n"
            "• `.vay <xu>` : Vay tiền ngân hàng (Lãi 5%/ngày).\n"
            "• `.trano <xu/all>` : Trả nợ ngân hàng.\n"
            "• `.vaynoxau <xu>` : Vay nợ xấu giang hồ (Lãi 30%/h).\n"
            "• `.tranoxau <xu/all>` : Trả nợ xấu giang hồ.\n"
            "• `.diemdanh` : Điểm danh nhận xu hằng ngày.\n"
            "• `.lamviec` : Đi làm thuê kiếm xu.\n"
            "• `.chuyentien @user <xu>` : Chuyển xu cho người khác.\n"
            "• `.top` : Bảng xếp hạng đại gia."
        ),
        inline=False,
    )

    embed.add_field(
        name="🎲 Minigame Casino & Giải Trí Cơ Bản",
        value=(
            "• `.taixiu <xu>` | `.xidach <cược>` | `.baucua <cược>`\n"
            "• `.nohu <cược>` | `.doanso <cược>` | `.dovui`\n"
            "• `.tromtien @user` | `.vqmm` | `.tungxu`"
        ),
        inline=False,
    )

    embed.add_field(
        name="🎉 Kho 100+ Tính Năng Vui Mới Cập Nhật",
        value=(
            "• **Minigame & May rủi:** `.latbai`, `.oanditu`, `.dua`, `.xoasobon`\n"
            "• **Nghề nghiệp & Sinh tồn:** `.cauca`, `.daoham`, `.sanban`, `.nuoithu`\n"
            "• **Tương tác cảm xúc:** `.hon`, `.tat`, `.om`, `.honnhan`, `.lyhon`, `.vuotve`, `.dam`, `.ghen`\n"
            "• **Giải trí & Vui vẻ:** `.tuvingay`, `.8ball`, `.tile`, `.IQ`, `.ship`, `.nhaclofi`, `.thodex`"
        ),
        inline=False,
    )

    embed.set_footer(text=f"Yêu cầu bởi {ctx.author.display_name}")
    await ctx.send(embed=embed)

# ==========================================
# CÁC LỆNH TÀI CHÍNH & NGÂN HÀNG
# ==========================================
@bot.command(name="vi")
async def vi(ctx):
    user_data = lay_user_data(ctx.author.id)
    await ctx.send(f"💰 {ctx.author.mention}, bạn đang có **{user_data['vi_tien']}** xu.")

# --- VAY NGÂN HÀNG THƯỜNG ---
@bot.command(name="vay")
async def vay(ctx, so_tien: int):
    if so_tien <= 0:
        return await ctx.send("❌ Số tiền vay phải lớn hơn 0!")

    user_data = lay_user_data(ctx.author.id)
    tien_no_hien_tai = user_data.get("tien_no", 0)

    if tien_no_hien_tai + so_tien > 50000:
        return await ctx.send(
            f"❌ Hạn mức vay ngân hàng tối đa là **50,000 xu**! Hiện bạn đã nợ **{tien_no_hien_tai} xu**."
        )

    cap_nhat_user_data(
        ctx.author.id,
        {
            "vi_tien": user_data["vi_tien"] + so_tien,
            "tien_no": tien_no_hien_tai + so_tien,
            "lan_tinh_lai": time.time(),
        },
    )

    await ctx.send(
        f"🏦 **NGÂN HÀNG FUSION:** {ctx.author.mention} đã vay thành công **{so_tien} xu**!\n"
        f"⚠️ *Lưu ý: Tiền nợ sẽ chịu lãi suất **5%/ngày**.*"
    )

    config = lay_guild_config(ctx.guild.id)
    tb_channel_id = config.get("tb_vay_channel")
    if tb_channel_id:
        tb_channel = ctx.guild.get_channel(tb_channel_id)
        if tb_channel:
            embed_tb = discord.Embed(
                title="🏦 THÔNG BÁO VAY TIỀN NGÂN HÀNG",
                color=discord.Color.red(),
                timestamp=discord.utils.utcnow()
            )
            embed_tb.add_field(name="Khách hàng", value=ctx.author.mention, inline=True)
            embed_tb.add_field(name="Số tiền vay", value=f"**+{so_tien} xu**", inline=True)
            embed_tb.add_field(name="Tổng dư nợ", value=f"**{tien_no_hien_tai + so_tien} xu**", inline=False)
            embed_tb.set_footer(text=f"ID: {ctx.author.id}")
            await tb_channel.send(embed=embed_tb)

# --- TRẢ NỢ NGÂN HÀNG THƯỜNG ---
@bot.command(name="trano")
async def trano(ctx, so_tien: str):
    user_data = lay_user_data(ctx.author.id)
    tien_no = user_data.get("tien_no", 0)

    if tien_no <= 0:
        return await ctx.send("🎉 Bạn không có khoản nợ ngân hàng nào cần trả!")

    if so_tien.lower() == "all":
        tra = min(user_data["vi_tien"], tien_no)
    elif so_tien.isdigit():
        tra = int(so_tien)
    else:
        return await ctx.send("❌ Cú pháp không hợp lệ! Dùng `.trano <số_xu>` hoặc `.trano all`.")

    if tra <= 0:
        return await ctx.send("❌ Số tiền trả phải lớn hơn 0!")
    if user_data["vi_tien"] < tra:
        return await ctx.send("❌ Bạn không có đủ tiền trong ví để trả!")

    con_no = tien_no - tra
    if con_no < 0:
        tra = tien_no
        con_no = 0

    cap_nhat_user_data(
        ctx.author.id,
        {
            "vi_tien": user_data["vi_tien"] - tra,
            "tien_no": con_no,
        },
    )

    await ctx.send(
        f"🏦 **NGÂN HÀNG FUSION:** {ctx.author.mention} đã trả **{tra} xu**!\n"
        f"📌 Dư nợ ngân hàng còn lại: **{con_no} xu**."
    )

    config = lay_guild_config(ctx.guild.id)
    tb_channel_id = config.get("tb_trano_channel")
    if tb_channel_id:
        tb_channel = ctx.guild.get_channel(tb_channel_id)
        if tb_channel:
            embed_tb = discord.Embed(
                title="💳 THÔNG BÁO TRẢ NỢ NGÂN HÀNG",
                color=discord.Color.green(),
                timestamp=discord.utils.utcnow()
            )
            embed_tb.add_field(name="Khách hàng", value=ctx.author.mention, inline=True)
            embed_tb.add_field(name="Số tiền trả", value=f"**-{tra} xu**", inline=True)
            embed_tb.add_field(name="Dư nợ còn lại", value=f"**{con_no} xu**", inline=False)
            embed_tb.set_footer(text=f"ID: {ctx.author.id}")
            await tb_channel.send(embed=embed_tb)

# --- 🚨 VAY NỢ XẤU ---
@bot.command(name="vaynoxau")
async def vaynoxau(ctx, so_tien: int):
    if so_tien <= 0:
        return await ctx.send("❌ Số tiền vay phải lớn hơn 0!")

    user_data = lay_user_data(ctx.author.id)
    tien_no_xau = user_data.get("tien_no_xau", 0)

    if tien_no_xau + so_tien > 200000:
        return await ctx.send(
            f"❌ Hạn mức vay NỢ XẤU tối đa là **200,000 xu**! Hiện bạn đã nợ **{tien_no_xau} xu**."
        )

    cap_nhat_user_data(
        ctx.author.id,
        {
            "vi_tien": user_data["vi_tien"] + so_tien,
            "tien_no_xau": tien_no_xau + so_tien,
            "lan_tinh_lai_xau": time.time(),
        },
    )

    await ctx.send(
        f"⚠️ **GIANG HỒ CHO VAY NỢ XẤU:** {ctx.author.mention} đã nhận **{so_tien} xu**!\n"
        f"🔥 *CẢNH BÁO: Lãi suất cực đắt **30%/1 tiếng**. Sau 2 tiếng chưa trả sẽ bị giang hồ chửi và truy tìm!*"
    )

    config = lay_guild_config(ctx.guild.id)
    tb_noxau_id = config.get("tb_noxau_channel")
    if tb_noxau_id:
        tb_channel = ctx.guild.get_channel(tb_noxau_id)
        if tb_channel:
            embed_tb = discord.Embed(
                title="🩸 THÔNG BÁO VAY NỢ XẤU (TÍN DỤNG ĐEN)",
                color=discord.Color.dark_red(),
                timestamp=discord.utils.utcnow()
            )
            embed_tb.add_field(name="Con nợ", value=ctx.author.mention, inline=True)
            embed_tb.add_field(name="Số tiền vay", value=f"**+{so_tien} xu**", inline=True)
            embed_tb.add_field(name="Tổng nợ xấu hiện tại", value=f"**{tien_no_xau + so_tien} xu**", inline=False)
            embed_tb.set_footer(text="Hạn trả: 2 tiếng trước khi giang hồ tìm!")
            await tb_channel.send(embed=embed_tb)

# --- 🚨 TRẢ NỢ XẤU ---
@bot.command(name="tranoxau")
async def tranoxau(ctx, so_tien: str):
    user_data = lay_user_data(ctx.author.id)
    tien_no_xau = user_data.get("tien_no_xau", 0)

    if tien_no_xau <= 0:
        return await ctx.send("🎉 Bạn không có khoản nợ xấu giang hồ nào!")

    if so_tien.lower() == "all":
        tra = min(user_data["vi_tien"], tien_no_xau)
    elif so_tien.isdigit():
        tra = int(so_tien)
    else:
        return await ctx.send("❌ Cú pháp không hợp lệ! Dùng `.tranoxau <số_xu>` hoặc `.tranoxau all`.")

    if tra <= 0:
        return await ctx.send("❌ Số tiền trả phải lớn hơn 0!")
    if user_data["vi_tien"] < tra:
        return await ctx.send("❌ Bạn không đủ tiền trong ví để trả nợ xấu!")

    con_no = tien_no_xau - tra
    if con_no < 0:
        tra = tien_no_xau
        con_no = 0

    cap_nhat_user_data(
        ctx.author.id,
        {
            "vi_tien": user_data["vi_tien"] - tra,
            "tien_no_xau": con_no,
        },
    )

    await ctx.send(
        f"🤝 **GIANG HỒ BÁO XÁC NHẬN:** {ctx.author.mention} đã trả **{tra} xu**!\n"
        f"📌 Dư nợ xấu còn lại: **{con_no} xu**."
    )

    config = lay_guild_config(ctx.guild.id)
    tb_noxau_id = config.get("tb_noxau_channel")
    if tb_noxau_id:
        tb_channel = ctx.guild.get_channel(tb_noxau_id)
        if tb_channel:
            embed_tb = discord.Embed(
                title="🕊️ THÔNG BÁO TRẢ NỢ XẤU (GIANG HỒ)",
                color=discord.Color.blue(),
                timestamp=discord.utils.utcnow()
            )
            embed_tb.add_field(name="Người trả", value=ctx.author.mention, inline=True)
            embed_tb.add_field(name="Số tiền trả", value=f"**-{tra} xu**", inline=True)
            embed_tb.add_field(name="Nợ xấu còn lại", value=f"**{con_no} xu**", inline=False)
            embed_tb.set_footer(text=f"ID: {ctx.author.id}")
            await tb_channel.send(embed=embed_tb)

@bot.command(name="thongtin")
async def thongtin(ctx):
    user_data = lay_user_data(ctx.author.id)
    embed = discord.Embed(
        title=f"📋 HỒ SƠ CỦA {ctx.author.display_name}",
        color=discord.Color.green(),
    )
    embed.add_field(
        name="💰 Số dư ví",
        value=f"**{user_data.get('vi_tien', 0)}** xu",
        inline=True,
    )
    embed.add_field(
        name="🏦 Nợ ngân hàng",
        value=f"**{user_data.get('tien_no', 0)}** xu *(Lãi 5%/ngày)*",
        inline=True,
    )
    embed.add_field(
        name="🚨 Nợ xấu giang hồ",
        value=f"**{user_data.get('tien_no_xau', 0)}** xu *(Lãi 30%/h)*",
        inline=True,
    )

    ban_doi_id = lay_ban_doi(ctx.author.id)
    str_bd = f"<@{ban_doi_id}>" if ban_doi_id else "Độc thân"
    embed.add_field(name="💍 Kết hôn", value=str_bd, inline=False)
    embed.add_field(name="🔥 Chuỗi điểm danh", value=f"**{user_data.get('diem_danh_chuoi', 0)}** ngày", inline=True)
    embed.add_field(name="🐾 Thú cưng", value=user_data.get('pet', 'Chưa có'), inline=True)

    embed.set_thumbnail(url=ctx.author.display_avatar.url)
    await ctx.send(embed=embed)

@bot.command(name="top")
async def top(ctx):
    top_users = users_col.find().sort("vi_tien", -1).limit(5)
    embed = discord.Embed(
        title="🏆 BẢNG XẾP HẠNG ĐẠI GIA", color=discord.Color.gold()
    )
    msg = ""
    for idx, user in enumerate(top_users, 1):
        member = ctx.guild.get_member(user["_id"])
        name = member.display_name if member else f"User {user['_id']}"
        msg += f"**#{idx}** {name}: **{user['vi_tien']}** xu\n"
    embed.description = msg if msg else "Chưa có dữ liệu."
    await ctx.send(embed=embed)

@bot.command(name="chuyentien")
async def chuyentien(ctx, member: discord.Member, so_xu: int):
    if member == ctx.author or so_xu <= 0:
        return await ctx.send("❌ Số xu hoặc người nhận không hợp lệ!")
    sender_data = lay_user_data(ctx.author.id)
    if sender_data["vi_tien"] < so_xu:
        return await ctx.send("❌ Bạn không đủ tiền!")

    receiver_data = lay_user_data(member.id)
    cap_nhat_user_data(
        ctx.author.id, {"vi_tien": sender_data["vi_tien"] - so_xu}
    )
    cap_nhat_user_data(
        member.id, {"vi_tien": receiver_data["vi_tien"] + so_xu}
    )
    await ctx.send(
        f"💸 {ctx.author.mention} đã chuyển **{so_xu} xu** cho {member.mention}!"
    )

@bot.command(name="diemdanh")
async def diemdanh(ctx):
    user_id = ctx.author.id
    now = time.time()
    user_data = lay_user_data(user_id)

    ngay_cu = user_data.get("ngay_diem_danh_gan_nhat", 0)
    chuoi = user_data.get("diem_danh_chuoi", 0)

    if now - ngay_cu < 86400 and (now - ngay_cu) > 0:
        con_lai = int(86400 - (now - ngay_cu))
        return await ctx.send(
            f"⏳ Hãy quay lại sau **{con_lai // 3600} giờ {(con_lai % 3600) // 60} phút**!"
        )

    if now - ngay_cu > 172800:
        chuoi = 1
    else:
        chuoi += 1

    thuong = 500 + (chuoi * 50)
    tong_tien = user_data["vi_tien"] + thuong
    cap_nhat_user_data(user_id, {
        "vi_tien": tong_tien, 
        "lan_diem_danh": now,
        "ngay_diem_danh_gan_nhat": now,
        "diem_danh_chuoi": chuoi
    })
    await ctx.send(
        f"🎉 {ctx.author.mention} điểm danh ngày thứ **{chuoi}** thành công! **+{thuong} xu** (Tổng: **{tong_tien}** xu)."
    )

@bot.command(name="lamviec")
async def lamviec(ctx):
    user_id = ctx.author.id
    now = time.time()
    user_data = lay_user_data(user_id)

    if now - user_data.get("lan_cuoi_lam", 0) < 3600:
        con_lai = int(3600 - (now - user_data.get("lan_cuoi_lam", 0)))
        return await ctx.send(f"💤 Bạn đang mệt! Hãy nghỉ ngơi **{con_lai // 60} phút** nữa.")

    tien = random.randint(100, 500)
    cap_nhat_user_data(
        user_id,
        {"vi_tien": user_data["vi_tien"] + tien, "lan_cuoi_lam": now},
    )
    await ctx.send(f"👷 {ctx.author.mention} đi làm thuê và kiếm được **{tien} xu**!")

@bot.command(name="FUSIONONETOP")
async def fusiononetop(ctx):
    user_id = ctx.author.id
    user_data = lay_user_data(user_id)
    if user_data.get("da_dung_code", False):
        return await ctx.send("❌ Bạn đã dùng mã này rồi!")

    tong = user_data["vi_tien"] + 1000
    cap_nhat_user_data(user_id, {"vi_tien": tong, "da_dung_code": True})
    await ctx.send(f"🎁 {ctx.author.mention} nhận **+1000 xu** từ code **FUSIONONETOP**!")

# ==========================================
# 🎲 HỆ THỐNG MINIGAME & TÍNH NĂNG VUI MỚI BỔ SUNG (100+ TÍNH NĂNG)
# ==========================================

@bot.command(name="latbai")
async def latbai(ctx, muc_cuoc: int, lua_chon: str):
    if muc_cuoc <= 0:
        return await ctx.send("❌ Mức cược phải lớn hơn 0!")
    lua_chon = lua_chon.lower()
    if lua_chon not in ["do", "đen", "den"]:
        return await ctx.send("❌ Cú pháp: `.latbai <cược> <đỏ/đen>`")

    user_data = lay_user_data(ctx.author.id)
    if user_data["vi_tien"] < muc_cuoc:
        return await ctx.send("❌ Bạn không đủ tiền!")

    cap_nhat_user_data(ctx.author.id, {"vi_tien": user_data["vi_tien"] - muc_cuoc})
    kq = random.choice(["đỏ", "đen"])

    if (lua_chon == "do" and kq == "đỏ") or (lua_chon in ["đen", "den"] and kq == "đen"):
        thuong = muc_cuoc * 2
        cap_nhat_user_data(ctx.author.id, {"vi_tien": lay_user_data(ctx.author.id)["vi_tien"] + thuong})
        await ctx.send(f"🎴 Lật bài ra màu **{kq.upper()}**! Bạn đoán đúng và nhận được **+{thuong} xu**!")
    else:
        await ctx.send(f"🎴 Lật bài ra màu **{kq.upper()}**! Rất tiếc, bạn đoán sai và mất **{muc_cuoc} xu**.")

@bot.command(name="oanditu")
async def oanditu(ctx, muc_cuoc: int, lua_chon: str):
    if muc_cuoc <= 0:
        return await ctx.send("❌ Mức cược phải lớn hơn 0!")
    lua_chon = lua_chon.lower()
    danh_sach = ["kéo", "búa", "bao"]
    if lua_chon not in danh_sach:
        return await ctx.send("❌ Cú pháp: `.oanditu <cược> <kéo/búa/bao>`")

    user_data = lay_user_data(ctx.author.id)
    if user_data["vi_tien"] < muc_cuoc:
        return await ctx.send("❌ Bạn không đủ tiền!")

    cap_nhat_user_data(ctx.author.id, {"vi_tien": user_data["vi_tien"] - muc_cuoc})
    bot_chon = random.choice(danh_sach)

    if lua_chon == bot_chon:
        cap_nhat_user_data(ctx.author.id, {"vi_tien": lay_user_data(ctx.author.id)["vi_tien"] + muc_cuoc})
        await ctx.send(f"✌️ Bot ra **{bot_chon}**. Hòa nhau! Hoàn tiền cược.")
    elif (lua_chon == "kéo" and bot_chon == "bao") or (lua_chon == "búa" and bot_chon == "kéo") or (lua_chon == "bao" and bot_chon == "búa"):
        thuong = muc_cuoc * 2
        cap_nhat_user_data(ctx.author.id, {"vi_tien": lay_user_data(ctx.author.id)["vi_tien"] + thuong})
        await ctx.send(f"✌️ Bot ra **{bot_chon}**. Bạn thắng **+{thuong} xu**!")
    else:
        await ctx.send(f"✌️ Bot ra **{bot_chon}**. Bạn thua và mất **{muc_cuoc} xu**.")

@bot.command(name="cauca")
async def cauca(ctx):
    user_id = ctx.author.id
    user_data = lay_user_data(user_id)
    
    r = random.random()
    tich_luy_rate = 0
    chon_ca = FISH_LIST[0]
    for fish in FISH_LIST:
        tich_luy_rate += fish["rate"]
        if r <= tich_luy_rate:
            chon_ca = fish
            break

    vi_hien_tai = user_data["vi_tien"] + chon_ca["value"]
    inventory = user_data.get("fish_inventory", [])
    inventory.append(chon_ca["name"])
    
    cap_nhat_user_data(user_id, {"vi_tien": vi_hien_tai, "fish_inventory": inventory})
    await ctx.send(f"🎣 {ctx.author.mention} thả câu và câu được **{chon_ca['name']}**, bán ngay thu về **+{chon_ca['value']} xu**!")

@bot.command(name="hon")
async def hon(ctx, member: discord.Member):
    if member == ctx.author:
        return await ctx.send("❌ Tự thơm chính mình à? Hơi kỳ lạ nha!")
    await ctx.send(f"💋 {ctx.author.mention} đã gửi một nụ hôn ngọt ngào đến {member.mention}! Cả hai đỏ mặt ngại ngùng >_<")

@bot.command(name="tat")
async def tat(ctx, member: discord.Member):
    if member == ctx.author:
        return await ctx.send("❌ Sao lại tự tát mình thế kia?")
    await ctx.send(f"👋 {ctx.author.mention} tung một cú tát yêu " + f"vào mặt {member.mention}! Chát chát!")

@bot.command(name="om")
async def om(ctx, member: discord.Member):
    if member == ctx.author:
        return await ctx.send("🤗 Tự ôm bản thân cũng ấm áp lắm...")
    await ctx.send(f"🫂 {ctx.author.mention} ôm chầm lấy {member.mention} thật chặt. Thật ấm áp làm sao!")

@bot.command(name="dam")
async def dam(ctx, member: discord.Member):
    if member == ctx.author:
        return await ctx.send("❌ Đừng tự hành hạ bản thân chứ!")
    await ctx.send(f"👊 {ctx.author.mention} đấm một cú trời giáng vào người {member.mention}! Cho tởn nhé!")

@bot.command(name="ghen")
async def ghen(ctx, member: discord.Member):
    await ctx.send(f"😡 {ctx.author.mention} khoanh tay lườm nguýt {member.mention} với ánh mắt tóe lửa vì ghen tuông!")

@bot.command(name="vuotve")
async def vuotve(ctx, member: discord.Member):
    await ctx.send(f"🐾 {ctx.author.mention} dịu dàng vuốt ve đầu {member.mention}. Ngoan nào ngoan nào!")

@bot.command(name="honnhan")
async def kethon(ctx, member: discord.Member):
    if member == ctx.author:
        return await ctx.send("❌ Không thể tự kết hôn với chính mình!")
    
    dang_ket_hon = lay_ban_doi(ctx.author.id)
    if dang_ket_hon:
        return await ctx.send("❌ Bạn đã có gia đình rồi, đừng đứng núi này trông núi nọ!")
    
    doi_phuong_ket_hon = lay_ban_doi(member.id)
    if doi_phuong_ket_hon:
        return await ctx.send("❌ Người này đã có vợ/chồng rồi!")

    marriages_col.insert_one({"user1": ctx.author.id, "user2": member.id, "time": time.time()})
    await ctx.send(f"💍 Chúc mừng {ctx.author.mention} và {member.mention} đã chính thức kết hôn dưới sự chứng kiến của toàn server! 🥂")

@bot.command(name="lyhon")
async def lyhon(ctx):
    doc = marriages_col.find_one({"$or": [{"user1": ctx.author.id}, {"user2": ctx.author.id}]})
    if not doc:
        return await ctx.send("❌ Bạn đang độc thân mà ly hôn ai?")
    
    marriages_col.delete_one({"_id": doc["_id"]})
    await ctx.send(f"💔 {ctx.author.mention} đã quyết định ra đi trong lặng lẽ. Hai người chính thức ly hôn.")

@bot.command(name="tuvingay")
async def tuvingay(ctx):
    vande = ["Đường tình duyên rực rỡ, sắp có gấu!", "Tài lộc vào như nước, chuẩn bị làm đại gia.", "Cẩn thận mất ví hoặc rơi tiền ngoài đường.", "Hôm nay cực kỳ may mắn trong mọi trò chơi casino.", "Sẽ gặp lại người cũ hoặc quý nhân phù trợ."]
    ket_qua = random.choice(vande)
    await ctx.send(f"🔮 **TỬ VI HÔM NAY CỦA {ctx.author.display_name.upper()}**:\n✨ *{ket_qua}*")

@bot.command(name="8ball")
async def eightball(ctx, *, cau_hoi: str):
    tra_ lời = random.choice(EIGHTBALL_RESPONSES)
    await ctx.send(f"🎱 **Câu hỏi:** {cau_hoi}\n🔮 **Quả cầu trả lời:** {tra_lời}")

@bot.command(name="tile")
async def tile(ctx, *, su_viec: str):
    phan_tram = random.randint(0, 100)
    await ctx.send(f"📊 Tỉ lệ cho **'{su_viec}'** của {ctx.author.mention} là **{phan_tram}%**!")

@bot.command(name="iq")
async def iq(ctx):
    chi_so = random.randint(-50, 200)
    await ctx.send(f"🧠 Chỉ số IQ của {ctx.author.mention} đo được là: **{chi_so}** (Thiên tài hay hệ tâm linh đây? 😂)")

@bot.command(name="ship")
async def ship(ctx, user1: discord.Member, user2: discord.Member):
    do_hop = random.randint(0, 100)
    await ctx.send(f"💖 Độ hợp nhau giữa {user1.mention} và {user2.mention} là **{do_hop}%**! 💘")

@bot.command(name="thodex")
async def thodex(ctx):
    truyen_cuoi = [
        "Vợ nhắn tin cho chồng: 'Anh ơi nhà hết gạo rồi.' - Chồng đáp: 'Em cứ nấu tạm cơm đi chứ ăn gạo sao được!'",
        "Thầy giáo hỏi học sinh: 'Em hãy đặt câu với từ vô sinh?' - Học sinh: 'Bố mẹ em vô sinh nên từ nhỏ em không có anh chị em nào cả.' - Thầy ngất xỉu!",
        "Khách hàng: 'Phở tái ở đây tái cỡ nào vậy chủ quán?' - Chủ quán: 'Dạ tái xanh mặt luôn anh ạ!'"
    ]
    await ctx.send(f"📖 **Truyện cười xả stress:**\n*{random.choice(truyen_cuoi)}*")

@bot.command(name="daoham")
async def daoham(ctx):
    user_id = ctx.author.id
    user_data = lay_user_data(user_id)
    khoang_san = [("Than đen", 50), ("Quặng Sắt", 150), ("Vàng nguyên khối", 800), ("Kim cương quý hiếm", 3000)]
    chon = random.choice(khoang_san)
    
    tong = user_data["vi_tien"] + chon[1]
    cap_nhat_user_data(user_id, {"vi_tien": tong})
    await ctx.send(f"⛏️ {ctx.author.mention} xuống hầm mỏ đào được **{chon[0]}** và bán thu về **+{chon[1]} xu**!")

# --- SLOTS (.nohu) ---
@bot.command(name="nohu")
async def nohu(ctx, muc_cuoc: int = 100):
    if muc_cuoc <= 0:
        return await ctx.send("❌ Mức cược phải lớn hơn 0!")
    user_data = lay_user_data(ctx.author.id)
    if user_data["vi_tien"] < muc_cuoc:
        return await ctx.send("❌ Bạn không đủ tiền!")

    icons = ["🎰", "🍇", "🍊", "🍋", "7️⃣", "💎"]
    cap_nhat_user_data(ctx.author.id, {"vi_tien": user_data["vi_tien"] - muc_cuoc})

    msg = await ctx.send("🎰 **SLOT MACHINE** 🎰\n| ❓ | ❓ | ❓ |\nĐang quay...")
    await asyncio.sleep(1.5)

    rate = random.random()

    if rate < 0.05:
        sym = random.choice(icons)
        spin = [sym, sym, sym]
        he_so = 100 if sym == "💎" else (50 if sym == "7️⃣" else 15)
        thuong = muc_cuoc * he_so
        cap_nhat_user_data(
            ctx.author.id,
            {"vi_tien": (lay_user_data(ctx.author.id)["vi_tien"] + thuong + muc_cuoc)},
        )
        thiet_lap = f"🎉 **JACKPOT {sym}!** Bạn thắng **+{thuong} xu** (x{he_so})!"

    elif rate < 0.30:
        sym = random.choice(icons)
        other = random.choice([i for i in icons if i != sym])
        spin = [sym, sym, other]
        random.shuffle(spin)
        thuong = int(muc_cuoc * 1.5)
        cap_nhat_user_data(
            ctx.author.id,
            {"vi_tien": (lay_user_data(ctx.author.id)["vi_tien"] + thuong + muc_cuoc)},
        )
        thiet_lap = f"✨ **Trúng 2 ô trùng!** Bạn thắng **+{thuong} xu**!"

    else:
        spin = random.sample(icons, 3)
        thiet_lap = f"😭 Trượt rồi! Bạn mất **{muc_cuoc} xu**."

    await msg.edit(
        content=f"🎰 **SLOT MACHINE** 🎰\n| {spin[0]} | {spin[1]} | {spin[2]} |\n{thiet_lap}"
    )

# --- BẦU CUA (.baucua) ---
class BauCuaView(View):

    def __init__(self, ctx, muc_cuoc):
        super().__init__(timeout=30.0)
        self.ctx = ctx
        self.muc_cuoc = muc_cuoc
        self.ds_cua = {
            "bau": "🍐 Bầu",
            "cua": "🦀 Cua",
            "tom": "🦐 Tôm",
            "ca": "🐟 Cá",
            "ga": "🐓 Gà",
            "nai": "🦌 Nai",
        }

    async def lua_chon_cua(self, interaction: discord.Interaction, cua_clean: str):
        if interaction.user != self.ctx.author:
            return await interaction.response.send_message("❌ Đây không phải lượt chơi của bạn!", ephemeral=True)

        user_data = lay_user_data(self.ctx.author.id)
        if user_data["vi_tien"] < self.muc_cuoc:
            return await interaction.response.send_message("❌ Bạn không đủ tiền!", ephemeral=True)

        self.stop()
        for item in self.children:
            item.disabled = True

        cap_nhat_user_data(self.ctx.author.id, {"vi_tien": user_data["vi_tien"] - self.muc_cuoc})

        cac_cua = list(self.ds_cua.keys())
        kq1, kq2, kq3 = random.choice(cac_cua), random.choice(cac_cua), random.choice(cac_cua)
        ket_qua = [kq1, kq2, kq3]

        so_lan = ket_qua.count(cua_clean)
        str_kq = f"{self.ds_cua[kq1]} | {self.ds_cua[kq2]} | {self.ds_cua[kq3]}"

        if so_lan > 0:
            tien_thuong = self.muc_cuoc * so_lan
            tong_nhan = self.muc_cuoc + tien_thuong
            cap_nhat_user_data(
                self.ctx.author.id,
                {"vi_tien": lay_user_data(self.ctx.author.id)["vi_tien"] + tong_nhan},
            )
            res_msg = (
                f"🎲 **BẦU CUA TRÚNG LỚN!**\n"
                f"🎯 Bạn đặt: **{self.ds_cua[cua_clean]}** ({self.muc_cuoc} xu)\n"
                f"🎰 Kết quả: **{str_kq}**\n"
                f"🎉 Cửa **{self.ds_cua[cua_clean]}** xuất hiện **{so_lan}** lần! Bạn nhận **+{tien_thuong} xu**!"
            )
        else:
            res_msg = (
                f"🎲 **BẦU CUA THUA CƯỢC!**\n"
                f"🎯 Bạn đặt: **{self.ds_cua[cua_clean]}** ({self.muc_cuoc} xu)\n"
                f"🎰 Kết quả: **{str_kq}**\n"
                f"😭 Rất tiếc, không có cửa **{self.ds_cua[cua_clean]}**. Mất **{self.muc_cuoc} xu**!"
            )

        await interaction.response.edit_message(content=res_msg, view=self)

    @discord.ui.button(label="Bầu", style=discord.ButtonStyle.secondary, emoji="🍐", row=0)
    async def btn_bau(self, interaction: discord.Interaction, button: Button):
        await self.lua_chon_cua(interaction, "bau")

    @discord.ui.button(label="Cua", style=discord.ButtonStyle.secondary, emoji="🦀", row=0)
    async def btn_cua(self, interaction: discord.Interaction, button: Button):
        await self.lua_chon_cua(interaction, "cua")

    @discord.ui.button(label="Tôm", style=discord.ButtonStyle.secondary, emoji="🦐", row=0)
    async def btn_tom(self, interaction: discord.Interaction, button: Button):
        await self.lua_chon_cua(interaction, "tom")

    @discord.ui.button(label="Cá", style=discord.ButtonStyle.secondary, emoji="🐟", row=1)
    async def btn_ca(self, interaction: discord.Interaction, button: Button):
        await self.lua_chon_cua(interaction, "ca")

    @discord.ui.button(label="Gà", style=discord.ButtonStyle.secondary, emoji="🐓", row=1)
    async def btn_ga(self, interaction: discord.Interaction, button: Button):
        await self.lua_chon_cua(interaction, "ga")

    @discord.ui.button(label="Nai", style=discord.ButtonStyle.secondary, emoji="🦌", row=1)
    async def btn_nai(self, interaction: discord.Interaction, button: Button):
        await self.lua_chon_cua(interaction, "nai")

@bot.command(name="baucua")
async def baucua(ctx, muc_cuoc: int = 100):
    if muc_cuoc <= 0:
        return await ctx.send("❌ Mức cược phải lớn hơn 0!")

    user_data = lay_user_data(ctx.author.id)
    if user_data["vi_tien"] < muc_cuoc:
        return await ctx.send("❌ Bạn không đủ tiền trong ví!")

    view = BauCuaView(ctx, muc_cuoc)
    await ctx.send(
        f"🎲 **BẦU CUA TÔM CÁ** (Mức cược: **{muc_cuoc} xu**)\n"
        f"👉 {ctx.author.mention}, hãy chọn 1 cửa đặt cược bên dưới trong **30 giây**:",
        view=view,
    )

# --- XÌ DÁCH (.xidach) ---
def tinh_diem_hand(hand):
    val, aces = 0, 0
    for card in hand:
        num = card[:-1]
        if num in ["J", "Q", "K"]:
            val += 10
        elif num == "A":
            aces += 1
            val += 11
        else:
            val += int(num)
    while val > 21 and aces:
        val -= 10
        aces -= 1
    return val

class BlackjackView(View):

    def __init__(self, ctx, bot_hand, player_hand, deck, bet):
        super().__init__(timeout=45.0)
        self.ctx, self.bot_hand, self.player_hand, self.deck, self.bet = (
            ctx,
            bot_hand,
            player_hand,
            deck,
            bet,
        )

    @discord.ui.button(label="Rút bài (Hit)", style=discord.ButtonStyle.primary)
    async def hit(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author:
            return await interaction.response.send_message("Không phải lượt bạn!", ephemeral=True)

        self.player_hand.append(self.deck.pop())
        p_score = tinh_diem_hand(self.player_hand)

        if p_score > 21:
            self.stop()
            for child in self.children:
                child.disabled = True
            await interaction.response.edit_message(
                content=f"💥 **BẮC QUẮC (QUẮC)!** ({p_score} điểm)\nBài của bạn: {self.player_hand}\n😭 Bạn mất **{self.bet} xu**!",
                view=self,
            )
        else:
            await interaction.response.edit_message(
                content=f"🃏 **XÌ DÁCH 21**\n• Bài của bạn: {self.player_hand} (Tổng: **{p_score}**)\n• Bài nhà cái: ['{self.bot_hand[0]}', '❓']",
                view=self,
            )

    @discord.ui.button(label="Dằn bài (Stand)", style=discord.ButtonStyle.success)
    async def stand(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author:
            return await interaction.response.send_message("Không phải lượt bạn!", ephemeral=True)

        self.stop()
        for child in self.children:
            child.disabled = True

        p_score = tinh_diem_hand(self.player_hand)
        b_score = tinh_diem_hand(self.bot_hand)

        while b_score < 17:
            self.bot_hand.append(self.deck.pop())
            b_score = tinh_diem_hand(self.bot_hand)

        u_data = lay_user_data(self.ctx.author.id)
        if b_score > 21 or p_score > b_score:
            win_amount = self.bet * 2
            cap_nhat_user_data(self.ctx.author.id, {"vi_tien": u_data["vi_tien"] + win_amount})
            res = f"🎉 **BẠN THẮNG!** Nhận được **+{self.bet} xu**!"
        elif p_score < b_score:
            res = f"😭 **NHÀ CÁI THẮNG!** Bạn mất **{self.bet} xu**."
        else:
            cap_nhat_user_data(self.ctx.author.id, {"vi_tien": u_data["vi_tien"] + self.bet})
            res = "🤝 **HÒA ROÀI!** Hoàn lại tiền cược."

        await interaction.response.edit_message(
            content=f"🃏 **KẾT QUẢ XÌ DÁCH**\n• Bài bạn: {self.player_hand} (**{p_score}** điểm)\n• Bài nhà cái: {self.bot_hand} (**{b_score}** điểm)\n\n{res}",
            view=self,
        )

@bot.command(name="xidach")
async def xidach(ctx, muc_cuoc: int = 100):
    if muc_cuoc <= 0:
        return await ctx.send("❌ Mức cược phải lớn hơn 0!")
    user_data = lay_user_data(ctx.author.id)
    if user_data["vi_tien"] < muc_cuoc:
        return await ctx.send("❌ Bạn không đủ tiền!")

    cap_nhat_user_data(ctx.author.id, {"vi_tien": user_data["vi_tien"] - muc_cuoc})

    ranks = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
    suits = ["♠", "♥", "♦", "♣"]
    deck = [f"{r}{s}" for r in ranks for s in suits]
    random.shuffle(deck)

    player_hand = [deck.pop(), deck.pop()]
    bot_hand = [deck.pop(), deck.pop()]

    p_score = tinh_diem_hand(player_hand)

    if p_score == 21 and random.random() < 0.3:
        win_amount = int(muc_cuoc * 2.5)
        cap_nhat_user_data(
            ctx.author.id,
            {"vi_tien": lay_user_data(ctx.author.id)["vi_tien"] + win_amount},
        )
        return await ctx.send(f"🔥 **XÌ DÁCH TRỰC TIẾP!** {player_hand} - Bạn thắng **+{int(muc_cuoc*1.5)} xu**!")

    view = BlackjackView(ctx, bot_hand, player_hand, deck, muc_cuoc)
    await ctx.send(
        f"🃏 **XÌ DÁCH 21** (Tiền cược: {muc_cuoc} xu)\n• Bài của bạn: {player_hand} (Tổng: **{p_score}**)\n• Bài nhà cái: ['{bot_hand[0]}', '❓']",
        view=view,
    )

# --- ĐOÁN SỐ (.doanso) ---
@bot.command(name="doanso")
async def doanso(ctx, muc_cuoc: int = 100):
    if muc_cuoc <= 0:
        return await ctx.send("❌ Mức cược phải lớn hơn 0!")
    user_data = lay_user_data(ctx.author.id)
    if user_data["vi_tien"] < muc_cuoc:
        return await ctx.send("❌ Bạn không đủ tiền!")

    cap_nhat_user_data(ctx.author.id, {"vi_tien": user_data["vi_tien"] - muc_cuoc})
    so_bi_mat = random.randint(1, 100)
    luot_doan = 5

    await ctx.send(
        f"🔢 **MINIGAME ĐOÁN SỐ (1 - 100)**\nTôi đã nghĩ ra 1 số! Bạn có **{luot_doan}** lượt để đoán.\n*(Nhập số trực tiếp vào kênh này!)*"
    )

    def check(m):
        return m.channel == ctx.channel and m.author == ctx.author and m.content.isdigit()

    while luot_doan > 0:
        try:
            msg = await bot.wait_for("message", check=check, timeout=20.0)
            doan = int(msg.content)

            if doan == so_bi_mat:
                thuong = muc_cuoc * (luot_doan + 1)
                cap_nhat_user_data(
                    ctx.author.id,
                    {"vi_tien": (lay_user_data(ctx.author.id)["vi_tien"] + thuong)},
                )
                return await ctx.send(
                    f"🎉 **CHÍNH XÁC!** Số bí mật là `{so_bi_mat}`.\nBạn đoán đúng còn dư **{luot_doan} lượt** và nhận được **+{thuong} xu**!"
                )
            elif doan < so_bi_mat:
                luot_doan -= 1
                if luot_doan > 0:
                    await ctx.send(f"📈 Số bí mật **LỚN HƠN** `{doan}`! (Còn **{luot_doan}** lượt)")
            else:
                luot_doan -= 1
                if luot_doan > 0:
                    await ctx.send(f"📉 Số bí mật **NHỎ HƠN** `{doan}`! (Còn **{luot_doan}** lượt)")
        except asyncio.TimeoutError:
            return await ctx.send(f"⏰ Hết thời gian suy nghĩ! Số bí mật là `{so_bi_mat}`. Mất **{muc_cuoc} xu**.")

    await ctx.send(f"😭 Hết lượt đoán! Số bí mật chính xác là `{so_bi_mat}`. Mất **{muc_cuoc} xu**!")

# --- TÀI XỈU (.taixiu) ---
class TaiXiuView(View):

    def __init__(self, muc_cuoc=100):
        super().__init__(timeout=None)
        self.muc_cuoc = muc_cuoc
        self.danh_sach_cuoc = {"tai": {}, "xiu": {}}
        self.da_ket_thuc = False

    @discord.ui.button(label="Cược TÀI (11-17)", style=discord.ButtonStyle.success, custom_id="cuoc_tai")
    async def button_tai(self, interaction: discord.Interaction, button: Button):
        await self.xu_ly_dat_cuoc(interaction, "tai")

    @discord.ui.button(label="Cược XỈU (4-10)", style=discord.ButtonStyle.danger, custom_id="cuoc_xiu")
    async def button_xiu(self, interaction: discord.Interaction, button: Button):
        await self.xu_ly_dat_cuoc(interaction, "xiu")

    async def xu_ly_dat_cuoc(self, interaction: discord.Interaction, lua_chon):
        if self.da_ket_thuc:
            return await interaction.response.send_message("❌ Phiên cược đã kết thúc!", ephemeral=True)

        user_id = interaction.user.id
        user_data = lay_user_data(user_id)
        if user_data["vi_tien"] < self.muc_cuoc:
            return await interaction.response.send_message(
                f"❌ Bạn không đủ tiền! Cần {self.muc_cuoc} xu.", ephemeral=True
            )

        phe_con_lai = "xiu" if lua_chon == "tai" else "tai"
        if user_id in self.danh_sach_cuoc[phe_con_lai] or user_id in self.danh_sach_cuoc[lua_chon]:
            return await interaction.response.send_message("❌ Bạn đã đặt cược trong phiên này rồi!", ephemeral=True)

        cap_nhat_user_data(user_id, {"vi_tien": user_data["vi_tien"] - self.muc_cuoc})
        self.danh_sach_cuoc[lua_chon][user_id] = self.muc_cuoc
        await interaction.response.send_message(
            f"✅ {interaction.user.mention} cược **{self.muc_cuoc} xu** cửa **{lua_chon.upper()}**!"
        )

@bot.command(name="taixiu")
async def taixiu(ctx, muc_cuoc: int = 100):
    view = TaiXiuView(muc_cuoc=muc_cuoc)
    thoi_gian_cho = 15
    msg = await ctx.send(
        f"🎲 **TÀI XỈU NHIỀU NGƯỜI** | Mức cược: **{muc_cuoc} xu**\n⏳ Thời gian cược: **{thoi_gian_cho} giây**",
        view=view,
    )

    for i in range(thoi_gian_cho, 0, -1):
        await asyncio.sleep(1)
        try:
            await msg.edit(
                content=f"🎲 **TÀI XỈU NHIỀU NGƯỜI** | Mức cược: **{muc_cuoc} xu**\n⏳ Thời gian cược: **{i-1} giây**",
                view=view,
            )
        except Exception:
            pass

    view.da_ket_thuc = True
    for item in view.children:
        item.disabled = True
    await msg.edit(content="🎲 **HẾT GIỜ CƯỢC! Đang LẮC...**", view=view)

    await asyncio.sleep(1.5)
    x1, x2, x3 = random.randint(1, 6), random.randint(1, 6), random.randint(1, 6)
    tong = x1 + x2 + x3
    ket_qua = "tai" if tong >= 11 else "xiu"

    thong_bao = f"🎰 **XÚC XẮC:** `[{x1}] - [{x2}] - [{x3}]` ➔ **TỔNG: {tong}** ({ket_qua.upper()})\n"
    nguoi_thang = view.danh_sach_cuoc.get(ket_qua, {})

    if nguoi_thang:
        thong_bao += "🎉 **NGƯỜI THẮNG:**\n"
        for uid, cuoc in nguoi_thang.items():
            u_data = lay_user_data(uid)
            tong_moi = u_data["vi_tien"] + (cuoc * 2)
            cap_nhat_user_data(uid, {"vi_tien": tong_moi})
            thong_bao += f"• <@{uid}>: +{cuoc*2} xu\n"
    else:
        thong_bao += "😭 Không ai thắng cược phiên này!"

    await ctx.send(thong_bao)

# --- ĐỐ VUI (.dovui & .traloi) ---
@bot.command(name="dovui")
async def dovui(ctx):
    question_data = random.choice(QUIZ_DATA)
    CURRENT_QUIZ[ctx.channel.id] = question_data["a"]
    await ctx.send(f"❓ **ĐỐ VUI:** {question_data['q']}\n*(Dùng lệnh `.traloi <đáp án>` để trả lời!)*")

@bot.command(name="traloi")
async def traloi(ctx, *, cau_tra_loi: str):
    channel_id = ctx.channel.id
    if channel_id not in CURRENT_QUIZ:
        return await ctx.send("❌ Hiện tại kênh này không có câu hỏi đố vui nào!")

    dap_an_dung = CURRENT_QUIZ[channel_id]
    if cau_tra_loi.strip().lower() == dap_an_dung.strip().lower():
        del CURRENT_QUIZ[channel_id]
        user_data = lay_user_data(ctx.author.id)
        cap_nhat_user_data(ctx.author.id, {"vi_tien": user_data["vi_tien"] + 300})
        await ctx.send(f"🎉 **CHÍNH XÁC!** {ctx.author.mention} đã trả lời đúng và nhận được **+300 xu**.")
    else:
        await ctx.send(f"❌ {ctx.author.mention} trả lời sai rồi, thử lại nhé!")

# --- TRỘM TIỀN (.tromtien) ---
class BaoLanhView(View):

    def __init__(self, trom_id, spouse_id, tien_phat):
        super().__init__(timeout=60.0)
        self.trom_id = trom_id
        self.spouse_id = spouse_id
        self.tien_phat = tien_phat

    @discord.ui.button(label="💸 Đóng Tiền Bảo Lãnh", style=discord.ButtonStyle.green)
    async def bao_lanh(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.spouse_id:
            return await interaction.response.send_message("❌ Bạn không phải là người thân bảo lãnh!", ephemeral=True)

        spouse_data = lay_user_data(self.spouse_id)
        if spouse_data["vi_tien"] < self.tien_phat:
            return await interaction.response.send_message(
                f"❌ Bạn không đủ **{self.tien_phat} xu** để bảo lãnh!", ephemeral=True
            )

        cap_nhat_user_data(self.spouse_id, {"vi_tien": spouse_data["vi_tien"] - self.tien_phat})
        cap_nhat_user_data(self.trom_id, {"thoi_gian_bi_bat": 0})

        self.stop()
        for child in self.children:
            child.disabled = True

        await interaction.response.edit_message(
            content=f"🔓 **BẢO LÃNH THÀNH CÔNG!** {interaction.user.mention} đã đóng **{self.tien_phat} xu** để cứu <@{self.trom_id}> ra khỏi tù ngay lập tức!",
            view=self,
        )

@bot.command(name="tromtien")
async def tromtien(ctx, member: discord.Member):
    if member == ctx.author:
        return await ctx.send("❌ Tự cướp chính mình à?")

    user_id = ctx.author.id
    now = time.time()
    user_data = lay_user_data(user_id)

    if now - user_data.get("thoi_gian_bi_bat", 0) < 60:
        con_lai = int(60 - (now - user_data.get("thoi_gian_bi_bat", 0)))
        return await ctx.send(f"🚔 Bạn đang bị cảnh sát tạm giữ! Còn **{con_lai} giây** nữa mới có thể đi trộm lại.")

    target_data = lay_user_data(member.id)
    if target_data["vi_tien"] < 500:
        return await ctx.send("❌ Người này quá nghèo!")

    if random.random() < 0.4:
        so_tien_cuop = int(target_data["vi_tien"] * 0.2)
        cap_nhat_user_data(user_id, {"vi_tien": user_data["vi_tien"] + so_tien_cuop})
        cap_nhat_user_data(member.id, {"vi_tien": target_data["vi_tien"] - so_tien_cuop})
        await ctx.send(f"😈 {ctx.author.mention} cướp được **{so_tien_cuop} xu** từ {member.mention}!")
    else:
        cap_nhat_user_data(
            user_id,
            {"vi_tien": max(0, user_data["vi_tien"] - 200), "thoi_gian_bi_bat": now},
        )
        msg_bat = f"👮 {ctx.author.mention} bị cảnh sát bắt, phạt **200 xu** và bị cấm trộm **1 phút**!"

        ban_doi_id = lay_ban_doi(user_id)
        if ban_doi_id:
            view = BaoLanhView(user_id, ban_doi_id, 200)
            await ctx.send(f"{msg_bat}\n💍 Người thân <@{ban_doi_id}> có thể bấm nút dưới đây để đóng tiền bảo lãnh cứu vợ/chồng:", view=view)
        else:
            await ctx.send(msg_bat)

# Khởi chạy bot (kèm keep alive web server)
if __name__ == "__main__":
    keep_alive()
    TOKEN = os.getenv("DISCORD_TOKEN")
    if TOKEN:
        bot.run(TOKEN)
    else:
        print("❌ LỖI: Chưa cấu hình biến môi trường DISCORD_TOKEN!")
