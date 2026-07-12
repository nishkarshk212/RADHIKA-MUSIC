# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic


import os
import sys
import shutil
import asyncio

from pyrogram import filters, types

from ishu import app, db, lang, stop, config


@app.on_message(filters.command(["logs"]) & app.sudoers)
@lang.language()
async def _logs(_, m: types.Message):
    sent = await m.reply_text(m.lang["log_fetch"])
    if not os.path.exists("log.txt"):
        return await sent.edit_text(m.lang["log_not_found"])
    await sent.edit_media(
        media=types.InputMediaDocument(
            media="log.txt",
            caption=m.lang["log_sent"].format(app.name),
        )
    )


@app.on_message(filters.command(["logger"]) & app.sudoers)
@lang.language()
async def _logger(_, m: types.Message):
    if len(m.command) < 2:
        return await m.reply_text(m.lang["logger_usage"].format(m.command[0]))
    if m.command[1] not in ("on", "off"):
        return await m.reply_text(m.lang["logger_usage"].format(m.command[0]))

    if m.command[1] == "on":
        await db.set_logger(True)
        await m.reply_text(m.lang["logger_on"])
    else:
        await db.set_logger(False)
        await m.reply_text(m.lang["logger_off"])


async def restart_bot():
    asyncio.create_task(stop())
    await asyncio.sleep(2)
    os.execl(sys.executable, sys.executable, "-m", "ishu")


@app.on_message(filters.command(["restart"]) & app.sudoers)
@lang.language()
async def _restart(_, m: types.Message):
    sent = await m.reply_text(m.lang["restarting"])

    for directory in ["cache", "downloads"]:
        shutil.rmtree(directory, ignore_errors=True)

    await sent.edit_text(m.lang["restarted"])
    try: os.remove("log.txt")
    except Exception: pass

    await restart_bot()


@app.on_message(filters.command(["update"]) & filters.user(config.OWNER_ID))
async def _update(_, m: types.Message):
    sent = await m.reply_text("Checking for updates and pulling from git...")
    
    process = await asyncio.create_subprocess_shell(
        "git pull",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    
    output = stdout.decode().strip()
    error = stderr.decode().strip()
    
    if "Already up to date." in output:
        return await sent.edit_text("Bot is already up to date!")
        
    if process.returncode != 0:
        return await sent.edit_text(f"**Git Pull Failed:**\n`{error or output}`")
        
    await sent.edit_text(f"**Updated successfully!**\n\n`{output}`\n\nRestarting the bot...")
    
    for directory in ["cache", "downloads"]:
        shutil.rmtree(directory, ignore_errors=True)
        
    try: os.remove("log.txt")
    except Exception: pass
    
    await restart_bot()


@app.on_message(filters.command(["env"]) & filters.user(config.OWNER_ID))
async def _env(_, m: types.Message):
    sent = await m.reply_text("Fetching env file...")
    env_path = ".env"
    
    if os.path.exists(env_path):
        await sent.delete()
        return await m.reply_document(
            document=env_path,
            caption=f"Here is the local `{env_path}` file.",
        )
        
    # If .env does not exist (like on Railway), construct it from active environment variables
    try:
        temp_env = "temp.env"
        with open(temp_env, "w", encoding="utf-8") as f:
            f.write("# Generated from active environment variables\n\n")
            keys = [
                "API_ID", "API_HASH", "BOT_TOKEN", "LOGGER_ID", "MONGO_URL", "OWNER_ID",
                "SESSION", "SESSION2", "SESSION3", "COOKIES_DATA", "RAILWAY_YT_API_URL",
                "RAILWAY_YT_API_KEY", "SHRUTI_API_URL", "SHRUTI_API_KEY", "YTPROXY_URL",
                "YT_API_KEY", "DURATION_LIMIT", "QUEUE_LIMIT", "PLAYLIST_LIMIT",
                "SUPPORT_CHANNEL", "SUPPORT_CHAT", "DEFAULT_THUMB", "PING_IMG", "START_IMG"
            ]
            for key in keys:
                val = os.environ.get(key)
                if val is not None:
                    f.write(f"{key}={val}\n")
                elif hasattr(config, key):
                    val_attr = getattr(config, key)
                    if val_attr:
                        f.write(f"{key}={val_attr}\n")
                        
        await sent.delete()
        await m.reply_document(
            document=temp_env,
            file_name=".env",
            caption="Constructed from active environment variables.",
        )
        try: os.remove(temp_env)
        except Exception: pass
    except Exception as e:
        await sent.edit_text(f"Failed to retrieve or generate env: {e}")
