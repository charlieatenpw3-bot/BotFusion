import os
import json
import time
import random
import asyncio
import discord
from discord.ext import commands
from discord.ui import Button, View

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix=".", intents=intents)

FILE_DATA = "data.json"
vi_tien = {}
lan_diem_danh = {}
da_dung_code = {}

# 1. QUẢN LÝ DỮ LIỆU
def doc_data():
    global vi_tien, lan_diem_danh, da_dung_code
    if os.path.exists(FILE_DATA):
        try:
            with open(FILE_DATA, "r", encoding="utf-8") as f:
                data_raw = json.load(f)
                
                vi_tien = {int(k): v for k, v in data_raw.get("vi_tien", {}).items()}
                lan_diem_danh = {int(k): v for k, v in data_raw.get("lan_diem_danh", {}).items()}
                da_dung_code = {int(k): v for k, v in data_raw.get("da_dung_code", {}).items()}
        except Exception as e:
            vi_tien = {}
            lan_diem_danh = {}
            da_dung_code = {}
    else:
        vi_tien = {}
        lan_diem_danh = {}
        da_dung_code = {}

def luu_data():
    try:
        data_to_save = {
            "vi_tien": vi_tien,
            "lan_diem_danh": lan_diem_danh,
            "da_dung_code": da_dung_code
        }
        with open(FILE_DATA, "w", encoding="utf-8") as f:
            json.dump(data_to_save, f, indent=4)
    except Exception as e:
        print(f"Lỗi lưu file: {e}")

def lay_tien(user_id):
    if user_id not in vi_tien:
        vi_tien[user_id] = 1000
        luu_data()
    return vi_tien[user_id]


