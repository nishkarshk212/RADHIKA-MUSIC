# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic


from pyrogram import Client


from pyrogram import errors

from ishu import config, logger


class Userbot(Client):
    def __init__(self):
        """
        Initializes the userbot with multiple clients.

        This method sets up clients for the userbot using predefined session strings.
        Each client is assigned a unique name based on the key in the `clients` dictionary.
        """
        self.clients = []
        clients = {"one": "SESSION1", "two": "SESSION2", "three": "SESSION3"}
        for key, string_key in clients.items():
            name = f"AnonyUB{key[-1]}"
            session = getattr(config, string_key)
            setattr(
                self,
                key,
                Client(
                    name=name,
                    api_id=config.API_ID,
                    api_hash=config.API_HASH,
                    session_string=session,
                ),
            )

    async def boot_client(self, num: int, ub: Client):
        """
        Boot a client and perform initial setup.
        Args:
            num (int): The client number to boot (1, 2, or 3).
            ub (Client): The userbot client instance.
        Raises:
            SystemExit: If the client fails to send a message in the log group.
        """
        clients = {
            1: self.one,
            2: self.two,
            3: self.three,
        }
        client = clients[num]
        try:
            await client.start()
        except errors.AuthKeyDuplicated:
            # Telegram invalidated this session because the SAME session
            # string is (or was) connected from another place at the same
            # time. Once duplicated, the key is dead until regenerated.
            raise SystemExit(
                f"\n\n[Assistant {num}] AuthKeyDuplicated: the SESSION{num} "
                "session string is being used by another instance (or was), "
                "so Telegram invalidated it.\n"
                "FIX (pick ONE):\n"
                "  1. Make sure ONLY ONE deployment uses this session string "
                "(kill the duplicate Railway deploy / local run / other host).\n"
                "  2. If the key is already dead, generate a fresh session with "
                "`python generate_session.py` and update SESSION"
                f"{num} in your env.\n"
            )
        try:
            await client.send_message(config.LOGGER_ID, "Assistant Started")
        except Exception:
            raise SystemExit(f"Assistant {num} failed to send message in log group.")

        client.id = ub.me.id
        client.name = ub.me.first_name
        client.username = ub.me.username
        client.mention = ub.me.mention
        self.clients.append(client)
        try:
            await ub.join_chat("AvyraUpdates")
        except Exception:
            pass
        logger.info(f"Assistant {num} started as @{client.username}")

    async def boot(self):
        """
        Asynchronously starts the assistants.
        """
        if config.SESSION1:
            await self.boot_client(1, self.one)
        if config.SESSION2:
            await self.boot_client(2, self.two)
        if config.SESSION3:
            await self.boot_client(3, self.three)

    async def exit(self):
        """
        Asynchronously stops the assistants.
        """
        if config.SESSION1:
            await self.one.stop()
        if config.SESSION2:
            await self.two.stop()
        if config.SESSION3:
            await self.three.stop()
        logger.info("Assistants stopped.")
