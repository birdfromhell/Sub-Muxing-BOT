import asyncio
import os
import shutil
import string
import time
import shutil, psutil
import pyrogram
from PIL import Image
from pyrogram import Client, filters
from pyrogram.errors.exceptions.flood_420 import FloodWait
from pyrogram.types import (CallbackQuery, InlineKeyboardButton,InlineKeyboardMarkup, Message)
from pyromod import listen

from config import Config
from helpers import database
from __init__ import LOGGER, gDict, UPLOAD_AS_DOC, UPLOAD_TO_DRIVE, queueDB, formatDB, replyDB
from helpers.utils import get_readable_time, get_readable_file_size
from helpers.rclone_upload import rclone_driver, rclone_upload
import plugins.cb_handler

botStartTime = time.time()

mergeApp = Client(
	session_name="merge-bot",
	api_hash=Config.API_HASH,
	api_id=Config.API_ID,
	bot_token=Config.BOT_TOKEN,
	workers=300,
	app_version="3.0+yash-multiSubsSupport"
)


if os.path.exists('./downloads') == False:
	os.makedirs('./downloads')




@mergeApp.on_message( filters.command(['login']) & filters.private & ~filters.edited )
async def allowUser(c:Client, m: Message):
	if await database.allowedUser(uid=m.from_user.id) is True:
		await m.reply_text(
			text=f"**Login Berhasil ✅,**\n  ⚡ Sekarang Kamu Bisa Mengunnakan Saya!!",
			quote=True
		)
	else:
		passwd = m.text.split(' ',1)[1]
		if passwd == Config.PASSWORD:
			await database.allowUser(uid=m.from_user.id)
			await m.reply_text(
				text=f"**Login Berhasil ✅,**\n  ⚡ Sekarang Kamu Bisa Menggunakan Saya!!",
				quote=True
			)
		else:
			await m.reply_text(
				text=f"**Login Gagal ❌,**\n  🛡️ Kamu Tidak Bisa Mengunakan saya \n\nContact: 🈲 @{Config.OWNER_USERNAME}",
				quote=True
			)
	return

@mergeApp.on_message(filters.command(['stats']) & filters.private & filters.user(Config.OWNER))
async def stats_handler(c:Client, m:Message):
    currentTime = get_readable_time(time.time() - botStartTime)
    total, used, free = shutil.disk_usage('.')
    total = get_readable_file_size(total)
    used = get_readable_file_size(used)
    free = get_readable_file_size(free)
    sent = get_readable_file_size(psutil.net_io_counters().bytes_sent)
    recv = get_readable_file_size(psutil.net_io_counters().bytes_recv)
    cpuUsage = psutil.cpu_percent(interval=0.5)
    memory = psutil.virtual_memory().percent
    disk = psutil.disk_usage('/').percent
    stats = f'<b>「 💠 BOT STATISTICS 」</b>\n' \
            f'<b></b>\n' \
            f'<b>⏳ Bot Uptime : {currentTime}</b>\n' \
            f'<b>💾 Total Disk Space : {total}</b>\n' \
            f'<b>📀 Total Used Space : {used}</b>\n' \
            f'<b>💿 Total Free Space : {free}</b>\n' \
            f'<b>🔺 Total Upload : {sent}</b>\n' \
            f'<b>🔻 Total Download : {recv}</b>\n' \
            f'<b>🖥 CPU : {cpuUsage}%</b>\n' \
            f'<b>⚙️ RAM : {memory}%</b>\n' \
            f'<b>💿 DISK : {disk}%</b>'
    await m.reply_text(stats,quote=True)

