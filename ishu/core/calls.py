# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic


import asyncio
from pathlib import Path

from ntgcalls import (ConnectionNotFound, TelegramServerError,
                      RTMPStreamingUnsupported, ConnectionError)
from pyrogram.errors import (ChatSendMediaForbidden, ChatSendPhotosForbidden,
                             MessageIdInvalid)
from pyrogram.types import InputMediaPhoto, Message
from pytgcalls import PyTgCalls, exceptions, types
from pytgcalls.pytgcalls_session import PyTgCallsSession

from ishu import (app, config, db, lang, logger,
                   queue, thumb, userbot, yt)
from ishu.core.youtube import YouTube, set_dl_context
from ishu.helpers import Media, Track, buttons, utils


def _cleanup_file(media) -> None:
    """Delete the downloaded file for a media item, if it exists."""
    if getattr(media, "file_path", None):
        try:
            path = Path(media.file_path)
            if path.exists():
                path.unlink()
                logger.info("Cleaned up file: %s", media.file_path)
        except Exception as e:
            logger.warning("Failed to delete file %s: %s", media.file_path, e)
        media.file_path = None


def _bg_download(media) -> None:
    """
    Kick off a background download for a track.
    Only starts if neither stream_url nor file_path is already set.
    This ensures the file is ready if the stream URL expires mid-play.
    """
    if isinstance(media, Track) and not media.file_path:
        async def _task():
            try:
                path = await yt.download(media.id, video=media.video)
                if path:
                    media.file_path = path
                    logger.info("Background download complete: %s → %s", media.id, path)
            except Exception as e:
                logger.warning("Background download failed for %s: %s", media.id, e)

        asyncio.create_task(_task())


