import os
import json
import wget
import random
import aiofiles
import aiohttp
import ffmpeg
import requests
from os import path
from typing import Callable
from PIL import Image, ImageDraw, ImageFont
from pyrogram import Client, filters
from pyrogram.types import Voice
from pyrogram.errors import UserAlreadyParticipant
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from Python_ARQ import ARQ
from youtube_search import YoutubeSearch
from asyncio.queues import QueueEmpty
from config import BOT_NAME as bn
from config import DURATION_LIMIT
from config import UPDATES_CHANNEL as updateschannel
from config import que
from cache.admins import admins as a
from helpers.admins import get_administrators
from helpers.channelmusic import get_chat_id
from helpers.errors import DurationLimitError
from helpers.strings import THUMBS as lel
from helpers.decorators import errors
from helpers.decorators import authorized_users_only
from helpers.filters import command, other_filters
from helpers.gets import get_file_name
from callsmusic import callsmusic, queues
from callsmusic.callsmusic import client as USER
from converter.converter import convert
from downloaders import youtube

aiohttpsession = aiohttp.ClientSession()
chat_id = None
arq = ARQ("https://thearq.tech", ARQ_API_KEY, aiohttpsession)
DISABLED_GROUPS = []
useer ="NaN"

def cb_admin_check(func: Callable) -> Callable:
    async def decorator(client, cb):
        admemes = a.get(cb.message.chat.id)
        if cb.from_user.id in admemes:
            return await func(client, cb)
        else:
            await cb.answer("You're Not Allowed! 🥲", show_alert=True)
            return

    return decorator


def transcode(filename):
    ffmpeg.input(filename).output(
        "input.raw", format="s16le", acodec="pcm_s16le", ac=2, ar="48k"
    ).overwrite_output().run()
    os.remove(filename)


# Convert seconds to mm:ss
def convert_seconds(seconds):
    seconds = seconds % (24 * 3600)
    seconds %= 3600
    minutes = seconds // 60
    seconds %= 60
    return "%02d:%02d" % (minutes, seconds)


# Convert hh:mm:ss to seconds
def time_to_seconds(time):
    stringt = str(time)
    return sum(int(x) * 60 ** i for i, x in enumerate(reversed(stringt.split(":"))))


# Change image size
def changeImageSize(maxWidth, maxHeight, image):
    widthRatio = maxWidth / image.size[0]
    heightRatio = maxHeight / image.size[1]
    newWidth = int(widthRatio * image.size[0])
    newHeight = int(heightRatio * image.size[1])
    newImage = image.resize((newWidth, newHeight))
    return newImage


async def generate_cover(chat_name, title, thumbnail):
    async with aiohttp.ClientSession() as session:
        async with session.get(thumbnail) as resp:
            if resp.status == 200:
                f = await aiofiles.open("background.png", mode="wb")
                await f.write(await resp.read())
                await f.close()

    title = title.strip()
    if len(title) > 25:
        title = title[:22]+str('...')

    safone = random.choice(lel)
    image1 = Image.open("./background.png")
    image2 = Image.open(safone)
    image3 = changeImageSize(1280, 720, image1)
    image4 = changeImageSize(1280, 720, image2)
    image5 = image3.convert("RGBA")
    image6 = image4.convert("RGBA")
    Image.alpha_composite(image5, image6).save("temp.png")
    img = Image.open("temp.png")
    draw = ImageDraw.Draw(img)
    KRONA_52 = ImageFont.truetype("etc/KronaOne-Regular.ttf", 52)
    KRONA_SMALL = ImageFont.truetype("etc/KronaOne-Regular.ttf", 32)
    draw.text((20, 65), f"{title}", fill="white", font=KRONA_52)
    draw.text((100, 640), f"Playing On: {chat_name}", fill="white", font=KRONA_52)
    draw.text((1030, 50), f"Project", fill="white", font=KRONA_SMALL)
    draw.text((1030, 80), f" Tsukiyomi", fill="white", font=KRONA_SMALL)
    img.save("final.png")
    os.remove("temp.png")
    os.remove("background.png")


