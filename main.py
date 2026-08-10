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
# CẤU HÌNH ADMIN
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
    print("❌ CẢNH BÁO: Chưa cấu hình MONGO_URI trong Environment Variables!")

cluster = pymongo.MongoClient(MONGO_URI)
db = cluster["fusion_bot"]
users_col = db["users"]


def lay_user_data(user_id: int):
    user_data = users_col.find_one({"_id": user_id})
    if not user_data:
        user_data = {
            "_id": user_id,
            "vi_tien": 1000,
            "lan_diem_danh": 0,
            "da_dung_code": False,
            "lan_cuoi_lam": 0,
        }
        users_col.insert_one(user_data)
    return user_data


def cap_nhat_user_data(user_id: int, updates: dict):
    users_col.update_one({"_id": user_id}, {"$set": updates}, upsert=True)


# ==========================================
# 2. DỮ LIỆU CÂU HỎI QUIZ
# ==========================================
QUIZ_DATA = [
    {"q": "Thủ đô của Việt Nam là gì?", "a": "hanoi"},
    {"q": "Thủ đô của nước Pháp là gì?", "a": "paris"},
    {"q": "Châu lục nào lớn nhất thế giới?", "a": "chau a"},
    {"q": "Đại dương nào lớn nhất thế giới?", "a": "thai binh duong"},
    {"q": "Đỉnh núi nào cao nhất thế giới?", "a": "everest"},
    {"q": "Công thức hóa học của nước là gì?", "a": "h2o"},
    {"q": "Kim loại nào dẫn điện tốt nhất?", "a": "bac"},
    {"q": "Hành tinh nào được gọi là 'Hành tinh Đỏ'?", "a": "sao hoa"},
    {"q": "Ngày Quốc khánh Việt Nam là ngày nào?", "a": "2/9"},
    {"q": "Bức tranh nàng Mona Lisa do ai vẽ?", "a": "leonardo da vinci"},
]

# ==========================================
# CẤU HÌNH BOT DISCORD
# ==========================================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix=".", intents=intents)


@bot.event
async def on_ready():
    print(f"Bot {bot.user} đã sẵn sàng hoạt động!")


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
        description="Dưới đây là toàn bộ các lệnh bạn có thể sử dụng:",
        color=discord.Color.blue(),
    )

    embed.add_field(
        name="💰 Quản Lý & Tài Chính",
        value=(
            "• `.vi` : Xem số xu trong ví.\n"
            "• `.profile` : Xem hồ sơ cá nhân.\n"
            "• `.diemdanh` : Điểm danh nhận 500 xu/ngày.\n"
            "• `.work` : Đi làm thuê kiếm xu (chờ 1 tiếng).\n"
            "• `.chuyentien @user <xu>` : Chuyển xu cho người khác.\n"
            "• `.top` : Bảng xếp hạng đại gia."
        ),
        inline=False,
    )

    embed.add_field(
        name="🎲 Minigame Casino & Giải Trí",
        value=(
            "• `.xx <số_xu>` : Lắc Xúc Xắc Tài/Xỉu.\n"
            "• `.blackjack <cược>` : Chơi Xì Dách 21 điểm với Bot.\n"
            "• `.baucua <cửa> <cược>` : Bầu Cua (bau, cua, tom, ca, ga, nai).\n"
            "• `.slots <cược>` : Quay hũ Slot Machine.\n"
            "• `.doasom <cược>` : Đoán số từ 1-100 (5 lượt đoán).\n"
            "• `.quiz` : Chơi đố vui nhận 300 xu.\n"
            "• `.rob @user` : Cướp xu người chơi khác.\n"
            "• `.fight @user` : Đấu tay đôi ăn tiền.\n"
            "• `.lucky` : Vòng quay may mắn.\n"
            "• `.tungxu` : Tung đồng xu Sấp/Ngửa.\n"
            "• `.8ball <câu hỏi>` : Bói toán ngẫu nhiên."
        ),
        inline=False,
    )

    embed.add_field(
        name="💞 Tương Tác Xã Hội",
        value=(
            "• `.choc @user` | `.hon @user` | `.boitinhyeu @user` | `.kethon"
            " @user`"
        ),
        inline=False,
    )

    embed.set_footer(text=f"Yêu cầu bởi {ctx.author.display_name}")
    await ctx.send(embed=embed)