@mergeApp.on_message(filters.command(['broadcast']) & filters.private & filters.user(Config.OWNER))
async def broadcast_handler(c:Client, m:Message):
	msg = m.reply_to_message
	userList = await database.broadcast()
	len = userList.collection.count_documents({})
	for i in range(len):
		try:
			await msg.copy(chat_id=userList[i]['_id'])
		except FloodWait as e:
			await asyncio.sleep(e.x)
			await msg.copy(chat_id=userList[i]['_id'])
		except Exception:
			await database.deleteUser(userList[i]['_id'])
			pass
		print(f"Message sent to {userList[i]['name']} ")
		await asyncio.sleep(2)
	await m.reply_text(
		text="🤓 __Broadcast Berhasil__",
		quote=True
	)

@mergeApp.on_message(filters.command(['start']) & filters.private & ~filters.edited)
async def start_handler(c: Client, m: Message):
	await database.addUser(uid=m.from_user.id,fname=m.from_user.first_name, lname=m.from_user.last_name)
	if await database.allowedUser(uid=m.from_user.id) is False:
		res = await m.reply_text(
			text=f"Hi **{m.from_user.first_name}**\n\n 🛡️ Kamu Tidak Bisa Mengunakan Saya\n\n**Contact: 🈲 @{Config.OWNER_USERNAME}** ",
			quote=True
		)
		return
	res = await m.reply_text(
		text=f"Hi **{m.from_user.first_name}**\n\n ⚡ Saya Adalah Bot untuk Merger Video/File \n\n😎 Saya Bisa Mengabungkan File/Video Dan Mengabungkan Subtitle ke Video(softmux)!, Dan Mengupload ny ke telgram Atau Google Drive\n\n**Owner: 🈲 @{Config.OWNER_USERNAME}** ",
		quote=True
	)


