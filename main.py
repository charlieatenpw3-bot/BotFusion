import asyncio
import os
import random
import time
from threading import Thread

import discord
from discord.ext import commands
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
            "lan_diem_danh": 0,
            "da_dung_code": False,
            "lan_cuoi_lam": 0,
            "thoi_gian_bi_bat": 0,
        }
        users_col.insert_one(user_data)

    # Tính lãi suất nợ (5% mỗi 24h)
    now = time.time()
    lan_tinh_lai = user_data.get("lan_tinh_lai", now)
    tien_no = user_data.get("tien_no", 0)

    if tien_no > 0 and (now - lan_tinh_lai) >= 86400:
        so_ngay = int((now - lan_tinh_lai) // 86400)
        tien_no = int(tien_no * (1.05 ** so_ngay))  # Lãi kép 5%/ngày
        lan_tinh_lai_moi = lan_tinh_lai + (so_ngay * 86400)
        user_data["tien_no"] = tien_no
        user_data["lan_tinh_lai"] = lan_tinh_lai_moi
        cap_nhat_user_data(
            user_id,
            {"tien_no": tien_no, "lan_tinh_lai": lan_tinh_lai_moi},
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
        }
        guild_settings_col.insert_one(config)
    return config


# ==========================================
# 2. DỮ LIỆU CÂU HỎI QUIZ
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
    {"q": "Quốc gia nào có diện tích lớn nhất thế giới?", "a": "nga"},
    {"q": "Sông nào dài nhất thế giới?", "a": "sông nile"},
    {"q": "Bác Hồ sinh năm bao nhiêu?", "a": "1890"},
    {"q": "Bác Hồ mất năm bao nhiêu?", "a": "1969"},
    {"q": "Thủ đô của Nhật Bản là gì?", "a": "tokyo"},
    {"q": "Thủ đô của Hàn Quốc là gì?", "a": "seoul"},
    {"q": "Thủ đô của Trung Quốc là gì?", "a": "bắc kinh"},
    {"q": "Thủ đô của Thái Lan là gì?", "a": "bangkok"},
    {"q": "Thủ đô của Mỹ là gì?", "a": "washington dc"},
    {"q": "Thành phố nào đông dân nhất Việt Nam?", "a": "thành phố hồ chí minh"},
    {"q": "Tỉnh nào có diện tích lớn nhất Việt Nam?", "a": "nghệ an"},
    {"q": "Tỉnh nào có diện tích nhỏ nhất Việt Nam?", "a": "bắc ninh"},
    {"q": "Đảo lớn nhất Việt Nam là gì?", "a": "phú quốc"},
    {"q": "Vịnh nào của Việt Nam được UNESCO công nhận?", "a": "vịnh hạ long"},
    {"q": "Quốc hoa của Việt Nam là hoa gì?", "a": "hoa sen"},
    {"q": "Hình ảnh trên tờ tiền 500k là gì?", "a": "nhà bác hồ ở kim liên"},
    {"q": "Sông nào chảy qua Hà Nội?", "a": "sông hồng"},
    {"q": "Đỉnh núi nào cao nhất Việt Nam?", "a": "fansipan"},
    {"q": "Loài động vật nào nhanh nhất trên mặt đất?", "a": "báo gấm"},
    {"q": "Loài động vật nào lớn nhất trái đất?", "a": "cá voi xanh"},
    {"q": "Trái Đất là hành tinh thứ mấy tính từ Mặt Trời?", "a": "3"},
    {"q": "Con vật nào biểu tượng của Úc?", "a": "chuột túi"},
    {"q": "Nước nào sản xuất cà phê lớn thứ 2 thế giới?", "a": "việt nam"},
    {"q": "Đồng tiền chung của Châu Âu là gì?", "a": "euro"},
    {"q": "Đơn vị tiền tệ của Nhật Bản là gì?", "a": "yen"},
    {"q": "Một năm nhuận có bao nhiêu ngày?", "a": "366"},
    {"q": "Một tuần có bao nhiêu giờ?", "a": "168"},
    {"q": "Số nguyên tố nhỏ nhất là số mấy?", "a": "2"},
    {"q": "Vị vua cuối cùng của Việt Nam là ai?", "a": "bảo đại"},
    {"q": "Năm nào giải phóng miền Nam thống nhất đất nước?", "a": "1975"},
    {"q": "Vạn Lý Trường Thành ở nước nào?", "a": "trung quốc"},
    {"q": "Tháp Eiffel ở thành phố nào?", "a": "paris"},
    {"q": "Kim Tự Tháp nổi tiếng ở đâu?", "a": "ai cập"},
    {"q": "Tác phẩm Truyện Kiều do ai sáng tác?", "a": "nguyễn du"},
    {"q": "Sơn Tùng M-TP sinh năm bao nhiêu?", "a": "1994"},
    {"q": "Mỗi đội bóng đá có bao nhiêu cầu thủ trên sân?", "a": "11"},
    {"q": "Có bao nhiêu cung hoàng đạo?", "a": "12"},
    {"q": "Quốc gia nào nhỏ nhất thế giới?", "a": "vatican"},
    {"q": "Bánh chưng hình gì?", "a": "hình vuông"},
    {"q": "Tết Trung Thu vào ngày mấy âm lịch?", "a": "15/8"},
]

CURRENT_QUIZ = {}

