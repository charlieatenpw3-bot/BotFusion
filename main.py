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
# 0. KHỞI TẠO WEB SERVER (GIỮ BOT ONLINE 24/7)
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
# 1. KẾT NỐI MONGODB (THAY THẾ DATA.JSON)
# ==========================================
MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
  print("❌ CẢNH BÁO: Chưa cấu hình MONGO_URI trong Environment Variables!")

cluster = pymongo.MongoClient(MONGO_URI)
db = cluster["fusion_bot"]  # Tên Database
users_col = db["users"]  # Collection lưu dữ liệu người dùng


def lay_user_data(user_id: int):
  """Lấy dữ liệu 1 user, nếu chưa có thì tạo mới."""
  user_data = users_col.find_one({"_id": user_id})
  if not user_data:
    user_data = {
        "_id": user_id,
        "vi_tien": 1000,
        "lan_diem_danh": 0,
        "da_dung_code": False,
    }
    users_col.insert_one(user_data)
  return user_data


def cap_nhat_user_data(user_id: int, updates: dict):
  """Cập nhật dữ liệu cho 1 user."""
  users_col.update_one({"_id": user_id}, {"$set": updates}, upsert=True)


# ==========================================
# CẤU HÌNH BOT DISCORD
# ==========================================
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix=".", intents=intents)


# 2. LỆNH XEM DANH SÁCH CHỨC NĂNG (.fusion)
@bot.command(name="fusion")
async def fusion(ctx):
  embed = discord.Embed(
      title="🤖 DANH SÁCH CHỨC NĂNG BOT FUSION",
      description="Dưới đây là toàn bộ các lệnh bạn có thể sử dụng:",
      color=discord.Color.blue(),
  )

  embed.add_field(
      name="💰 Quản Lý Tài Khoản",
      value=(
          "• `.vi` : Xem số xu hiện có trong ví.\n• `.diemdanh` : Nhận 500 xu"
          " miễn phí mỗi 24 giờ."
      ),
      inline=False,
  )

  embed.add_field(
      name="🎲 Minigame Giải Trí",
      value=(
          "• `.xx` : Bắt đầu phiên lắc Xúc Xắc (Mặc định 100 xu).\n• `.xx"
          " <số_xu>` : Bắt đầu phiên lắc Xúc Xắc với mức cược tùy chỉnh."
      ),
      inline=False,
  )

  embed.add_field(
      name="🎁 Mã Quà Tặng (Giftcode)",
      value=(
          "• `.FUSIONONETOP` : Nhận ngay +1000 xu (Dùng 1 lần duy nhất)."
      ),
      inline=False,
  )

  embed.set_footer(
      text=f"Yêu cầu bởi {ctx.author.display_name}",
      icon_url=ctx.author.display_avatar.url,
  )

  await ctx.send(embed=embed)


# 3. LỆNH NHẬP MÃ QUÀ TẶNG (.FUSIONONETOP)
@bot.command(name="FUSIONONETOP")
async def fusiononetop(ctx):
  user_id = ctx.author.id
  tien_thuong = 1000
  user_data = lay_user_data(user_id)

  if user_data.get("da_dung_code", False):
    await ctx.send(
        f"❌ {ctx.author.mention}, bạn đã sử dụng mã quà tặng **FUSIONONETOP**"
        " trước đó rồi!"
    )
    return

  tong_tien = user_data["vi_tien"] + tien_thuong
  cap_nhat_user_data(
      user_id, {"vi_tien": tong_tien, "da_dung_code": True}
  )

  await ctx.send(
      f"🎁 **MÃ QUÀ TẶNG HỢP LỆ!**\n"
      f"🎉 Chúc mừng {ctx.author.mention} nhận được **+{tien_thuong} xu** từ mã"
      " **FUSIONONETOP**!\n"
      f"💰 Số xu hiện tại: **{tong_tien}** xu."
  )


# 4. LỆNH ĐIỂM DANH HÀNG NGÀY (.diemdanh)
@bot.command(name="diemdanh")
async def diemdanh(ctx):
  user_id = ctx.author.id
  thoi_gian_hien_tai = time.time()
  thoi_gian_cho = 86400
  tien_thuong = 500

  user_data = lay_user_data(user_id)
  lan_cuoi = user_data.get("lan_diem_danh", 0)

  if thoi_gian_hien_tai - lan_cuoi < thoi_gian_cho:
    thoi_gian_con_lai = int(thoi_gian_cho - (thoi_gian_hien_tai - lan_cuoi))
    gio = thoi_gian_con_lai // 3600
    phut = (thoi_gian_con_lai % 3600) // 60
    giay = thoi_gian_con_lai % 60

    await ctx.send(
        f"⏳ {ctx.author.mention}, bạn đã điểm danh hôm nay rồi!\nVui lòng"
        f" quay lại sau **{gio} giờ {phut} phút {giay} giây**."
    )
    return

  tong_tien = user_data["vi_tien"] + tien_thuong
  cap_nhat_user_data(
      user_id, {"vi_tien": tong_tien, "lan_diem_danh": thoi_gian_hien_tai}
  )

  await ctx.send(
      f"🎉 {ctx.author.mention} đã điểm danh thành công!\n🎁 Bạn nhận được"
      f" **+{tien_thuong} xu** (Tổng hiện có: **{tong_tien}** xu)."
  )