class TgCall(PyTgCalls):
    def __init__(self):
        self.clients = []

    async def pause(self, chat_id: int) -> bool:
        client = await db.get_assistant(chat_id)
        await db.playing(chat_id, paused=True)
        return await client.pause(chat_id)

    async def resume(self, chat_id: int) -> bool:
        client = await db.get_assistant(chat_id)
        await db.playing(chat_id, paused=False)
        return await client.resume(chat_id)

    async def stop(self, chat_id: int) -> None:
        client = await db.get_assistant(chat_id)

        # Clean up files for all media items in queue
        q_items = queue.get_queue(chat_id)
        for item in q_items:
            _cleanup_file(item)

        queue.clear(chat_id)
        await db.remove_call(chat_id)
        await db.set_loop(chat_id, 0)

        try:
            await client.leave_call(chat_id, close=False)
        except Exception:
            pass


    async def play_media(
        self,
        chat_id: int,
        message: Message,
        media: Media | Track,
        seek_time: int = 0,
    ) -> None:
        client = await db.get_assistant(chat_id)
        _lang = await lang.get_lang(chat_id)
        _thumb = (
            await thumb.generate(media)
            if isinstance(media, Track)
            else config.DEFAULT_THUMB
        ) if config.THUMB_GEN else None

        # ── Step 1: Resolve media path (prefer stream URL for instant play) ───
        # When STREAM_PROXY_URL is set, PyTgCalls can't proxy the direct
        # googlevideo stream URL (MediaStream has no proxy param), so it would
        # 403 on the bot's flagged egress IP. Go straight to the proxied
        # yt-dlp download instead — it's fetched through the forward proxy.
        _stream_proxy = getattr(config, "STREAM_PROXY_URL", "")
        media_path = media.file_path or (None if _stream_proxy else media.stream_url)
        used_stream = bool(media.stream_url) and not _stream_proxy

        if not media_path and isinstance(media, Track):
            if _stream_proxy:
                media.file_path = await yt.download(media.id, video=media.video)
                media_path = media.file_path
            else:
                media.stream_url = await yt.get_stream_url(media.id, video=media.video)
                if media.stream_url:
                    media_path = media.stream_url
                    used_stream = True

        # ── Step 2: Attempt playback ──────────────────────────────────────────
        stream_success = False
        if media_path:
            try:
                stream = types.MediaStream(
                    media_path=media_path,
                    audio_parameters=types.AudioQuality.HIGH,
                    video_parameters=types.VideoQuality.HD_720p,
                    audio_flags=types.MediaStream.Flags.REQUIRED,
                    video_flags=(
                        types.MediaStream.Flags.AUTO_DETECT
                        if media.video
                        else types.MediaStream.Flags.IGNORE
                    ),
                    ffmpeg_parameters=f"-ss {seek_time}" if seek_time > 1 else None,
                )
                await client.play(
                    chat_id=chat_id,
                    stream=stream,
                    config=types.GroupCallConfig(auto_start=False),
                )
                stream_success = True

                # If we started via stream URL, kick off a background download
                # so that the file is cached and cleanup works normally.
                if used_stream and isinstance(media, Track):
                    _bg_download(media)

            except Exception as e:
                logger.warning("Stream URL failed: %s. Falling back to download.", e)
                stream_success = False

        # ── Step 3: Fallback — download then play ─────────────────────────────
        if not stream_success and isinstance(media, Track):
            set_dl_context(
                chat_id=chat_id,
                chat_title=getattr(message.chat, "title", None),
                title=media.title,
                video=media.video,
            )
            media.file_path = await yt.download(media.id, video=media.video)
            media_path = media.file_path

        if not media_path:
            await message.edit_text(_lang["error_no_file"].format(config.SUPPORT_CHAT))
            if isinstance(media, Track):
                await utils.error_log(
                    context="Stream URL + Download both failed",
                    error="No media source could be resolved (all download methods returned None).",
                    chat_id=chat_id,
                    chat_title=getattr(message.chat, "title", None),
                    title=media.title,
                    video=media.video,
                )
            return await self.play_next(chat_id)

        try:
            if not stream_success:
                stream = types.MediaStream(
                    media_path=media_path,
                    audio_parameters=types.AudioQuality.HIGH,
                    video_parameters=types.VideoQuality.HD_720p,
                    audio_flags=types.MediaStream.Flags.REQUIRED,
                    video_flags=(
                        types.MediaStream.Flags.AUTO_DETECT
                        if media.video
                        else types.MediaStream.Flags.IGNORE
                    ),
                    ffmpeg_parameters=f"-ss {seek_time}" if seek_time > 1 else None,
                )
                await client.play(
                    chat_id=chat_id,
                    stream=stream,
                    config=types.GroupCallConfig(auto_start=False),
                )

            if not seek_time:
                media.time = 1
                await db.add_call(chat_id)

                # Shorten title to 50 characters max
                short_title = media.title.split("|")[0].split("(")[0].strip()
                if len(short_title) > 50:
                    short_title = short_title[:47].rstrip() + "…"

                text = _lang["play_media"].format(
                    media.url,
                    short_title,
                    media.duration,
                    media.user,
                )

                keyboard = buttons.controls(chat_id)

                if _thumb:
                    await message.edit_media(
                        media=InputMediaPhoto(
                            media=_thumb,
                            caption=text,
                        ),
                        reply_markup=keyboard,
                    )
                else:
                    await message.edit_text(
                        text,
                        reply_markup=keyboard,
                    )

                media.message_id = message.id

        except FileNotFoundError:
            await message.edit_text(_lang["error_no_file"].format(config.SUPPORT_CHAT))
            await self.play_next(chat_id)
        except exceptions.NoActiveGroupCall:
            await self.stop(chat_id)
            await message.edit_text(_lang["error_no_call"])
        except exceptions.NoAudioSourceFound:
            await message.edit_text(_lang["error_no_audio"])
            await self.play_next(chat_id)
        except (ConnectionError, ConnectionNotFound, TelegramServerError):
            await self.stop(chat_id)
            await message.edit_text(_lang["error_tg_server"])
        except RTMPStreamingUnsupported:
            await self.stop(chat_id)
            await message.edit_text(_lang["error_rtmp"])


    async def replay(self, chat_id: int) -> None:
        if not await db.get_call(chat_id):
            return

        media = queue.get_current(chat_id)
        _lang = await lang.get_lang(chat_id)
        msg = await app.send_message(chat_id=chat_id, text=_lang["play_again"])
        media.message_id = msg.id
        await self.play_media(chat_id, msg, media)


    async def play_next(self, chat_id: int) -> None:
        if loop := await db.get_loop(chat_id):
            await db.set_loop(chat_id, loop - 1)
            return await self.replay(chat_id)

        # ── Clean up the finished song's file BEFORE popping it ───────────────
        current_media = queue.get_current(chat_id)
        if current_media:
            _cleanup_file(current_media)

        # ── Advance queue ─────────────────────────────────────────────────────
        media = queue.get_next(chat_id)

        # ── FIX: check media is not None BEFORE accessing its attributes ──────
        if not media:
            return await self.stop(chat_id)

        # Delete the "now playing" message of the next track (it was "queued")
        try:
            if media.message_id:
                await app.delete_messages(
                    chat_id=chat_id,
                    message_ids=media.message_id,
                    revoke=True,
                )
                media.message_id = 0
        except Exception:
            pass

        _lang = await lang.get_lang(chat_id)
        msg = await app.send_message(chat_id=chat_id, text=_lang["play_next"])

        # ── Resolve playback source for the next track ────────────────────────
        # Priority: existing file_path → existing stream_url → get stream URL
        # When STREAM_PROXY_URL is set, prefer the proxied yt-dlp download over
        # the direct (un-proxiable) stream URL to avoid the googlevideo 403.
        _stream_proxy = getattr(config, "STREAM_PROXY_URL", "")
        if not media.file_path and not media.stream_url:
            fname = f"downloads/{media.id}.{'mp4' if media.video else 'mp3'}"
            if Path(fname).exists():
                media.file_path = fname
            elif _stream_proxy:
                media.file_path = await yt.download(media.id, video=media.video)
            else:
                # Try fast stream URL first
                media.stream_url = await yt.get_stream_url(media.id, video=media.video)

                # If still nothing, fall back to download (blocks briefly)
                if not media.stream_url:
                    media.file_path = await yt.download(media.id, video=media.video)

        if not media.stream_url and not media.file_path:
            await msg.edit_text(_lang["error_no_file"].format(config.SUPPORT_CHAT))
            return await self.play_next(chat_id)

        # ── Pre-download the track AFTER this one (look-ahead) ───────────────
        next_media = queue.get_next(chat_id, check=True)
        if next_media and isinstance(next_media, Track):
            _bg_download(next_media)

        media.message_id = msg.id
        await self.play_media(chat_id, msg, media)


    async def ping(self) -> float:
        pings = [client.ping for client in self.clients]
        return round(sum(pings) / len(pings), 2)


    async def decorators(self, client: PyTgCalls) -> None:
        @client.on_update()
        async def update_handler(_, update: types.Update) -> None:
            if isinstance(update, types.StreamEnded):
                if update.stream_type == types.StreamEnded.Type.AUDIO:
                    await self.play_next(update.chat_id)
            elif isinstance(update, types.ChatUpdate):
                if update.status in [
                    types.ChatUpdate.Status.KICKED,
                    types.ChatUpdate.Status.LEFT_GROUP,
                    types.ChatUpdate.Status.CLOSED_VOICE_CHAT,
                ]:
                    await self.stop(update.chat_id)


    async def boot(self) -> None:
        PyTgCallsSession.notice_displayed = True
        for ub in userbot.clients:
            client = PyTgCalls(ub, cache_duration=100)
            await client.start()
            self.clients.append(client)
            await self.decorators(client)
        logger.info("PyTgCalls client(s) started.")