@Client.on_message(filters.command("playlist") & filters.group & ~filters.edited)
async def playlist(client, message):
    global que
    if message.chat.id in DISABLED_GROUPS:
        return    
    queue = que.get(message.chat.id)
    if not queue:
        await message.reply_text("__**Player is Idle!**__ 😴")
    temp = []
    for t in queue:
        temp.append(t)
    now_playing = temp[0][0]
    by = temp[0][1].mention(style="md")
    msg = "▶️ **Now Playing** in {}".format(message.chat.title)
    msg += "\n- " + now_playing
    msg += "\n- Req By: " + by
    temp.pop(0)
    if temp:
        msg += "\n\n"
        msg += "🔂 **Queued Playlist:**"
        for song in temp:
            name = song[0]
            usr = song[1].mention(style="md")
            msg += f"\n- {name}"
            msg += f"\n- Req By: {usr}\n"
    await message.reply_text(msg)


# ============================= Settings =========================================


def updated_stats(chat, queue, vol=100):
    if chat.id in callsmusic.pytgcalls.active_calls:
        # if chat.id in active_chats:
        stats = "⚙️ Settings of **{}**".format(chat.title)
        if len(que) > 0:
            stats += "\n\n"
            stats += "🎚 Volume : {}%\n".format(vol)
            stats += "🎵 Songs in Queue : `{}`\n".format(len(que))
            stats += "🔉 Now Playing : **{}**\n".format(queue[0][0])
            stats += "🎧 Requested By : {}".format(queue[0][1].mention)
    else:
        stats = None
    return stats


def r_ply(type_):
    if type_ == "play":
        pass
    else:
        pass
    mar = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("▶️", "resume"),
                InlineKeyboardButton("⏸", "puse"),
                InlineKeyboardButton("⏭", "skip"),
                InlineKeyboardButton("⏹", "leave"),
            ],
            [
                InlineKeyboardButton("🎹 Play List", callback_data="playlist"),
                InlineKeyboardButton("🎛 Other Menu", callback_data="menu"),
            ],
            [
                InlineKeyboardButton(text="🗑 Close Menu", callback_data="cls")
            ],
        ]
    )
    return mar


@Client.on_message(filters.command("current") & filters.group & ~filters.edited)
async def ee(client, message):
    if message.chat.id in DISABLED_GROUPS:
        return
    queue = que.get(message.chat.id)
    stats = updated_stats(message.chat, queue)
    if stats:
        await message.reply(stats)
    else:
        await message.reply("__**There Is No Voice Chat Running!**__ 🙄")


@Client.on_message(filters.command("settings") & filters.group & ~filters.edited)
@authorized_users_only
async def settings(client, message):
    if message.chat.id in DISABLED_GROUPS:
        await message.reply("🚫 __**Music Player Is Disabled!**__")
        return    
    playing = None
    chat_id = get_chat_id(message.chat)
    if chat_id in callsmusic.pytgcalls.active_calls:
        playing = True
    queue = que.get(chat_id)
    stats = updated_stats(message.chat, queue)
    if stats:
        if playing:
            await message.reply(stats, reply_markup=r_ply("pause"))

        else:
            await message.reply(stats, reply_markup=r_ply("play"))
    else:
        await message.reply("__**There Is No Voice Chat Running!**__ 🙄")


@Client.on_message(
    filters.command("musicplayer") & ~filters.edited & ~filters.bot & ~filters.private
)
@authorized_users_only
async def hfmm(_, message):
    global DISABLED_GROUPS
    try:
        user_id = message.from_user.id
    except:
        return
    if len(message.command) != 2:
        await message.reply_text(
            "💁 __**I Recognize `/musicplayer on` & /musicplayer off` Only!**__"
        )
        return
    status = message.text.split(None, 1)[1]
    message.chat.id
    if status == "ON" or status == "on" or status == "On":
        lel = await message.reply("`Processing ...`")
        if not message.chat.id in DISABLED_GROUPS:
            await lel.edit("✅ __**Music Player Already Activated In This Chat!**__")
            return
        DISABLED_GROUPS.remove(message.chat.id)
        await lel.edit(
            f"✅ __**Music Player Successfully Enabled For Users In The Chat {message.chat.id}!**__"
        )

    elif status == "OFF" or status == "off" or status == "Off":
        lel = await message.reply("`Processing ...`")
        
        if message.chat.id in DISABLED_GROUPS:
            await lel.edit("❎ __**Music Player Already Turned Off In This Chat!**__")
            return
        DISABLED_GROUPS.append(message.chat.id)
        await lel.edit(
            f"❎ __**Music Player Successfully Deactivated For Users In The Chat {message.chat.id}!**__"
        )
    else:
        await message.reply_text(
            "💁 __**I Recognize `/musicplayer on` & /musicplayer off` Only!**__"
        )    
        