# 2. LỆNH XEM DANH SÁCH CHỨC NĂNG (.fusion)
@bot.command(name="fusion")
async def fusion(ctx):
    embed = discord.Embed(
        title="🤖 DANH SÁCH CHỨC NĂNG BOT FUSION",
        description="Dưới đây là toàn bộ các lệnh bạn có thể sử dụng:",
        color=discord.Color.blue()
    )
    
    embed.add_field(
        name="💰 Quản Lý Tài Khoản", 
        value="• `.vi` : Xem số xu hiện có trong ví.\n• `.diemdanh` : Nhận 500 xu miễn phí mỗi 24 giờ.", 
        inline=False
    )
    
    embed.add_field(
        name="🎲 Minigame Giải Trí", 
        value="• `.xx` : Bắt đầu phiên lắc Xúc Xắc (Mặc định 100 xu).\n• `.xx <số_xu>` : Bắt đầu phiên lắc Xúc Xắc với mức cược tùy chỉnh.", 
        inline=False
    )
    
    embed.add_field(
        name="🎁 Mã Quà Tặng (Giftcode)", 
        value="• `.FUSIONONETOP` : Nhận ngay +1000 xu (Dùng 1 lần duy nhất).", 
        inline=False
    )
    
    embed.set_footer(text=f"Yêu cầu bởi {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
    
    await ctx.send(embed=embed)


# 3. LỆNH NHẬP MÃ QUÀ TẶNG (.FUSIONONETOP)
@bot.command(name="FUSIONONETOP")
async def fusiononetop(ctx):
    user_id = ctx.author.id
    tien_thuong = 1000

    if da_dung_code.get(user_id, False):
        await ctx.send(f"❌ {ctx.author.mention}, bạn đã sử dụng mã quà tặng **FUSIONONETOP** trước đó rồi!")
        return

    lay_tien(user_id)
    vi_tien[user_id] += tien_thuong
    da_dung_code[user_id] = True
    luu_data()

    await ctx.send(
        f"🎁 **MÃ QUÀ TẶNG HỢP LỆ!**\n"
        f"🎉 Chúc mừng {ctx.author.mention} nhận được **+{tien_thuong} xu** từ mã **FUSIONONETOP**!\n"
        f"💰 Số xu hiện tại: **{vi_tien[user_id]}** xu."
    )


# 4. LỆNH ĐIỂM DANH HÀNG NGÀY (.diemdanh)
@bot.command(name="diemdanh")
async def diemdanh(ctx):
    user_id = ctx.author.id
    thoi_gian_hien_tai = time.time()
    thoi_gian_cho = 86400
    tien_thuong = 500

    lan_cuoi = lan_diem_danh.get(user_id, 0)

    if thoi_gian_hien_tai - lan_cuoi < thoi_gian_cho:
        thoi_gian_con_lai = int(thoi_gian_cho - (thoi_gian_hien_tai - lan_cuoi))
        gio = thoi_gian_con_lai // 3600
        phut = (thoi_gian_con_lai % 3600) // 60
        giay = thoi_gian_con_lai % 60
        
        await ctx.send(
            f"⏳ {ctx.author.mention}, bạn đã điểm danh hôm nay rồi!\n"
            f"Vui lòng quay lại sau **{gio} giờ {phut} phút {giay} giây**."
        )
        return

    lay_tien(user_id)
    vi_tien[user_id] += tien_thuong
    lan_diem_danh[user_id] = thoi_gian_hien_tai
    luu_data()

    await ctx.send(
        f"🎉 {ctx.author.mention} đã điểm danh thành công!\n"
        f"🎁 Bạn nhận được **+{tien_thuong} xu** (Tổng hiện có: **{vi_tien[user_id]}** xu)."
    )


# 5. GIAO DIỆN NÚT BẤM CƯỢC XÚC XẮC (VIEW)
class XucXacView(View):
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
            await interaction.response.send_message("❌ Phiên cược đã kết thúc!", ephemeral=True)
            return

        user_id = interaction.user.id
        tien_hien_co = lay_tien(user_id)

        if tien_hien_co < self.muc_cuoc:
            await interaction.response.send_message(f"❌ Bạn không đủ tiền! Cần tối thiểu {self.muc_cuoc} xu.", ephemeral=True)
            return

        phe_con_lai = "xiu" if lua_chon == "tai" else "tai"
        if user_id in self.danh_sach_cuoc[phe_con_lai]:
            await interaction.response.send_message("❌ Bạn đã cược bên kia rồi, không thể cược cả 2 cửa!", ephemeral=True)
            return

        if user_id in self.danh_sach_cuoc[lua_chon]:
            await interaction.response.send_message("❌ Bạn đã đặt cược trong phiên này rồi!", ephemeral=True)
            return

        vi_tien[user_id] -= self.muc_cuoc
        luu_data()
        self.danh_sach_cuoc[lua_chon][user_id] = self.muc_cuoc

        await interaction.response.send_message(
            f"✅ {interaction.user.mention} đã cược **{self.muc_cuoc} xu** vào cửa **{lua_chon.upper()}**!",
            ephemeral=False
        )


@bot.event
async def on_ready():
    doc_data()
    print(f"Bot {bot.user} ready!")


# 6. LỆNH .xx BẮT ĐẦU PHIÊN XÚC XẮC
@bot.command(name="xx")
async def xx(ctx, muc_cuoc: int = 100):
    view = XucXacView(muc_cuoc=muc_cuoc)
    thoi_gian_cho = 20

    msg = await ctx.send(
        f"🎲 **PHIÊN LẮC XÚC XẮC NHIỀU NGƯỜI BẮT ĐẦU!**\n"
        f"💵 Mức cược: **{muc_cuoc} xu**\n"
        f"⏳ Thời gian cược còn lại: **{thoi_gian_cho} giây**\n"
        f"👇 Chọn cửa cược của bạn phía dưới:",
        view=view
    )

    while thoi_gian_cho > 0:
        await asyncio.sleep(5)
        thoi_gian_cho -= 5
        if thoi_gian_cho > 0:
            await msg.edit(content=
                f"🎲 **PHIÊN LẮC XÚC XẮC NHIỀU NGƯỜI BẮT ĐẦU!**\n"
                f"💵 Mức cược: **{muc_cuoc} xu**\n"
                f"⏳ Thời gian cược còn lại: **{thoi_gian_cho} giây**\n"
                f"👇 Chọn cửa cược của bạn phía dưới:"
            )

    view.da_ket_thuc = True
    for item in view.children:
        item.disabled = True
    await msg.edit(content="🎲 **ĐÃ HẾT GIỜ CƯỢC! ĐANG LẮC XÚC XẮC...**", view=view)

    await asyncio.sleep(2)

    x1 = random.randint(1, 6)
    x2 = random.randint(1, 6)
    x3 = random.randint(1, 6)
    tong = x1 + x2 + x3

    if x1 == x2 == x3:
        ket_qua = "bao"
        ten_ket_qua = f"BÃO {x1} (Nhà cái ăn hết!)"
    elif tong >= 11:
        ket_qua = "tai"
        ten_ket_qua = "TÀI"
    else:
        ket_qua = "xiu"
        ten_ket_qua = "XỈU"

    thong_bao = (
        f"🎰 **KẾT QUẢ XÚC XẮC:** `[{x1}] - [{x2}] - [{x3}]`\n"
        f"💥 **TỔNG ĐIỂM:** `{tong}` ➔ **{ten_ket_qua}**\n\n"
    )

    nguoi_thang = view.danh_sach_cuoc.get(ket_qua, {})
    
    if nguoi_thang:
        thong_bao += "🎉 **DANH SÁCH THẮNG CƯỢC (+100% XU):**\n"
        for uid, cuoc in nguoi_thang.items():
            tien_thuong = cuoc * 2
            vi_tien[uid] += tien_thuong
            thong_bao += f"• <@{uid}>: +{tien_thuong} xu (Hiện có: {vi_tien[uid]})\n"
    else:
        thong_bao += "😭 Phiên này không có ai thắng cược!\n"

    luu_data()
    await ctx.send(thong_bao)


# 7. LỆNH XEM XU (.vi)
@bot.command(name="vi")
async def vi(ctx):
    so_tien = lay_tien(ctx.author.id)
    await ctx.send(f"💰 {ctx.author.mention}, bạn đang có **{so_tien}** xu.")


TOKEN = os.getenv("DISCORD_TOKEN")
if TOKEN:
    bot.run(TOKEN)