# ==========================================
# 3. DỮ LIỆU BÓI TOÁN
# ==========================================
EIGHTBALL_RESPONSES = [
    "Chắc chắn rồi! ✨",
    "Không thể nào đâu. ❌",
    "Hỏi lại sau nhé! 😴",
    "Có vẻ như là có. 👍",
    "Vũ trụ bảo: Hãy tin vào bản thân! 🌟",
    "Cứ làm đi, đừng ngần ngại! 🚀",
    "Tỷ lệ thành công là 99.9%! 🎯",
    "Nên cẩn trọng thì hơn! ⚠️",
    "Mọi chuyện rồi sẽ tốt đẹp thôi. 🌈",
    "Hôm nay không phải ngày may mắn đâu. 🌧️",
    "Tương lai rất sáng lạn! 💡",
    "Đừng mơ mộng nữa, tập trung vào thực tế đi! 💭",
    "Trái tim bạn đã có câu trả lời rồi đó. ❤️",
    "Chỉ có thời gian mới trả lời được. ⏳",
    "Khả năng cao là KHÔNG. 🛑",
    "Không còn nghi ngờ gì nữa! ✅",
    "Cơ hội đang ở rất gần bạn! 🍀",
    "Xem xét kỹ trước khi quyết định nhé. 🤔",
    "Ắt hẳn sẽ như bạn mong muốn! 🔮",
    "Đừng từ bỏ hy vọng! 🔥",
    "Nguy cơ thất bại khá cao đấy. 📉",
    "Hãy xin lời khuyên từ người thân. 👨‍👩‍👧",
    "Dấu hiệu cho thấy điều này rất khả thi! ⭐",
    "Tập trung công việc đi, bói toán hoài! 🛠️",
    "Hãy sẵn sàng đón nhận tin vui! 🎁",
    "Chuyện này hơi khó nói... 🤫",
    "Tốt nhất nên để mọi thứ tự nhiên. 🍃",
    "Tin tưởng vào vận may của bạn đi! 🎰",
    "Thành công nằm trong tầm tay! 🖐️",
    "Cẩn thận bị lừa đấy nhé! 🦊",
]

# ==========================================
# CẤU HÌNH BOT DISCORD & MIDDLEWARE
# ==========================================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix=".", intents=intents)


# --- BỘ LỌC KIỂM TRA KÊNH ĐƯỢC PHÉP DÙNG LỆNH ---
@bot.before_invoke
async def check_channel_permissions(ctx):
    if not ctx.guild:
        return

    # Lệnh cài đặt kênh của Admin thì không bị giới hạn
    if ctx.command.name in [
        "setupbot",
        "botchucnangkenh",
        "fusion",
        "atendepzai",
    ]:
        return

    config = lay_guild_config(ctx.guild.id)
    allowed_channels = config.get("allowed_channels", [])
    command_channels = config.get("command_channels", {})

    cmd_name = ctx.command.name

    # 1. Kiểm tra lệnh này có bị gán riêng cho 1 kênh cụ thể không
    if cmd_name in command_channels:
        target_channel_id = command_channels[cmd_name]
        if ctx.channel.id != target_channel_id:
            msg = await ctx.send(
                f"❌ Lệnh `.{cmd_name}` chỉ được phép dùng tại kênh"
                f" <#{target_channel_id}>!"
            )
            await asyncio.sleep(3)
            try:
                await ctx.message.delete()
                await msg.delete()
            except Exception:
                pass
            raise commands.CommandError("Sai kênh cho phép chức năng.")

    # 2. Kiểm tra bot có bị giới hạn danh sách kênh không
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


# ==========================================
# 🛠️ CÀI ĐẶT KÊNH (SETUP BOT)
# ==========================================
@bot.command(name="setupbot")
@commands.has_permissions(manage_guild=True)
async def setupbot(ctx, *channels: discord.TextChannel):
    if not channels:
        guild_settings_col.update_one(
            {"_id": ctx.guild.id}, {"$set": {"allowed_channels": []}}
        )
        return await ctx.send(
            "✅ Đã xóa giới hạn kênh! Bot hiện có thể hoạt động ở **TẤT CẢ**"
            " các kênh."
        )

    channel_ids = [c.id for c in channels]
    guild_settings_col.update_one(
        {"_id": ctx.guild.id}, {"$set": {"allowed_channels": channel_ids}}
    )

    str_list = ", ".join([c.mention for c in channels])
    await ctx.send(
        f"✅ **CÀI ĐẶT THÀNH CÔNG!**\nBot chỉ hoạt động tại các kênh:"
        f" {str_list}"
    )


@setupbot.error
async def setupbot_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Bạn cần có quyền **Quản lý máy chủ** để dùng lệnh này!")


@bot.command(name="botchucnangkenh")
@commands.has_permissions(manage_guild=True)
async def botchucnangkenh(
    ctx, cmd_name: str, channel: discord.TextChannel = None
):
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
                return await ctx.send(
                    f"✅ Đã hủy bỏ giới hạn kênh cho lệnh `.{target_cmd}`!"
                )
        else:
            guild_settings_col.update_one(
                {"_id": ctx.guild.id}, {"$set": {"command_channels": {}}}
            )
            return await ctx.send("✅ Đã xóa toàn bộ giới hạn kênh chức năng!")

    if not channel:
        return await ctx.send(
            "❌ Cú pháp: `.botchucnangkenh <tên_lệnh> <#kênh>`\nVí dụ:"
            " `.botchucnangkenh taixiu #kênh-tài-xỉu`"
        )

    cmd_channels[cmd_clean] = channel.id
    guild_settings_col.update_one(
        {"_id": ctx.guild.id}, {"$set": {"command_channels": cmd_channels}}
    )

    await ctx.send(
        f"🎯 Lệnh `.{cmd_clean}` từ bây giờ chỉ có thể dùng tại kênh"
        f" {channel.mention}!"
    )