@Client.on_callback_query(filters.regex(pattern=r"^(playlist)$"))
async def p_cb(b, cb):
    global que
    que.get(cb.message.chat.id)
    type_ = cb.matches[0].group(1)
    cb.message.chat.id
    cb.message.chat
    cb.message.reply_markup.inline_keyboard[1][0].callback_data
    if type_ == "playlist":
        queue = que.get(cb.message.chat.id)
        if not queue:
            await cb.message.edit("__**Player is Idle!**__ 😴")
        temp = []
        for t in queue:
            temp.append(t)
        now_playing = temp[0][0]
        by = temp[0][1].mention(style="md")
        msg = "▶️ **Now Playing** in {}".format(cb.message.chat.title)
        msg += "\n- " + now_playing
        msg += "\n- Req By: " + by
        temp.pop(0)
        if temp:
            msg += "\n\n"
            msg += "🔂 **Queued Playlist:**"
            for song in temp:
                name = song[0]
                usr = song[1].mention(style="md")
                msg += f"\n- {name}"
                msg += f"\n- Req By: {usr}\n"
        await cb.message.edit(msg)


@Client.on_callback_query(
    filters.regex(pattern=r"^(play|pause|skip|leave|puse|resume|menu|cls)$")
)
@cb_admin_check
async def m_cb(b, cb):
    global que
    if (
        cb.message.chat.title.startswith("Zero Two: ")
        and chat.title[14:].isnumeric()
    ):
        chet_id = int(chat.title[13:])
    else:
        chet_id = cb.message.chat.id
    qeue = que.get(chet_id)
    type_ = cb.matches[0].group(1)
    cb.message.chat.id
    m_chat = cb.message.chat

    the_data = cb.message.reply_markup.inline_keyboard[1][0].callback_data
    if type_ == "pause":
        if (chet_id not in callsmusic.pytgcalls.active_calls) or (
            callsmusic.pytgcalls.active_calls[chet_id] == "paused"
        ):
            await cb.answer("Voice Chat Is Not Connected!", show_alert=True)
        else:
            callsmusic.pytgcalls.pause_stream(chet_id)

            await cb.answer("Music Paused!")
            await cb.message.edit(
                updated_stats(m_chat, qeue), reply_markup=r_ply("play")
            )

    elif type_ == "play":
        if (chet_id not in callsmusic.pytgcalls.active_calls) or (
            callsmusic.pytgcalls.active_calls[chet_id] == "playing"
        ):
            await cb.answer("Voice Chat Is Not Connected!", show_alert=True)
        else:
            callsmusic.pytgcalls.resume_stream(chet_id)
            await cb.answer("Music Resumed!")
            await cb.message.edit(
                updated_stats(m_chat, qeue), reply_markup=r_ply("pause")
            )

    elif type_ == "playlist":
        queue = que.get(cb.message.chat.id)
        if not queue:
            await cb.message.edit("__**Player is Idle!**__ 😴")
        temp = []
        for t in queue:
            temp.append(t)
        now_playing = temp[0][0]
        by = temp[0][1].mention(style="md")
        msg = "▶️ **Now Playing** in {}".format(cb.message.chat.title)
        msg += "\n- " + now_playing
        msg += "\n- Req By: " + by
        temp.pop(0)
        if temp:
            msg += "\n\n"
            msg += "🔂 **Queued Playlist:**"
            for song in temp:
                name = song[0]
                usr = song[1].mention(style="md")
                msg += f"\n- {name}"
                msg += f"\n- Req By: {usr}\n"
        await cb.message.edit(msg)

    elif type_ == "resume":
        if (chet_id not in callsmusic.pytgcalls.active_calls) or (
            callsmusic.pytgcalls.active_calls[chet_id] == "playing"
        ):
            await cb.answer("Maybe Not Connected or Already Playing!", show_alert=True)
        else:
            callsmusic.pytgcalls.resume_stream(chet_id)
            await cb.answer("Music Resumed!")
    elif type_ == "puse":
        if (chet_id not in callsmusic.pytgcalls.active_calls) or (
            callsmusic.pytgcalls.active_calls[chet_id] == "paused"
        ):
            await cb.answer("Maybe Not Connected or Already Paused!", show_alert=True)
        else:
            callsmusic.pytgcalls.pause_stream(chet_id)

            await cb.answer("Music Paused!")
    elif type_ == "cls":
        await cb.answer("Closed Menu!")
        await cb.message.delete()

    elif type_ == "menu":
        stats = updated_stats(cb.message.chat, qeue)
        await cb.answer("Menu Opened!")
        marr = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("⬇️ Get Audio", "getaud"),
                    InlineKeyboardButton("⬇️ Get Video", "getvid"),
                ],
                [
                    InlineKeyboardButton("➕ Play List", "playlist"),
                    InlineKeyboardButton("🗑 Close Menu", "cls"),
                ]
            ]
        )
        await cb.message.edit(stats, reply_markup=marr)
    elif type_ == "skip":
        if qeue:
            qeue.pop(0)
        if chet_id not in callsmusic.pytgcalls.active_calls:
            await cb.answer("Voice Chat Is Not Connected!", show_alert=True)
        else:
            callsmusic.queues.task_done(chet_id)

            if callsmusic.queues.is_empty(chet_id):
                callsmusic.pytgcalls.leave_group_call(chet_id)

                await cb.message.edit("__**No Song In Queue!**__ 😪\n**Leaving From Voice Chat...**")
            else:
                callsmusic.pytgcalls.change_stream(
                    chet_id, callsmusic.queues.get(chet_id)["file"]
                )
                await cb.answer("Skipped!")
                await cb.message.edit((m_chat, qeue), reply_markup=r_ply(the_data))
                await cb.message.reply_text(
                    f"__**Skipped Track!**__\n▶️ **Now Playing:** **{qeue[0][0]}**"
                )

    else:
        if chet_id in callsmusic.pytgcalls.active_calls:
            try:
                callsmusic.queues.clear(chet_id)
            except QueueEmpty:
                pass

            callsmusic.pytgcalls.leave_group_call(chet_id)
            await cb.message.edit("✅ __**Successfully Left The Voice Chat!**__")
        else:
            await cb.answer("Voice Chat Is Not Connected!", show_alert=True)