@mergeApp.on_message((filters.document | filters.video) & filters.private & ~filters.edited)
async def video_handler(c: Client, m: Message):
	if await database.allowedUser(uid=m.from_user.id) is False:
		res = await m.reply_text(
			text=f"Hi **{m.from_user.first_name}**\n\n 🛡️ Kamu Tidak Bisa Mengunakan Saya\n\n**Contact: 🈲 @{Config.OWNER_USERNAME}** ",
			quote=True
		)
		return
	input_ = f"downloads/{str(m.from_user.id)}/input.txt"
	if os.path.exists(input_):
		await m.reply_text("Maaf 🙏,\nSatu Proses Sedang Di Kerjakan!\n🤬JANGAN SPAM.")
		return
	media = m.video or m.document
	currentFileNameExt = media.file_name.rsplit(sep='.')[-1].lower()
	if media.file_name is None:
		await m.reply_text('File Tidak Ditemukan 🤔')
		return
	if media.file_name.rsplit(sep='.')[-1].lower() in 'conf':
		await m.reply_text(
			text="**💾 Rclone Config file Terdeteksi, Apakah kamu Mau Menyimpan Ini?**",
			reply_markup = InlineKeyboardMarkup(
				[
					[
						InlineKeyboardButton("✅ Yes", callback_data=f"rclone_save"),
						InlineKeyboardButton("❌ No", callback_data='rclone_discard')
					]
				]
			),
			quote=True
		)
		return

	if currentFileNameExt == 'srt':
		queueDB.get(m.from_user.id)['videos'].append(m.message_id)
		queueDB.get(m.from_user.id)['subtitles'].append(None)

		button = await MakeButtons(c,m,queueDB)
		button.remove([InlineKeyboardButton("🔗 Merge Sekarang", callback_data="merge")])
		button.remove([InlineKeyboardButton("💥 Clear Files", callback_data="cancel")])

		button.append([InlineKeyboardButton("🔗 Merge Subtitles", callback_data="mergeSubtitles")])
		button.append([InlineKeyboardButton("💥 Hapus Files", callback_data="cancel")])
		await m.reply_text(
			text="Kamu Mengirim File subtitle. Apakah Kamu Mau Mengabungkan Ini?",
			quote=True,
			reply_markup= InlineKeyboardMarkup(button)
		)
		formatDB.update({m.from_user.id: currentFileNameExt})
		return

	if queueDB.get(m.from_user.id, None) is None:
		formatDB.update({m.from_user.id: currentFileNameExt})
	if (formatDB.get(m.from_user.id, None) is not None) and (currentFileNameExt != formatDB.get(m.from_user.id)):
		await m.reply_text(f"First you sent a {formatDB.get(m.from_user.id).upper()} file so now send only that type of file.", quote=True)
		return
	if currentFileNameExt not in ['mkv','mp4','webm']:
		await m.reply_text("Format Video  Ini Tidak Dibolehkan!\nHanya Boleh MP4 atau MKV atau WEBM.", quote=True)
		return
	editable = await m.reply_text("Harap Tunggu...", quote=True)
	MessageText = "Okay,\nSekarang Kirim Video/Subtitle Selanjutnya atau Tekan Tombol **Merge Now**!"
	if queueDB.get(m.from_user.id, None) is None:
		queueDB.update({m.from_user.id: {'videos':[],'subtitles':[]}})
	if (len(queueDB.get(m.from_user.id)['videos']) >= 0) and (len(queueDB.get(m.from_user.id)['videos'])<10 ):
		queueDB.get(m.from_user.id)['videos'].append(m.message_id)
		queueDB.get(m.from_user.id)['subtitles'].append(None)
		print(queueDB.get(m.from_user.id)['videos'], queueDB.get(m.from_user.id)['subtitles'])
		if len(queueDB.get(m.from_user.id)['videos']) == 1:
			await editable.edit(
				'**Kirim Beberapa File Untuk Digabungkan Menjadi Satu**',parse_mode='markdown'
			)
			return
		if queueDB.get(m.from_user.id, None)['videos'] is None:
			formatDB.update({m.from_user.id: media.file_name.split(sep='.')[-1].lower()})
		if replyDB.get(m.from_user.id, None) is not None:
			await c.delete_messages(chat_id=m.chat.id, message_ids=replyDB.get(m.from_user.id))
		if len(queueDB.get(m.from_user.id)['videos']) == 10:
			MessageText = "Okay, Sekarang Tekan Tombol **Merge Now** !!"
		markup = await MakeButtons(c, m, queueDB)
		reply_ = await editable.edit(
			text=MessageText,
			reply_markup=InlineKeyboardMarkup(markup)
		)
		replyDB.update({m.from_user.id: reply_.message_id})
	elif len(queueDB.get(m.from_user.id)['videos']) > 10:
		markup = await MakeButtons(c,m,queueDB)
		await editable.text(
			"Hanya 10 Video di Perbolehkan",
			reply_markup=InlineKeyboardMarkup(markup)
		)

@mergeApp.on_message(filters.photo & filters.private & ~filters.edited)
async def photo_handler(c: Client,m: Message):
	if await database.allowedUser(uid=m.from_user.id) is False:
		res = await m.reply_text(
			text=f"Hi **{m.from_user.first_name}**\n\n 🛡️ Kamu Tidak Bisa Mengunakan Saya\n\n**Contact: 🈲 @{Config.OWNER_USERNAME}** ",
			quote=True
		)
		return
	thumbnail = m.photo.file_id
	msg = await m.reply_text('Menyimpan Thumbnail. . . .',quote=True)
	await database.saveThumb(m.from_user.id,thumbnail)
	LOCATION = f'./downloads/{m.from_user.id}_thumb.jpg'
	await c.download_media(
		message=m,
		file_name=LOCATION
	)
	await msg.edit_text(
		text="✅ Custom Thumbnail Disimpan!"
	)

@mergeApp.on_message(filters.command(['help']) & filters.private & ~filters.edited)
async def help_msg(c: Client, m: Message):
	await m.reply_text(
		text='''**Ikuti Langkah Ini:

1) Kirim Saya Foto Untuk menjadi Thumbnail (optional).
2) Kirim 2 atau Lebih Video/Subtitle
3) Setelah Mengirim Semua Silahkan Pilih opsi Merge
4) Pilih Upload Mode.
5) Pilih Rename Jika Kamu Ingin Mengganti Nama File atau Pilih tidak Untuk Default**''',
		quote=True,
		reply_markup=InlineKeyboardMarkup(
			[
				[
					InlineKeyboardButton("Tutup 🔐", callback_data="close")
				]
			]
		)
	)