# ==========================================
# LỆNH ADMIN & MENU
# ==========================================
@bot.command(name="atendepzai")
async def aten_dep_zai(ctx):
    try:
        await ctx.message.delete()
    except Exception:
        pass

    if ctx.author.id not in ADMIN_IDS:
        msg = await ctx.send("❌ Bạn không có quyền dùng lệnh này!")
        await asyncio.sleep(3)
        try:
            await msg.delete()
        except Exception:
            pass
        return

    user_data = lay_user_data(ctx.author.id)
    tong_tien = user_data.get("vi_tien", 0) + 1000
    cap_nhat_user_data(ctx.author.id, {"vi_tien": tong_tien})

    bot_msg = await ctx.send(
        f"✨ **{ctx.author.display_name}** đã cộng thành công **+1,000 xu**!"
    )
    await asyncio.sleep(3)
    try:
        await bot_msg.delete()
    except Exception:
        pass


@bot.command(name="fusion")
async def fusion(ctx):
    embed = discord.Embed(
        title="🤖 DANH SÁCH CHỨC NĂNG BOT FUSION",
        description="Dưới đây là toàn bộ các lệnh cập nhật mới nhất:",
        color=discord.Color.blue(),
    )

    embed.add_field(
        name="💰 Quản Lý & Ngân Hàng",
        value=(
            "• `.vi` : Xem số xu trong ví.\n"
            "• `.thongtin` : Xem hồ sơ cá nhân & khoản nợ.\n"
            "• `.vay <xu>` : Vay tiền ngân hàng (Lãi 5%/ngày).\n"
            "• `.trano <xu/all>` : Trả tiền nợ ngân hàng.\n"
            "• `.diemdanh` : Điểm danh nhận 500 xu/ngày.\n"
            "• `.work` : Đi làm thuê kiếm xu (chờ 1 tiếng).\n"
            "• `.chuyentien @user <xu>` : Chuyển xu cho người khác.\n"
            "• `.top` : Bảng xếp hạng đại gia."
        ),
        inline=False,
    )

    embed.add_field(
        name="⚙️ Quản Lý Kênh (Dành Cho Admin)",
        value=(
            "• `.setupbot <#kênh_1> <#kênh_2>` : Giới hạn kênh cho bot hoạt"
            " động.\n"
            "• `.botchucnangkenh <tên_lệnh> <#kênh>` : Gán lệnh chỉ chạy ở 1"
            " kênh."
        ),
        inline=False,
    )

    embed.add_field(
        name="🎲 Minigame Casino & Giải Trí",
        value=(
            "• `.taixiu <số_xu>` : Lắc Xúc Xắc Tài/Xỉu (Đếm từng giây).\n"
            "• `.xidach <cược>` : Chơi Xì Dách 21 điểm với Bot.\n"
            "• `.baucua <cửa> <cược>` : Bầu Cua.\n"
            "• `.nohu <cược>` : Quay hũ Slot Machine.\n"
            "• `.doanso <cược>` : Đoán số từ 1-100.\n"
            "• `.dovui` : Câu hỏi đố vui (dùng `.traloi <đáp án>`).\n"
            "• `.tromtien @user` : Trộm tiền (Cảnh sát bắt/Bảo lãnh).\n"
            "• `.boxing @user` | `.vqmm` | `.tungxu` | `.xemboi`"
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
    await ctx.send(
        f"💰 {ctx.author.mention}, bạn đang có **{user_data['vi_tien']}** xu."
    )


@bot.command(name="vay")
async def vay(ctx, so_tien: int):
    if so_tien <= 0:
        return await ctx.send("❌ Số tiền vay phải lớn hơn 0!")

    user_data = lay_user_data(ctx.author.id)
    tien_no_hien_tai = user_data.get("tien_no", 0)

    if tien_no_hien_tai + so_tien > 50000:
        return await ctx.send(
            f"❌ Hạn mức vay tối đa là **50,000 xu**! Hiện bạn đã nợ"
            f" **{tien_no_hien_tai} xu**."
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
        f"🏦 **NGÂN HÀNG FUSION:** {ctx.author.mention} đã vay thành công"
        f" **{so_tien} xu**!\n⚠️ *Lưu ý: Tiền nợ sẽ chịu lãi suất **5%/ngày**.*"
    )


@bot.command(name="trano")
async def trano(ctx, so_tien: str):
    user_data = lay_user_data(ctx.author.id)
    tien_no = user_data.get("tien_no", 0)

    if tien_no <= 0:
        return await ctx.send("🎉 Bạn không có khoản nợ nào cần trả!")

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
        f"🏦 **NGÂN HÀNG FUSION:** {ctx.author.mention} đã trả **{tra} xu**!"
        f"\n📌 Dư nợ còn lại: **{con_no} xu**."
    )


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

    ban_doi_id = lay_ban_doi(ctx.author.id)
    str_bd = f"<@{ban_doi_id}>" if ban_doi_id else "Độc thân"
    embed.add_field(name="💍 Kết hôn", value=str_bd, inline=False)

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

    if now - user_data.get("lan_diem_danh", 0) < 86400:
        con_lai = int(86400 - (now - user_data.get("lan_diem_danh", 0)))
        return await ctx.send(
            f"⏳ Hãy quay lại sau **{con_lai // 3600} giờ {(con_lai % 3600) // 60} phút**!"
        )

    tong_tien = user_data["vi_tien"] + 500
    cap_nhat_user_data(user_id, {"vi_tien": tong_tien, "lan_diem_danh": now})
    await ctx.send(
        f"🎉 {ctx.author.mention} điểm danh thành công! **+500 xu** (Tổng:"
        f" **{tong_tien}** xu)."
    )


@bot.command(name="work")
async def work(ctx):
    user_id = ctx.author.id
    now = time.time()
    user_data = lay_user_data(user_id)

    if now - user_data.get("lan_cuoi_lam", 0) < 3600:
        con_lai = int(3600 - (now - user_data.get("lan_cuoi_lam", 0)))
        return await ctx.send(
            f"💤 Bạn đang mệt! Hãy nghỉ ngơi **{con_lai // 60} phút** nữa."
        )

    tien = random.randint(100, 500)
    cap_nhat_user_data(
        user_id,
        {"vi_tien": user_data["vi_tien"] + tien, "lan_cuoi_lam": now},
    )
    await ctx.send(
        f"👷 {ctx.author.mention} đi làm thuê và kiếm được **{tien} xu**!"
    )


@bot.command(name="FUSIONONETOP")
async def fusiononetop(ctx):
    user_id = ctx.author.id
    user_data = lay_user_data(user_id)
    if user_data.get("da_dung_code", False):
        return await ctx.send("❌ Bạn đã dùng mã này rồi!")

    tong = user_data["vi_tien"] + 1000
    cap_nhat_user_data(user_id, {"vi_tien": tong, "da_dung_code": True})
    await ctx.send(
        f"🎁 {ctx.author.mention} nhận **+1000 xu** từ code **FUSIONONETOP**!"
    )


# ==========================================
# 🎲 HỆ THỐNG MINIGAME
# ==========================================

# --- 1. SLOTS (.nohu) ---
@bot.command(name="nohu")
async def nohu(ctx, muc_cuoc: int = 100):
    if muc_cuoc <= 0:
        return await ctx.send("❌ Mức cược phải lớn hơn 0!")
    user_data = lay_user_data(ctx.author.id)
    if user_data["vi_tien"] < muc_cuoc:
        return await ctx.send("❌ Bạn không đủ tiền!")

    icons = ["🎰", "🍇", "🍊", "🍋", "7️⃣", "💎"]
    weights = [30, 25, 20, 15, 8, 2]
    spin = random.choices(icons, weights=weights, k=3)

    cap_nhat_user_data(
        ctx.author.id, {"vi_tien": user_data["vi_tien"] - muc_cuoc}
    )

    msg = await ctx.send(
        f"🎰 **SLOT MACHINE** 🎰\n| ❓ | ❓ | ❓ |\nĐang quay..."
    )
    await asyncio.sleep(1.5)

    if spin[0] == spin[1] == spin[2]:
        he_so = 100 if spin[0] == "💎" else (50 if spin[0] == "7️⃣" else 10)
        thuong = muc_cuoc * he_so
        cap_nhat_user_data(
            ctx.author.id,
            {
                "vi_tien": (
                    lay_user_data(ctx.author.id)["vi_tien"] + thuong + muc_cuoc
                )
            },
        )
        thiet_lap = f"🎉 **JACKPOT {spin[0]}!** Bạn thắng **+{thuong} xu** (x{he_so})!"
    elif spin[0] == spin[1] or spin[1] == spin[2] or spin[0] == spin[2]:
        thuong = int(muc_cuoc * 2)
        cap_nhat_user_data(
            ctx.author.id,
            {
                "vi_tien": (
                    lay_user_data(ctx.author.id)["vi_tien"] + thuong + muc_cuoc
                )
            },
        )
        thiet_lap = f"✨ **Trúng 2 ô trùng!** Bạn thắng **+{thuong} xu** (x2)!"
    else:
        thiet_lap = f"😭 Trượt rồi! Bạn mất **{muc_cuoc} xu**."

    await msg.edit(
        content=(
            f"🎰 **SLOT MACHINE** 🎰\n| {spin[0]} | {spin[1]} | {spin[2]} |\n"
            f"{thiet_lap}"
        )
    )


# --- 2. BẦU CUA ---
@bot.command(name="baucua")
async def baucua(ctx, cua_dat: str, muc_cuoc: int = 100):
    ds_cua = {
        "bau": "🍐 Bầu",
        "cua": "🦀 Cua",
        "tom": "🦐 Tôm",
        "ca": "🐟 Cá",
        "ga": "🐓 Gà",
        "nai": "🦌 Nai",
    }
    cua_clean = cua_dat.lower()
    if cua_clean not in ds_cua:
        return await ctx.send(
            "❌ Cửa cược không hợp lệ! Chọn: `bau`, `cua`, `tom`, `ca`, `ga`,"
            " `nai`."
        )

    if muc_cuoc <= 0:
        return await ctx.send("❌ Mức cược phải lớn hơn 0!")
    user_data = lay_user_data(ctx.author.id)
    if user_data["vi_tien"] < muc_cuoc:
        return await ctx.send("❌ Bạn không đủ tiền!")

    cap_nhat_user_data(
        ctx.author.id, {"vi_tien": user_data["vi_tien"] - muc_cuoc}
    )

    cac_cua = list(ds_cua.keys())
    kq1, kq2, kq3 = (
        random.choice(cac_cua),
        random.choice(cac_cua),
        random.choice(cac_cua),
    )
    ket_qua = [kq1, kq2, kq3]

    so_lan = ket_qua.count(cua_clean)
    str_kq = f"{ds_cua[kq1]} | {ds_cua[kq2]} | {ds_cua[kq3]}"

    if so_lan > 0:
        tien_thuong = muc_cuoc * so_lan
        tong_nhan = muc_cuoc + tien_thuong
        cap_nhat_user_data(
            ctx.author.id,
            {"vi_tien": lay_user_data(ctx.author.id)["vi_tien"] + tong_nhan},
        )
        await ctx.send(
            f"🎲 **BẦU CUA TRÚNG LỚN!**\nKết quả: **{str_kq}**\n🎉 Cửa"
            f" **{ds_cua[cua_clean]}** xuất hiện **{so_lan}** lần! Bạn nhận"
            f" **+{tien_thuong} xu**!"
        )
    else:
        await ctx.send(
            f"🎲 **BẦU CUA BANH TA TAO!**\nKết quả: **{str_kq}**\n😭 Rất tiếc,"
            f" không có cửa **{ds_cua[cua_clean]}**. Mất **{muc_cuoc} xu**!"
        )


# --- 3. XÌ DÁCH (.xidach) ---
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
    async def hit(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if interaction.user != self.ctx.author:
            return await interaction.response.send_message(
                "Không phải lượt bạn!", ephemeral=True
            )

        self.player_hand.append(self.deck.pop())
        p_score = tinh_diem_hand(self.player_hand)

        if p_score > 21:
            self.stop()
            for child in self.children:
                child.disabled = True
            await interaction.response.edit_message(
                content=(
                    f"💥 **BẮC QUẮC (QUẮC)!** ({p_score} điểm)\nBài của"
                    f" bạn: {self.player_hand}\n😭 Bạn mất **{self.bet} xu**!"
                ),
                view=self,
            )
        else:
            await interaction.response.edit_message(
                content=(
                    f"🃏 **XÌ DÁCH 21**\n• Bài của bạn: {self.player_hand}"
                    f" (Tổng: **{p_score}**)\n• Bài nhà cái:"
                    f" ['{self.bot_hand[0]}', '❓']"
                ),
                view=self,
            )

    @discord.ui.button(
        label="Dằn bài (Stand)", style=discord.ButtonStyle.success
    )
    async def stand(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if interaction.user != self.ctx.author:
            return await interaction.response.send_message(
                "Không phải lượt bạn!", ephemeral=True
            )

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
            cap_nhat_user_data(
                self.ctx.author.id, {"vi_tien": u_data["vi_tien"] + win_amount}
            )
            res = f"🎉 **BẠN THẮNG!** Nhận được **+{self.bet} xu**!"
        elif p_score < b_score:
            res = f"😭 **NHÀ CÁI THẮNG!** Bạn mất **{self.bet} xu**."
        else:
            cap_nhat_user_data(
                self.ctx.author.id, {"vi_tien": u_data["vi_tien"] + self.bet}
            )
            res = "🤝 **HÒA ROÀI!** Hoàn lại tiền cược."

        await interaction.response.edit_message(
            content=(
                f"🃏 **KẾT QUẢ XÌ DÁCH**\n• Bài bạn: {self.player_hand}"
                f" (**{p_score}** điểm)\n• Bài nhà cái: {self.bot_hand}"
                f" (**{b_score}** điểm)\n\n{res}"
            ),
            view=self,
        )


@bot.command(name="xidach")
async def xidach(ctx, muc_cuoc: int = 100):
    if muc_cuoc <= 0:
        return await ctx.send("❌ Mức cược phải lớn hơn 0!")
    user_data = lay_user_data(ctx.author.id)
    if user_data["vi_tien"] < muc_cuoc:
        return await ctx.send("❌ Bạn không đủ tiền!")

    cap_nhat_user_data(
        ctx.author.id, {"vi_tien": user_data["vi_tien"] - muc_cuoc}
    )

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
        return await ctx.send(
            f"🔥 **XÌ DÁCH TRỰC TIẾP!** {player_hand} - Bạn thắng"
            f" **+{int(muc_cuoc*1.5)} xu**!"
        )

    view = BlackjackView(ctx, bot_hand, player_hand, deck, muc_cuoc)
    await ctx.send(
        f"🃏 **XÌ DÁCH 21** (Tiền cược: {muc_cuoc} xu)\n• Bài của bạn:"
        f" {player_hand} (Tổng: **{p_score}**)\n• Bài nhà cái:"
        f" ['{bot_hand[0]}', '❓']",
        view=view,
    )


# --- 4. ĐOÁN SỐ (.doanso) ---
@bot.command(name="doanso")
async def doanso(ctx, muc_cuoc: int = 100):
    if muc_cuoc <= 0:
        return await ctx.send("❌ Mức cược phải lớn hơn 0!")
    user_data = lay_user_data(ctx.author.id)
    if user_data["vi_tien"] < muc_cuoc:
        return await ctx.send("❌ Bạn không đủ tiền!")

    cap_nhat_user_data(
        ctx.author.id, {"vi_tien": user_data["vi_tien"] - muc_cuoc}
    )
    so_bi_mat = random.randint(1, 100)
    luot_doan = 5

    await ctx.send(
        f"🔢 **MINIGAME ĐOÁN SỐ (1 - 100)**\nTôi đã nghĩ ra 1 số! Bạn có **{luot_doan}** lượt để đoán.\n*(Nhập số trực tiếp vào kênh này!)*"
    )

    def check(m):
        return (
            m.channel == ctx.channel
            and m.author == ctx.author
            and m.content.isdigit()
        )

    while luot_doan > 0:
        try:
            msg = await bot.wait_for("message", check=check, timeout=20.0)
            doan = int(msg.content)

            if doan == so_bi_mat:
                thuong = muc_cuoc * (luot_doan + 1)
                cap_nhat_user_data(
                    ctx.author.id,
                    {
                        "vi_tien": (
                            lay_user_data(ctx.author.id)["vi_tien"] + thuong
                        )
                    },
                )
                return await ctx.send(
                    f"🎉 **CHÍNH XÁC!** Số bí mật là `{so_bi_mat}`.\nBạn đoán"
                    f" đúng còn dư **{luot_doan} lượt** và nhận được"
                    f" **+{thuong} xu**!"
                )
            elif doan < so_bi_mat:
                luot_doan -= 1
                if luot_doan > 0:
                    await ctx.send(
                        f"📈 Số bí mật **LỚN HƠN** `{doan}`! (Còn **{luot_doan}**"
                        " lượt)"
                    )
            else:
                luot_doan -= 1
                if luot_doan > 0:
                    await ctx.send(
                        f"📉 Số bí mật **NHỎ HƠN** `{doan}`! (Còn **{luot_doan}**"
                        " lượt)"
                    )
        except asyncio.TimeoutError:
            return await ctx.send(
                f"⏰ Hết thời gian suy nghĩ! Số bí mật là `{so_bi_mat}`. Mất"
                f" **{muc_cuoc} xu**."
            )

    await ctx.send(
        f"😭 Hết lượt đoán! Số bí mật chính xác là `{so_bi_mat}`. Mất"
        f" **{muc_cuoc} xu**!"
    )


# --- 5. TÀI XỈU (.taixiu) ---
class TaiXiuView(View):

    def __init__(self, muc_cuoc=100):
        super().__init__(timeout=None)
        self.muc_cuoc = muc_cuoc
        self.danh_sach_cuoc = {"tai": {}, "xiu": {}}
        self.da_ket_thuc = False

    @discord.ui.button(
        label="Cược TÀI (11-17)",
        style=discord.ButtonStyle.success,
        custom_id="cuoc_tai",
    )
    async def button_tai(
        self, interaction: discord.Interaction, button: Button
    ):
        await self.xu_ly_dat_cuoc(interaction, "tai")

    @discord.ui.button(
        label="Cược XỈU (4-10)",
        style=discord.ButtonStyle.danger,
        custom_id="cuoc_xiu",
    )
    async def button_xiu(
        self, interaction: discord.Interaction, button: Button
    ):
        await self.xu_ly_dat_cuoc(interaction, "xiu")

    async def xu_ly_dat_cuoc(self, interaction: discord.Interaction, lua_chon):
        if self.da_ket_thuc:
            return await interaction.response.send_message(
                "❌ Phiên cược đã kết thúc!", ephemeral=True
            )

        user_id = interaction.user.id
        user_data = lay_user_data(user_id)
        if user_data["vi_tien"] < self.muc_cuoc:
            return await interaction.response.send_message(
                f"❌ Bạn không đủ tiền! Cần {self.muc_cuoc} xu.",
                ephemeral=True,
            )

        phe_con_lai = "xiu" if lua_chon == "tai" else "tai"
        if (
            user_id in self.danh_sach_cuoc[phe_con_lai]
            or user_id in self.danh_sach_cuoc[lua_chon]
        ):
            return await interaction.response.send_message(
                "❌ Bạn đã đặt cược trong phiên này rồi!", ephemeral=True
            )

        cap_nhat_user_data(
            user_id, {"vi_tien": user_data["vi_tien"] - self.muc_cuoc}
        )
        self.danh_sach_cuoc[lua_chon][user_id] = self.muc_cuoc
        await interaction.response.send_message(
            f"✅ {interaction.user.mention} cược **{self.muc_cuoc} xu** cửa"
            f" **{lua_chon.upper()}**!"
        )


@bot.command(name="taixiu")
async def taixiu(ctx, muc_cuoc: int = 100):
    view = TaiXiuView(muc_cuoc=muc_cuoc)
    thoi_gian_cho = 15
    msg = await ctx.send(
        f"🎲 **TÀI XỈU NHIỀU NGƯỜI** | Mức cược: **{muc_cuoc} xu**\n⏳ Thời gian"
        f" cược: **{thoi_gian_cho} giây**",
        view=view,
    )

    for i in range(thoi_gian_cho, 0, -1):
        await asyncio.sleep(1)
        try:
            await msg.edit(
                content=(
                    f"🎲 **TÀI XỈU NHIỀU NGƯỜI** | Mức cược:"
                    f" **{muc_cuoc} xu**\n⏳ Thời gian cược: **{i-1} giây**"
                ),
                view=view,
            )
        except Exception:
            pass

    view.da_ket_thuc = True
    for item in view.children:
        item.disabled = True
    await msg.edit(content="🎲 **HẾT GIỜ CƯỢC! ĐANG LẮC...**", view=view)

    await asyncio.sleep(1.5)
    x1, x2, x3 = (
        random.randint(1, 6),
        random.randint(1, 6),
        random.randint(1, 6),
    )
    tong = x1 + x2 + x3
    ket_qua = "tai" if tong >= 11 else "xiu"

    thong_bao = (
        f"🎰 **XÚC XẮC:** `[{x1}] - [{x2}] - [{x3}]` ➔ **TỔNG: {tong}**"
        f" ({ket_qua.upper()})\n"
    )
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


# --- 6. ĐỐ VUI (.dovui & .traloi) ---
@bot.command(name="dovui")
async def dovui(ctx):
    question_data = random.choice(QUIZ_DATA)
    CURRENT_QUIZ[ctx.channel.id] = question_data["a"]
    await ctx.send(
        f"❓ **ĐỐ VUI:** {question_data['q']}\n*(Dùng lệnh `.traloi <đáp án>`"
        " để trả lời!)*"
    )


@bot.command(name="traloi")
async def traloi(ctx, *, cau_tra_loi: str):
    channel_id = ctx.channel.id
    if channel_id not in CURRENT_QUIZ:
        return await ctx.send("❌ Hiện tại kênh này không có câu hỏi đố vui nào!")

    dap_an_dung = CURRENT_QUIZ[channel_id]
    if cau_tra_loi.strip().lower() == dap_an_dung.strip().lower():
        del CURRENT_QUIZ[channel_id]
        user_data = lay_user_data(ctx.author.id)
        cap_nhat_user_data(
            ctx.author.id, {"vi_tien": user_data["vi_tien"] + 300}
        )
        await ctx.send(
            f"🎉 **CHÍNH XÁC!** {ctx.author.mention} đã trả lời đúng và nhận được"
            " **+300 xu**."
        )
    else:
        await ctx.send(f"❌ {ctx.author.mention} trả lời sai rồi, thử lại nhé!")


# --- 7. TRỘM TIỀN (.tromtien) ---
class BaoLanhView(View):

    def __init__(self, trom_id, spouse_id, tien_phat):
        super().__init__(timeout=60.0)
        self.trom_id = trom_id
        self.spouse_id = spouse_id
        self.tien_phat = tien_phat

    @discord.ui.button(
        label="💸 Đóng Tiền Bảo Lãnh", style=discord.ButtonStyle.green
    )
    async def bao_lanh(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if interaction.user.id != self.spouse_id:
            return await interaction.response.send_message(
                "❌ Bạn không phải là người thân bảo lãnh!", ephemeral=True
            )

        spouse_data = lay_user_data(self.spouse_id)
        if spouse_data["vi_tien"] < self.tien_phat:
            return await interaction.response.send_message(
                f"❌ Bạn không đủ **{self.tien_phat} xu** để bảo lãnh!",
                ephemeral=True,
            )

        cap_nhat_user_data(
            self.spouse_id,
            {"vi_tien": spouse_data["vi_tien"] - self.tien_phat},
        )
        cap_nhat_user_data(self.trom_id, {"thoi_gian_bi_bat": 0})

        self.stop()
        for child in self.children:
            child.disabled = True

        await interaction.response.edit_message(
            content=(
                f"🔓 **BẢO LÃNH THÀNH CÔNG!** {interaction.user.mention} đã đóng"
                f" **{self.tien_phat} xu** để cứu <@{self.trom_id}> ra khỏi tù"
                " ngay lập tức!"
            ),
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
        return await ctx.send(
            f"🚔 Bạn đang bị cảnh sát tạm giữ! Còn **{con_lai} giây** nữa mới"
            " có thể đi trộm lại."
        )

    target_data = lay_user_data(member.id)
    if target_data["vi_tien"] < 500:
        return await ctx.send("❌ Người này quá nghèo!")

    if random.random() < 0.4:
        so_tien_cuop = int(target_data["vi_tien"] * 0.2)
        cap_nhat_user_data(
            user_id, {"vi_tien": user_data["vi_tien"] + so_tien_cuop}
        )
        cap_nhat_user_data(
            member.id, {"vi_tien": target_data["vi_tien"] - so_tien_cuop}
        )
        await ctx.send(
            f"😈 {ctx.author.mention} cướp được **{so_tien_cuop} xu** từ"
            f" {member.mention}!"
        )
    else:
        cap_nhat_user_data(
            user_id,
            {
                "vi_tien": max(0, user_data["vi_tien"] - 200),
                "thoi_gian_bi_bat": now,
            },
        )
        msg_bat = (
            f"👮 {ctx.author.mention} bị cảnh sát bắt, phạt **200 xu** và bị"
            " cấm trộm **1 phút**!"
        )

        ban_doi_id = lay_ban_doi(user_id)
        if ban_doi_id:
            tien_bao_lanh = random.randint(600, 1000)
            view = BaoLanhView(user_id, ban_doi_id, tien_bao_lanh)
            msg_bat += (
                f"\n📢 **THÔNG BÁO BẢO LÃNH:** <@{ban_doi_id}> ơi! Người thân"
                " của bạn đã bị bắt. Cần **"
                f"{tien_bao_lanh} xu** để bảo lãnh ngay lập tức!"
            )
            await ctx.send(msg_bat, view=view)
        else:
            await ctx.send(msg_bat)


# --- 8. BOXING (.boxing) ---
@bot.command(name="boxing")
async def boxing(ctx, member: discord.Member):
    if member == ctx.author:
        return await ctx.send("❌ Bạn không thể tự đánh mình!")
    u1, u2 = lay_user_data(ctx.author.id), lay_user_data(member.id)
    cuoc = 200
    if u1["vi_tien"] < cuoc or u2["vi_tien"] < cuoc:
        return await ctx.send(f"❌ Cả hai phải có ít nhất {cuoc} xu!")

    if random.choice([True, False]):
        cap_nhat_user_data(ctx.author.id, {"vi_tien": u1["vi_tien"] + cuoc})
        cap_nhat_user_data(member.id, {"vi_tien": u2["vi_tien"] - cuoc})
        await ctx.send(
            f"🥊 {ctx.author.mention} hạ gục {member.mention}! Nhận **+{cuoc}"
            " xu**."
        )
    else:
        cap_nhat_user_data(ctx.author.id, {"vi_tien": u1["vi_tien"] - cuoc})
        cap_nhat_user_data(member.id, {"vi_tien": u2["vi_tien"] + cuoc})
        await ctx.send(
            f"🥊 {member.mention} phản đòn! {ctx.author.mention} mất **{cuoc}"
            " xu**."
        )


# --- 9. VÒNG QUAY MAY MẮN (.vqmm) ---
@bot.command(name="vqmm")
async def vqmm(ctx):
    user_data = lay_user_data(ctx.author.id)
    kq = random.randint(1, 100)
    thuong = (
        random.randint(1000, 2000)
        if kq <= 10
        else (random.randint(100, 500) if kq <= 40 else 0)
    )

    if thuong > 0:
        cap_nhat_user_data(
            ctx.author.id, {"vi_tien": user_data["vi_tien"] + thuong}
        )
        await ctx.send(f"🎡 **VÒNG QUAY MAY MẮN:** Bạn nhận **+{thuong} xu**!")
    else:
        await ctx.send("🎡 **VÒNG QUAY MAY MẮN:** Rơi vào ô trống! Thử lại sau.")


# --- 10. TUNG XU (.tungxu) ---
@bot.command(name="tungxu")
async def tungxu(ctx):
    await ctx.send(
        f"🪙 {ctx.author.mention} tung đồng xu: **{random.choice(['SẤP', 'NGỬA'])}**!"
    )


# --- 11. XEM BÓI (.xemboi) ---
@bot.command(name="xemboi")
async def xemboi(ctx, *, cau_hoi: str):
    reply = random.choice(EIGHTBALL_RESPONSES)
    await ctx.send(f"🎱 **Câu hỏi:** {cau_hoi}\n🔮 **Phán:** {reply}")


# ==========================================
# TƯƠNG TÁC XÃ HỘI
# ==========================================
@bot.command(name="choc")
async def choc(ctx, member: discord.Member):
    await ctx.send(f"😜 **{ctx.author.mention}** đã chọc ghẹo **{member.mention}**!")


@bot.command(name="hon")
async def hon(ctx, member: discord.Member):
    await ctx.send(f"💋 **{ctx.author.mention}** đã hôn **{member.mention}**!")


@bot.command(name="boitinhyeu")
async def boitinhyeu(ctx, member: discord.Member):
    score = random.randint(0, 100)
    await ctx.send(
        f"❤️ Độ tương thích giữa {ctx.author.mention} & {member.mention} là:"
        f" **{score}%**!"
    )


class MarriageView(discord.ui.View):

    def __init__(self, proposer, target):
        super().__init__(timeout=60.0)
        self.proposer, self.target = proposer, target

    @discord.ui.button(label="Đồng ý", style=discord.ButtonStyle.green)
    async def confirm(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if interaction.user != self.target:
            return await interaction.response.send_message(
                "Không phải lời cầu hôn của bạn!", ephemeral=True
            )

        marriages_col.insert_one(
            {
                "user1": self.proposer.id,
                "user2": self.target.id,
                "time": time.time(),
            }
        )

        await interaction.response.send_message(
            f"Chúc mừng! {self.proposer.mention} và {self.target.mention} đã"
            " kết hôn! 💍"
        )
        self.stop()

    @discord.ui.button(label="Từ chối", style=discord.ButtonStyle.red)
    async def cancel(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if interaction.user != self.target:
            return await interaction.response.send_message(
                "Bạn không thể từ chối thay!", ephemeral=True
            )
        await interaction.response.send_message(
            f"{self.target.mention} đã từ chối lời cầu hôn."
        )
        self.stop()


@bot.command(name="kethon")
async def kethon(ctx, member: discord.Member):
    if member == ctx.author:
        return await ctx.send("Không thể tự kết hôn!")

    if lay_ban_doi(ctx.author.id) or lay_ban_doi(member.id):
        return await ctx.send("❌ Một trong hai người đã kết hôn rồi!")

    view = MarriageView(ctx.author, member)
    await ctx.send(
        f"💍 **{ctx.author.mention}** cầu hôn **{member.mention}**. Bạn đồng ý"
        " không?",
        view=view,
    )


# ==========================================
# KHỞI CHẠY BOT
# ==========================================
if __name__ == "__main__":
    keep_alive()
    TOKEN = os.getenv("DISCORD_TOKEN")
    if TOKEN:
        bot.run(TOKEN)
    else:
        print("❌ Lỗi: Chưa cấu hình DISCORD_TOKEN trong Environment Variables!")