@Client.on_message(command("play") & other_filters)
async def play(_, message: Message):
    global que
    global useer
    if message.chat.id in DISABLED_GROUPS:
        return    
    lel = await message.reply_text("Hang On! Processing ... 🎵")
    administrators = await get_administrators(message.chat)
    chid = message.chat.id

    try:
        user = await USER.get_me()
    except:
        user.first_name = "Akatsuki_02_Assistant"
    usar = user
    wew = usar.id
    try:
        # chatdetails = await USER.get_chat(chid)
        await _.get_chat_member(chid, wew)
    except:
        for administrator in administrators:
            if administrator == message.from_user.id:
                if message.chat.title.startswith("Stream Music: "):
                    await lel.edit(
                        "<i><b>Remember To Add @Akatsuki_02_Assistant To Your Channel! 🙂</b></i>",
                    )
                    pass
                try:
                    invitelink = await _.export_chat_invite_link(chid)
                except:
                    await lel.edit(
                        "<i><b>Add Me As Admin Of Your Group First! 🙂</b></i>",
                    )
                    return

                try:
                    await USER.join_chat(invitelink)
                    await USER.send_message(
                        message.chat.id, "👋🏻 Hello Admin, \nI Joined Here For Playing Music In Voice Chat!"
                    )
                    await lel.edit(
                        "<i><b>My Assistant Userbot Joined Your Chat! 😌</b></i>",
                    )

                except UserAlreadyParticipant:
                    pass
                except Exception:
                    # print(e)
                    await lel.edit(
                        f"<b>🔴 Flood Wait Error 🔴 </b>\n<i><b>{user.first_name} Couldn't Join Your Group Due To Heavy Requests For Userbot! Make Sure My Assistant Is Not Blocked/Banned In Your Group.</b></i>🤔"
                         " <i><b>Or Manually Add @Akatsuki_02_Assistant To Your Group & Try Again!!</b></i>",
                    )
    try:
        await USER.get_chat(chid)
        # lmoa = await client.get_chat_member(chid,wew)
    except:
        await lel.edit(
            f"<i>{user.first_name} Not In This Chat, Ask Admin To Send /play Command For First Time or Add @Akatuski_02_Assistant Manually! 😶</i>"
        )
        return
    text_links=None
    await lel.edit("`Hang On! Searching ...`🔎")
    if message.reply_to_message:
        entities = []
        toxt = message.reply_to_message.text or message.reply_to_message.caption
        if message.reply_to_message.entities:
            entities = message.reply_to_message.entities + entities
        elif message.reply_to_message.caption_entities:
            entities = message.reply_to_message.entities + entities
        urls = [entity for entity in entities if entity.type == 'url']
        text_links = [
            entity for entity in entities if entity.type == 'text_link'
        ]
    else:
        urls=None
    if text_links:
        urls = True
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    rpk = "[" + user_name + "](tg://user?id=" + str(user_id) + ")"
    audio = (
        (message.reply_to_message.audio or message.reply_to_message.voice)
        if message.reply_to_message
        else None
    )
    if audio:
        if round(audio.duration / 60) > DURATION_LIMIT:
            raise DurationLimitError(
                f"__**Sorry!🥲 I Can't Play Songs Which Longer Than {DURATION_LIMIT} Minutes!**__"
            )
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("⏸", "puse"),
                    InlineKeyboardButton("▶️", "resume"),
                    InlineKeyboardButton("⏭", "skip"),
                    InlineKeyboardButton("⏹", "leave"),
                ],
                [
                    InlineKeyboardButton("🎹 Play List", callback_data="playlist"),
                    InlineKeyboardButton("🎛 Other Menu", callback_data="menu"),
                ],
                [
                    InlineKeyboardButton(text="🗑 Close Menu", callback_data="cls")
                ],
                ]
        )
        file_name = get_file_name(audio)
        title = file_name
        thumb_name = "https://telegra.ph/file/820cac7cb7b1a025542e2.png"
        thumbnail = thumb_name
        duration = round(audio.duration / 60)
        views = "Locally Added"
        chat_name = message.chat.title
        requested_by = message.from_user.first_name
        await generate_cover(chat_name, title, thumbnail)
        file_path = await convert(
            (await message.reply_to_message.download(file_name))
            if not path.isfile(path.join("downloads", file_name))
            else file_name
        )
    elif urls:
        query = toxt
        await lel.edit(" Hang On! Processing ... 🎵")
        ydl_opts = {"format": "bestaudio[ext=m4a]"}
        try:
            results = YoutubeSearch(query, max_results=1).to_dict()
            url = f"https://youtube.com{results[0]['url_suffix']}"
            # print(results)
            title = results[0]["title"][:40]
            thumbnail = results[0]["thumbnails"][0]
            thumb_name = f"thumb{title}.jpg"
            thumb = requests.get(thumbnail, allow_redirects=True)
            open(thumb_name, "wb").write(thumb.content)
            duration = results[0]["duration"]
            results[0]["url_suffix"]
            views = results[0]["views"]

        except Exception as e:
            await lel.edit(
                "__**Literary Found Noting 🥲 \nPlease Try Another Song or Use Correct Spelling!**__"
            )
            print(str(e))
            return
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("⏸", "puse"),
                    InlineKeyboardButton("▶️", "resume"),
                    InlineKeyboardButton("⏭", "skip"),
                    InlineKeyboardButton("⏹", "leave"),
                ],
                [
                    InlineKeyboardButton("🎹 Play List", callback_data="playlist"),
                    InlineKeyboardButton("🎛 Other Menu", callback_data="menu"),
                ],
                [
                    InlineKeyboardButton(text="🗑 Close Menu", callback_data="cls")
                ],
                ]
        )
        chat_name = message.chat.title
        requested_by = message.from_user.first_name
        await generate_cover(chat_name, title, thumbnail)
        file_path = await convert(youtube.download(url))        
    else:
        query = ""
        for i in message.command[1:]:
            query += " " + str(i)
        print(query)
        await lel.edit(" Hang On! Processing ... 🎵")
        ydl_opts = {"format": "bestaudio[ext=m4a]"}
        
        try:
          results = YoutubeSearch(query, max_results=5).to_dict()
        except:
          await lel.edit("😕 __**Give Me The Song Name To Play!**__")
        # Looks like hell. Aren't it?? FUCK OFF
        try:
            toxxt = "**Select The Song You Want To Play:**\n\n"
            j = 0
            useer=user_name
            emojilist = ["1️⃣","2️⃣","3️⃣","4️⃣","5️⃣",]

            while j < 5:
                toxxt += f"{emojilist[j]} [{results[j]['title'][:25]}...](https://youtube.com{results[j]['url_suffix']})\n"
                toxxt += f" ├ ⚡ __ Powered By - [MizuharaSemxy](https://t.me/smexy_updates)__\n\n"
                toxxt += f" └ ❄ __•Network [Project Tsukiyomi](https://t.me/Project_tsukiyomi)__\n\n"
                
                j += 1            
            koyboard = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton("1️⃣", callback_data=f'plll 0|{query}|{user_id}'),
                        InlineKeyboardButton("2️⃣", callback_data=f'plll 1|{query}|{user_id}'),
                        InlineKeyboardButton("3️⃣", callback_data=f'plll 2|{query}|{user_id}'),
                    ],
                    [
                        InlineKeyboardButton("4️⃣", callback_data=f'plll 3|{query}|{user_id}'),
                        InlineKeyboardButton("5️⃣", callback_data=f'plll 4|{query}|{user_id}'),
                    ],
                    [
                        InlineKeyboardButton(text="🗑 Close", callback_data="cls"),
                    ],
                ]
            )
            pic = f'https://telegra.ph/file/260a248639448684143c6.jpg'
            await message.reply_photo(photo=pic, caption=toxxt, reply_markup=koyboard)
            # WHY PEOPLE ALWAYS LOVE PORN ?? (A point to think)
            return
            # Returning to pornhub
        except:
            await lel.edit(" Hang On! Starting ... 🎵")
                        
            # print(results)
            try:
                url = f"https://youtube.com{results[0]['url_suffix']}"
                title = results[0]["title"][:40]
                thumbnail = results[0]["thumbnails"][0]
                thumb_name = f"thumb{title}.jpg"
                thumb = requests.get(thumbnail, allow_redirects=True)
                open(thumb_name, "wb").write(thumb.content)
                duration = results[0]["duration"]
                results[0]["url_suffix"]
                views = results[0]["views"]

            except Exception as e:
                await lel.edit(
                    "__**Literary Found Noting 🥲 \nPlease Try Another Song or Use Correct Spelling!**__"
                )
                print(str(e))
                return
            keyboard = InlineKeyboardMarkup(
                [
                [
                    InlineKeyboardButton("⏸", "puse"),
                    InlineKeyboardButton("▶️", "resume"),
                    InlineKeyboardButton("⏭", "skip"),
                    InlineKeyboardButton("⏹", "leave"),
                ],
                [
                    InlineKeyboardButton("🎹 Play List", callback_data="playlist"),
                    InlineKeyboardButton("🎛 Other Menu", callback_data="menu"),
                ],
                [
                    InlineKeyboardButton(text="🗑 Close Menu", callback_data="cls")
                ],
                ]
            )
            chat_name = message.chat.title
            requested_by = message.from_user.first_name
            await generate_cover(chat_name, title, thumbnail)
            file_path = await convert(youtube.download(url))   
    chat_id = get_chat_id(message.chat)
    if chat_id in callsmusic.pytgcalls.active_calls:
        position = await queues.put(chat_id, file=file_path)
        qeue = que.get(chat_id)
        s_name = title
        r_by = message.from_user
        loc = file_path
        appendable = [s_name, r_by, loc]
        qeue.append(appendable)
        await message.reply_photo(
            photo="final.png",
            caption="🎙 **Title** : [{}]({})\n⏱ **Duration** : `{}`\n💡 **Status** : `Queued ({})`\n🎧 **Requested By** : {}".format(
                title, url, duration, position, message.from_user.mention()
            ),
            reply_markup=keyboard,
        )
        os.remove("final.png")
        try:
            await lel.delete()
        except:
            pass
        return
    else:
        chat_id = get_chat_id(message.chat)
        que[chat_id] = []
        qeue = que.get(chat_id)
        s_name = title
        r_by = message.from_user
        loc = file_path
        appendable = [s_name, r_by, loc]
        qeue.append(appendable)
        try:
            callsmusic.pytgcalls.join_group_call(chat_id, file_path)
        except:
            message.reply("__**Group Call Is Not Connected or I Can't Join VC!**__")
            return
        await message.reply_photo(
            photo="final.png",
            reply_markup=keyboard,
            caption="🎙 **Title** : [{}]({})\n⏱ **Duration** : `{}`\n💡 **Status** : `Playing`\n🎧 **Requested By** : {}".format(
                title, url, duration, message.from_user.mention()
            ),
        )
        os.remove("final.png")
        try:
            await lel.delete()
        except:
            pass
        return