# ==========================================
# CÁC LỆNH TÀI CHÍNH
# ==========================================
@bot.command(name="vi")
async def vi(ctx):
    user_data = lay_user_data(ctx.author.id)
    await ctx.send(
        f"💰 {ctx.author.mention}, bạn đang có **{user_data['vi_tien']}** xu."
    )


@bot.command(name="profile")
async def profile(ctx):
    user_data = lay_user_data(ctx.author.id)
    embed = discord.Embed(
        title=f"📋 HỒ SƠ CỦA {ctx.author.display_name}",
        color=discord.Color.green(),
    )
    embed.add_field(
        name="💰 Số dư",
        value=f"**{user_data.get('vi_tien', 0)}** xu",
        inline=True,
    )
    embed.add_field(
        name="🎁 Code Fusion",
        value="Đã dùng" if user_data.get("da_dung_code") else "Chưa dùng",
        inline=True,
    )
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
# 🎲 HỆ THỐNG MINIGAME MỚI & CŨ
# ==========================================

# --- 1. SLOTS (QUAY HŨ) ---
@bot.command(name="slots")
async def slots(ctx, muc_cuoc: int = 100):
    if muc_cuoc <= 0:
        return await ctx.send("❌ Mức cược phải lớn hơn 0!")
    user_data = lay_user_data(ctx.author.id)
    if user_data["vi_tien"] < muc_cuoc:
        return await ctx.send("❌ Bạn không đủ tiền!")

    icons = ["🎰", "🍇", "🍊", "🍋", "7️⃣", "💎"]
    weights = [30, 25, 20, 15, 8, 2]  # Tỉ lệ xuất hiện
    spin = random.choices(icons, weights=weights, k=3)

    cap_nhat_user_data(
        ctx.author.id, {"vi_tien": user_data["vi_tien"] - muc_cuoc}
    )

    msg = await ctx.send(
        f"🎰 **SLOT MACHINE** 🎰\n| ❓ | ❓ | ❓ |\nĐang quay..."
    )
    await asyncio.sleep(1.5)

    thiet_hai = 0
    thiet_lap = ""
    if spin[0] == spin[1] == spin[2]:
        if spin[0] == "💎":
            he_so = 100
        elif spin[0] == "7️⃣":
            he_so = 50
        else:
            he_so = 10
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


# --- 2. BẦU CUA TÔM CÁ ---
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


# --- 3. BLACKJACK (XÌ DÁCH 21 ĐIỂM) ---
def tinh_diem_hand(hand):
    val = 0
    aces = 0
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
        self.ctx = ctx
        self.bot_hand = bot_hand
        self.player_hand = player_hand
        self.deck = deck
        self.bet = bet

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
                    f"🃏 **BLACKJACK 21**\n• Bài của bạn: {self.player_hand}"
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

        res = ""
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
                f"🃏 **KẾT QUẢ BLACKJACK**\n• Bài bạn: {self.player_hand}"
                f" (**{p_score}** điểm)\n• Bài nhà cái: {self.bot_hand}"
                f" (**{b_score}** điểm)\n\n{res}"
            ),
            view=self,
        )


@bot.command(name="blackjack")
async def blackjack(ctx, muc_cuoc: int = 100):
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
    if p_score == 21:
        win_amount = int(muc_cuoc * 2.5)
        cap_nhat_user_data(
            ctx.author.id,
            {"vi_tien": lay_user_data(ctx.author.id)["vi_tien"] + win_amount},
        )
        return await ctx.send(
            f"🔥 **BLACKJACK TRỰC TIẾP!** {player_hand} - Bạn thắng"
            f" **+{int(muc_cuoc*1.5)} xu**!"
        )

    view = BlackjackView(ctx, bot_hand, player_hand, deck, muc_cuoc)
    await ctx.send(
        f"🃏 **BLACKJACK 21** (Tiền cược: {muc_cuoc} xu)\n• Bài của bạn:"
        f" {player_hand} (Tổng: **{p_score}**)\n• Bài nhà cái:"
        f" ['{bot_hand[0]}', '❓']",
        view=view,
    )