# 5. GIAO DIỆN NÚT BẤM CƯỢC XÚC XẮC (VIEW)
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
      await interaction.response.send_message(
          "❌ Phiên cược đã kết thúc!", ephemeral=True
      )
      return

    user_id = interaction.user.id
    user_data = lay_user_data(user_id)
    tien_hien_co = user_data["vi_tien"]

    if tien_hien_co < self.muc_cuoc:
      await interaction.response.send_message(
          f"❌ Bạn không đủ tiền! Cần tối thiểu {self.muc_cuoc} xu.",
          ephemeral=True,
      )
      return

    phe_con_lai = "xiu" if lua_chon == "tai" else "tai"
    if user_id in self.danh_sach_cuoc[phe_con_lai]:
      await interaction.response.send_message(
          "❌ Bạn đã cược bên kia rồi, không thể cược cả 2 cửa!",
          ephemeral=True,
      )
      return

    if user_id in self.danh_sach_cuoc[lua_chon]:
      await interaction.response.send_message(
          "❌ Bạn đã đặt cược trong phiên này rồi!", ephemeral=True
      )
      return

    # Trừ tiền cược
    cap_nhat_user_data(user_id, {"vi_tien": tien_hien_co - self.muc_cuoc})
    self.danh_sach_cuoc[lua_chon][user_id] = self.muc_cuoc

    await interaction.response.send_message(
        f"✅ {interaction.user.mention} đã cược **{self.muc_cuoc} xu** vào cửa"
        f" **{lua_chon.upper()}**!",
        ephemeral=False,
    )


@bot.event
async def on_ready():
  print(f"Bot {bot.user} ready!")


# 6. LỆNH .xx BẮT ĐẦU PHIÊN XÚC XẮC
@bot.command(name="xx")
async def xx(ctx, muc_cuoc: int = 100):
  view = XucXacView(muc_cuoc=muc_cuoc)
  thoi_gian_cho = 20

  msg = await ctx.send(
      f"🎲 **PHIÊN LẮC XÚC XẮC NHIỀU NGƯỜI BẮT ĐẦU!**\n💵 Mức cược: **{muc_cuoc}"
      f" xu**\n⏳ Thời gian cược còn lại: **{thoi_gian_cho} giây**\n👇 Chọn"
      " cửa cược của bạn phía dưới:",
      view=view,
  )

  while thoi_gian_cho > 0:
    await asyncio.sleep(5)
    thoi_gian_cho -= 5
    if thoi_gian_cho > 0:
      await msg.edit(
          content=(
              "🎲 **PHIÊN LẮC XÚC XẮC NHIỀU NGƯỜI BẮT ĐẦU!**\n💵 Mức cược:"
              f" **{muc_cuoc} xu**\n⏳ Thời gian cược còn lại:"
              f" **{thoi_gian_cho} giây**\n👇 Chọn cửa cược của bạn phía"
              " dưới:"
          )
      )

  view.da_ket_thuc = True
  for item in view.children:
    item.disabled = True
  await msg.edit(
      content="🎲 **ĐÃ HẾT GIỜ CƯỢC! ĐANG LẮC XÚC XẮC...**", view=view
  )

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
      f"🎰 **KẾT QUẢ XÚC XẮC:** `[{x1}] - [{x2}] - [{x3}]`\n💥 **TỔNG ĐIỂM:**"
      f" `{tong}` ➔ **{ten_ket_qua}**\n\n"
  )

  nguoi_thang = view.danh_sach_cuoc.get(ket_qua, {})

  if nguoi_thang:
    thong_bao += "🎉 **DANH SÁCH THẮNG CƯỢC (+100% XU):**\n"
    for uid, cuoc in nguoi_thang.items():
      u_data = lay_user_data(uid)
      tien_thuong = cuoc * 2
      tong_moi = u_data["vi_tien"] + tien_thuong

      cap_nhat_user_data(uid, {"vi_tien": tong_moi})
      thong_bao += f"• <@{uid}>: +{tien_thuong} xu (Hiện có: {tong_moi})\n"
  else:
    thong_bao += "😭 Phiên này không có ai thắng cược!\n"

  await ctx.send(thong_bao)


# 7. LỆNH XEM XU (.vi)
@bot.command(name="vi")
async def vi(ctx):
  user_data = lay_user_data(ctx.author.id)
  await ctx.send(
      f"💰 {ctx.author.mention}, bạn đang có **{user_data['vi_tien']}** xu."
  )


# ==========================================
# KHỞI CHẠY BOT VÀ SERVER
# ==========================================
if __name__ == "__main__":
  keep_alive()
  TOKEN = os.getenv("DISCORD_TOKEN")
  if TOKEN:
    bot.run(TOKEN)
  else:
    print("❌ Lỗi: Không tìm thấy DISCORD_TOKEN trong Environment Variables!")