@Client.on_callback_query(filters.regex(pattern=r"plll"))
async def lol_cb(b, cb):
    global que

    cbd = cb.data.strip()
    chat_id = cb.message.chat.id
    chaat_name = cb.message.chat.title
    typed_=cbd.split(None, 1)[1]
    try:
        x,query,useer_id = typed_.split("|")      
    except:
        await cb.message.edit("__**Literary Found Noting 🥲 \nPlease Try Another Song or Use Correct Spelling!**__")
        return
    useer_id = int(useer_id)
    if cb.from_user.id != useer_id:
        await cb.answer("🤭 You Ain't The Person Who Requested To Play This Song!", show_alert=True)
        return
    x=int(x)
    try:
        useer_name = cb.message.reply_to_message.from_user.first_name
    except:
        useer_name = cb.message.from_user.first_name
    
    results = YoutubeSearch(query, max_results=5).to_dict()
    resultss=results[x]["url_suffix"]
    title=results[x]["title"][:40]
    thumbnail=results[x]["thumbnails"][0]
    duration=results[x]["duration"]
    views=results[x]["views"]
    url = f"https://youtube.com{resultss}"
    
    try:    
        duuration= round(duration / 60)
        if duuration > DURATION_LIMIT:
            await cb.message.edit(f"__**Sorry! 🥲 \nI Can't Play Songs Which Longer Than {DURATION_LIMIT} Minutes!**__")
            return
    except:
        pass
    try:
        thumb_name = f"thumb{title}.jpg"
        thumb = requests.get(thumbnail, allow_redirects=True)
        open(thumb_name, "wb").write(thumb.content)
    except Exception as e:
        print(e)
        return
    keyboard = InlineKeyboardMarkup(
        [
                [
                    InlineKeyboardButton("⏸", "puse"),
                    InlineKeyboardButton("▶️", "resume"),
                    InlineKeyboardButton("⏭", "skip"),
                    InlineKeyboardButton("⏹", "leave"),
                ],
                [
                    InlineKeyboardButton("🎹 Play List", callback_data="playlist"),
                    InlineKeyboardButton("🎛 Other Menu", callback_data="menu"),
                ],
                [
                    InlineKeyboardButton(text="🗑 Close Menu", callback_data="cls")
                ],
         ]
    )
    chat_name = chaat_name
    requested_by = useer_name
    await generate_cover(chat_name, title, thumbnail)
    file_path = await convert(youtube.download(url))  
    if chat_id in callsmusic.pytgcalls.active_calls:
        position = await queues.put(chat_id, file=file_path)
        qeue = que.get(chat_id)
        s_name = title
        try:
            r_by = cb.message.reply_to_message.from_user
        except:
            r_by = cb.message.from_user
        loc = file_path
        appendable = [s_name, r_by, loc]
        qeue.append(appendable)
        await cb.message.delete()
        await b.send_photo(chat_id,
            photo="final.png",
            caption="🎙 **Title** : [{}]({})\n⏱ **Duration** : `{}`\n💡 **Status** : `Queued ({})`\n🎧 **Requested By** : {}".format(
                title, url, duration, position, r_by.mention()
            ),
            reply_markup=keyboard,
        )
        os.remove("final.png")
        try:
            await lel.delete()
        except:
            pass
        
    else:
        que[chat_id] = []
        qeue = que.get(chat_id)
        s_name = title
        try:
            r_by = cb.message.reply_to_message.from_user
        except:
            r_by = cb.message.from_user
        loc = file_path
        appendable = [s_name, r_by, loc]
        qeue.append(appendable)

        callsmusic.pytgcalls.join_group_call(chat_id, file_path)
        await cb.message.delete()
        await b.send_photo(chat_id,
            photo="final.png",
            reply_markup=keyboard,
            caption="🎙 **Title** : [{}]({})\n⏱ **Duration** : `{}`\n💡 **Status** : `Playing`\n🎧 **Requested By** : {}".format(
                title, url, duration, r_by.mention()
            ),
        )
        
        os.remove("final.png")
        try:
            await lel.delete()
        except:
            pass

# Have u read all. If read RESPECT :-)