# --- 4. ĐOÁN SỐ 1 - 100 ---
@bot.command(name="doasom")
async def doasom(ctx, muc_cuoc: int = 100):
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


# --- CÁC MINIGAME CŨ (.xx, .quiz, .rob, .fight, .lucky, .tungxu, .8ball) ---
class XucXacView(View):

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

        cap_nhat_user_data(user_id, {"vi_tien": user_data["vi_tien"] - self.muc_cuoc})
        self.danh_sach_cuoc[lua_chon][user_id] = self.muc_cuoc
        await interaction.response.send_message(
            f"✅ {interaction.user.mention} cược **{self.muc_cuoc} xu** cửa"
            f" **{lua_chon.upper()}**!"
        )


@bot.command(name="xx")
async def xx(ctx, muc_cuoc: int = 100):
    view = XucXacView(muc_cuoc=muc_cuoc)
    thoi_gian_cho = 15
    msg = await ctx.send(
        f"🎲 **TÀI XỈU NHIỀU NGƯỜI** | Mức cược: **{muc_cuoc} xu**\n⏳ Thời gian"
        f" cược: **{thoi_gian_cho} giây**",
        view=view,
    )

    await asyncio.sleep(thoi_gian_cho)
    view.da_ket_thuc = True
    for item in view.children:
        item.disabled = True
    await msg.edit(content="🎲 **HẾT GIỜ CƯỢC! ĐANG LẮC...**", view=view)

    await asyncio.sleep(2)
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


@bot.command(name="quiz")
async def quiz(ctx):
    question_data = random.choice(QUIZ_DATA)
    await ctx.send(
        f"❓ **ĐỐ VUI:** {question_data['q']}\n*(15 giây để trả lời, không"
        " dấu!)*"
    )

    def check(m):
        return m.channel == ctx.channel and not m.author.bot

    try:
        msg = await bot.wait_for("message", check=check, timeout=15.0)
        if msg.content.lower() == question_data["a"]:
            user_data = lay_user_data(msg.author.id)
            cap_nhat_user_data(
                msg.author.id, {"vi_tien": user_data["vi_tien"] + 300}
            )
            await ctx.send(
                f"✅ Chính xác! {msg.author.mention} nhận **+300 xu**."
            )
        else:
            await ctx.send(
                f"❌ Sai rồi! Đáp án là: `{question_data['a'].upper()}`"
            )
    except asyncio.TimeoutError:
        await ctx.send(f"⏰ Hết giờ! Đáp án là: `{question_data['a'].upper()}`")


@bot.command(name="rob")
async def rob(ctx, member: discord.Member):
    if member == ctx.author:
        return await ctx.send("❌ Tự cướp chính mình à?")
    user_data = lay_user_data(ctx.author.id)
    target_data = lay_user_data(member.id)

    if target_data["vi_tien"] < 500:
        return await ctx.send("❌ Người này quá nghèo!")

    if random.random() < 0.4:
        so_tien_cuop = int(target_data["vi_tien"] * 0.2)
        cap_nhat_user_data(
            ctx.author.id, {"vi_tien": user_data["vi_tien"] + so_tien_cuop}
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
            ctx.author.id, {"vi_tien": max(0, user_data["vi_tien"] - 200)}
        )
        await ctx.send(
            f"👮 {ctx.author.mention} bị cảnh sát bắt và phạt **200 xu**!"
        )


@bot.command(name="fight")
async def fight(ctx, member: discord.Member):
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


@bot.command(name="lucky")
async def lucky(ctx):
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


@bot.command(name="tungxu")
async def tungxu(ctx):
    await ctx.send(
        f"🪙 {ctx.author.mention} tung đồng xu: **{random.choice(['SẤP', 'NGỬA'])}**!"
    )


@bot.command(name="8ball")
async def eightball(ctx, *, cau_hoi):
    responses = [
        "Chắc chắn rồi! ✨",
        "Không thể nào đâu. ❌",
        "Hỏi lại sau nhé! 😴",
        "Có vẻ như là có. 👍",
    ]
    await ctx.send(
        f"🎱 **Câu hỏi:** {cau_hoi}\n🔮 **Phán:** {random.choice(responses)}"
    )


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
