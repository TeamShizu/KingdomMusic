import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from pymongo import MongoClient
from config import BOT_USERNAME, DATABASE_URL as db_url
from helpers.filters import command, other_filters
from helpers.decorators import sudo_users_only

users_db = MongoClient(db_url)['users']
col = users_db['USER']
grps = users_db['GROUPS']


@Client.on_message(command(["gstats", f"gstats@{BOT_USERNAME}"]) & filters.private & ~filters.edited)
@sudo_users_only
async def stats(_, m: Message):
  users = col.find({})
  mfs = []
  for x in users:
    mfs.append(x['user_id'])
    
  total = len(mfs)
  
  grp = grps.find({})
  grps_ = []
  for x in grp:
    grps_.append(x['chat_id'])
    
  total_ = len(grps_)
  
  await m.reply_text(f"👥 Total Users: `{total}`\n💭 Total Groups: `{total_}`")