@mergeApp.on_message( filters.command(['about']) & filters.private & ~filters.edited )
async def about_handler(c:Client,m:Message):
	await m.reply_text(
		text='''
- **Whats New:**
+ Kamu Bisa Upload Ke Gdrive Mengunakan Rclone Config
- **FEATURES:**
+ merger 1 Sampai 10 Video Menjadi Satu
+ Merger Subtitle Dengan Video (SoftSub)
+ Upload Sebagai document/video
+ Custom thumbnail Di Dukung
		''',
		quote=True,
		reply_markup=InlineKeyboardMarkup(
			[
				[
					InlineKeyboardButton("Developer", url="https://t.me/BIRD_from_HELL")
				],
				[
					InlineKeyboardButton("Source Code", url="https://soon"),
					InlineKeyboardButton("more bots", url=f"https://t.me/mustaxproject")
				]
			]
		)
	)

@mergeApp.on_message(filters.command(['showthumbnail']) & filters.private & ~filters.edited)
async def show_thumbnail(c:Client ,m: Message):
	try:
		thumb_id = await database.getThumb(m.from_user.id)
		LOCATION = f'./downloads/{m.from_user.id}_thumb.jpg'
		await c.download_media(message=str(thumb_id),file_name=LOCATION)
		if os.path.exists(LOCATION) is False:
			await m.reply_text(text='❌ Custom thumbnail Tidak Di Temukan',quote=True)
		else:
			await m.reply_photo(photo=LOCATION, caption='🖼️ Your custom thumbnail', quote=True)
	except Exception as err:
		await m.reply_text(text='❌ Custom thumbnail Tidak Ditemukan',quote=True)


@mergeApp.on_message(filters.command(['deletethumbnail']) & filters.private & ~filters.edited)
async def delete_thumbnail(c: Client,m: Message):
	try:
		await database.delThumb(m.from_user.id)
		if os.path.exists(f"downloads/{str(m.from_user.id)}"):
			os.remove(f"downloads/{str(m.from_user.id)}")
		await m.reply_text('✅ Thumbnail Berhasil Dihapus',quote=True)
	except Exception as err:
		await m.reply_text(text='❌ Custom thumbnail Tidak Di Temukan',quote=True)


@mergeApp.on_callback_query()
async def callback(c: Client, cb: CallbackQuery):
	await plugins.cb_handler.cb_handler(c,cb)

async def showQueue(c:Client, cb: CallbackQuery):
	try:
		markup = await MakeButtons(c,cb.message,queueDB)
		await cb.message.edit(
			text="Okay,\nSekarang Kirim Beberapa Video/Subtitle atau Tekan Tombol **Merge Now**!",
			reply_markup=InlineKeyboardMarkup(markup)
		)
	except ValueError:
		await cb.message.edit('Kirim Beberapa Video')
	return

async def delete_all(root):
	try:
		shutil.rmtree(root)
	except Exception as e:
		print(e)

async def MakeButtons(bot: Client, m: Message, db: dict):
	markup = []
	for i in (await bot.get_messages(chat_id=m.chat.id, message_ids=db.get(m.chat.id)['videos'])):
		media = i.video or i.document or None
		if media is None:
			continue
		else:
			markup.append([InlineKeyboardButton(f"{media.file_name}", callback_data=f"showFileName_{i.message_id}")])
	markup.append([InlineKeyboardButton("🔗 Merge Now", callback_data="merge")])
	markup.append([InlineKeyboardButton("💥 Hapus Files", callback_data="cancel")])
	return markup


if __name__ == '__main__':	
	mergeApp.run()
