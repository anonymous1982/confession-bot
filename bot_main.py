import sys
import time
import telepot
import datetime
import sqlite3
import hashlib
import re
import git
import os

"""
$ python3.2 skeleton_extend.py <token>
A skeleton for your telepot programs - extend from `Bot` and define a `handle` method.
"""

"""
This bot's purpose: to take text confessions and (anonymously) send them to https://telegram.me/shithole_confessions
"""

"""
Plans for the future:
    Finish up /ban
    add /unban
"""



class BangarangsBot(telepot.Bot):

    def confess(self, chat_id, msg):

        confession = msg['text'].replace("/Confess", "/confess", 1).replace("/confess@shitholeConfessionsBot ", "/confess", 1).replace("/confess ", "", 1)

        sha = hashlib.sha256()
        sha.update(bytes(chat_id))
        hashed_id = sha.hexdigest()

        #banned_phrases = open("banned_words.txt") #banned_words.txt won't be posted on github since the _smart_ trolls would just look at it and phrase carefully
        #for phrase in banned_phrases.readlines():
        #    if (phrase.lower().strip() in confession.strip().lower()): #so spacing out words / case is irrelvant - might catch words occasionally from enjambment
        #        print(" !! FLAGGED CONFESSION\nID:" + str(hashed_id) + "\nmsg:" + confession) #continue on silently



        # let's try to avoid opening the DB if we can

        if len(confession) < 10:  # to cut down on spam, I don't anticipate this being a problem.
            self.sendMessage(msg['from']['id'], "Sorry, but in order to cut down on spam, confessions need to be at least 10 characters.", reply_to_message_id=msg['message_id'])
            return

        # let's open up the DB

        confessions_db = sqlite3.connect("confessions.db")
        confessions_cur = confessions_db.cursor()

        # make sure the tables exist for the first run, or in case migration

        confessions_cur.execute('CREATE TABLE IF NOT EXISTS confessors (confessor_id_hash TEXT PRIMARY KEY, last_confession TEXT NOT NULL, unix_timestamp INTEGER NOT NULL, number_confessions INTEGER NOT NULL)')

        confessions_cur.execute('CREATE TABLE IF NOT EXISTS banned_people (banned_id_hash TEXT PRIMARY KEY, ban_reason TEXT NOT NULL, unix_timestamp INTEGER NOT NULL)')

        # see if the person is in the banned table

        person_is_banned = confessions_cur.execute("SELECT banned_id_hash, ban_reason, unix_timestamp FROM banned_people WHERE banned_id_hash=?", (hashed_id, )).fetchone()

        if (person_is_banned):
            self.sendMessage(chat_id, "Sorry, but you are banned for the following reason:\n" + person_is_banned[1] + "\n\nUnix timestamp of ban: " + person_is_banned[2], reply_to_message_id=msg['message_id'])
            print("  ! Banned user " + person_is_banned[0] + " is attempting to confess again.")
            return

        # see if they surpass the rate limit (or see if they've never confessed, which makes it easy)

        person_confessed_before = confessions_cur.execute("SELECT confessor_id_hash, unix_timestamp FROM confessors WHERE confessor_id_hash=?", (hashed_id, )).fetchone()

        if (person_confessed_before):

            curTime = time.time() # potentially, the bot could be under heavy load and the time could roll over to a valid time on the next line, which would lead to a hilarious "0 or -1 more seconds" message.

            timeout = 300

            if (person_confessed_before[1] + timeout > curTime):
                time_remaining = str(int(person_confessed_before[1] + timeout - curTime))
                self.sendMessage(chat_id, "Sorry, but you can only lodge a confession every " + str(timeout / 60) + " minutes. You'll need to wait " + time_remaining + " more seconds until you can confess again.", reply_to_message_id=msg['message_id']) #ideally would give the timedelta
                return

            else:
                confessions_cur.execute("UPDATE confessors SET unix_timestamp=?, number_confessions=number_confessions+1 WHERE confessor_id_hash=?", (int(time.time()), hashed_id))

        else:
            confessions_cur.execute("INSERT INTO confessors values(?, ?, ?, 1)", (hashed_id, confession, int(time.time())))


        confessions_db.commit()
        confessions_db.close()

        self.sendMessage('-106839678', confession + "\n\n ID hash: " + str(hashed_id)) #paste message contents to the admin group
        self.sendMessage('@shithole_confessions', "Confession:\n"+ confession) # in case in the future I want to distinguish between confessions and announcements to tell people to knock it off
        self.sendMessage(chat_id, "Confession sent successfully.", reply_to_message_id=msg['message_id'])

    def contactAdmin(self, chat_id, msg):

        toAdmin = msg['text'].replace("/contactAdmin ", "/contactadmin", 1).replace("/contactadmin@shitholeConfessionsBot ", "/contactadmin", 1).replace("/contactadmin ", "", 1)

        sha = hashlib.sha256()
        sha.update(bytes(chat_id))
        hashed_id = sha.hexdigest()

        # let's open up the DB

        confessions_db = sqlite3.connect("confessions.db")
        confessions_cur = confessions_db.cursor()

        # make sure the tables exist for the first run, or in case migration

        confessions_cur.execute('CREATE TABLE IF NOT EXISTS banned_people (banned_id_hash TEXT PRIMARY KEY, ban_reason TEXT NOT NULL, unix_timestamp INTEGER NOT NULL)')

        confessions_cur.execute('CREATE TABLE IF NOT EXISTS admin_contact (id_hash TEXT PRIMARY KEY, unix_timestamp INTEGER NOT NULL)')

        # confessions_cur.execute('CREATE TABLE IF NOT EXISTS very_banned_people (banned_id_hash TEXT PRIMARY KEY, ban_reason TEXT NOT NULL, unix_timestamp INTEGER NOT NULL)')

        # see if the person is in the banned table

        person_is_banned = confessions_cur.execute("SELECT banned_id_hash, ban_reason, unix_timestamp FROM banned_people WHERE banned_id_hash=?", (hashed_id, )).fetchone()

        last_time_contacted = confessions_cur.execute("SELECT id_hash, unix_timestamp FROM admin_contact WHERE id_hash=?", (hashed_id, )).fetchone()

        if (last_time_contacted):
            curTime = time.time()
            banned_timeout = 172800
            normal_timeout = 7200

            if (person_is_banned and (last_time_contacted[1] + banned_timeout > curTime)):
                self.sendMessage(chat_id, "Sorry, you're banned and must wait " + str(int((last_time_contacted[1] + banned_timeout - curTime) / 60)) + " minutes before you can contact the admins again.", reply_to_message_id=msg['message_id'])
                return
            elif (last_time_contacted[1] + normal_timeout > curTime):
                self.sendMessage(chat_id, "Sorry, you must wait " + str(int((last_time_contacted[1] + normal_timeout - curTime) / 60)) + " minutes before you can contact the admins again.", reply_to_message_id=msg['message_id'])
                return
            else:
                 confessions_cur.execute("UPDATE admin_contact SET unix_timestamp=?  WHERE id_hash=?", (int(time.time()), hashed_id))
        else:
            confessions_cur.execute("INSERT INTO admin_contact values(?, ?)", (hashed_id, int(time.time())))

        # see if they surpass the rate limit (or see if they've never confessed, which makes it easy)

        confessions_db.commit()
        confessions_db.close()

        if (person_is_banned):
            self.sendMessage('-106839678', "Banned user " + hashed_id + " says: \n\n" + toAdmin)
        else:
            self.sendMessage('-106839678', "User " + hashed_id + " says: \n\n" + toAdmin)


        self.sendMessage(chat_id, "Message sent successfully.", reply_to_message_id=msg['message_id'])

    def ban(self, chat_id, msg):

        ban_info = re.match('([A-Fa-f0-9]{64})\s(.*)', msg['text'].replace("/ban@shitholeConfessionsBot ", "").replace("/ban ", ""), re.DOTALL) # ban_info.groups[0] is ID, [1] is $reason

        if (ban_info):

            confessions_db = sqlite3.connect("confessions.db")
            confessions_cur = confessions_db.cursor()

            confessions_cur.execute('CREATE TABLE IF NOT EXISTS banned_people (banned_id_hash TEXT PRIMARY KEY, ban_reason TEXT NOT NULL, unix_timestamp INTEGER NOT NULL)')

            person_already_banned = confessions_cur.execute("SELECT banned_id_hash, ban_reason, unix_timestamp FROM banned_people WHERE banned_id_hash=?", (ban_info.groups()[0], )).fetchone()

            if (person_already_banned):
                self.sendMessage(chat_id, "Error: user already banned.\nBan Reason: " + person_already_banned[1], reply_to_message_id=msg['message_id'])
                return

            confessions_cur.execute("INSERT INTO banned_people values(?, ?, ?)", (ban_info.groups()[0], ban_info.groups()[1], int(time.time())))

            confessions_db.commit()
            confessions_db.close()

            self.sendMessage(chat_id, "User banned successfully.", reply_to_message_id=msg['message_id'])

        else:

            self.sendMessage(chat_id, "Invalid format.\nUsage: /ban [sha-256] [reason]", reply_to_message_id=msg['message_id'])

    def veryBan(self, chat_id, msg): #for people that abuse the contactadmin thing

        ban_info = re.match('([A-Fa-f0-9]{64})\s(.*)', msg['text'].replace("/ban@shitholeConfessionsBot ", "").replace("/ban ", ""), re.DOTALL) # ban_info.groups[0] is ID, [1] is $reason

        if (ban_info):

            confessions_db = sqlite3.connect("confessions.db")
            confessions_cur = confessions_db.cursor()

            confessions_cur.execute('CREATE TABLE IF NOT EXISTS very_banned_people (banned_id_hash TEXT PRIMARY KEY, ban_reason TEXT NOT NULL, unix_timestamp INTEGER NOT NULL)')

            person_already_very_banned = confessions_cur.execute("SELECT banned_id_hash, ban_reason, unix_timestamp FROM very_banned_people WHERE banned_id_hash=?", (ban_info.groups()[0], )).fetchone()

            if (person_already_very_banned):
                self.sendMessage(chat_id, "Error: user already very banned.\nBan Reason: " + person_already_banned[1], reply_to_message_id=msg['message_id'])
                return

            confessions_cur.execute("INSERT INTO very_banned_people values(?, ?, ?)", (ban_info.groups()[0], ban_info.groups()[1], int(time.time())))

            confessions_db.commit()
            confessions_db.close()

            self.sendMessage(chat_id, "User very banned successfully.", reply_to_message_id=msg['message_id'])

        else:

            self.sendMessage(chat_id, "Invalid format.\nUsage: /veryban [sha-256] [reason]", reply_to_message_id=msg['message_id'])

    def unban(self, chat_id, msg):

        id_hash = re.match('([A-Fa-f0-9]{64})', msg['text'].replace("/unban@shitholeConfessionsBot", "").replace("/unban", "").strip()) # ban_info[0] is ID, [1] is $reason

        if (id_hash):

            confessions_db = sqlite3.connect("confessions.db")
            confessions_cur = confessions_db.cursor()

            confessions_cur.execute('CREATE TABLE IF NOT EXISTS banned_people (banned_id_hash TEXT PRIMARY KEY, ban_reason TEXT NOT NULL, unix_timestamp INTEGER NOT NULL)')

            person_is_banned = confessions_cur.execute("SELECT banned_id_hash, ban_reason, unix_timestamp FROM banned_people WHERE banned_id_hash=?", (id_hash.groups()[0], )).fetchone()

            if not (person_is_banned):
                self.sendMessage(chat_id, "Error: user is not banned.", reply_to_message_id=msg['message_id'])
                return

            confessions_cur.execute("DELETE FROM banned_people WHERE banned_id_hash=?", (id_hash.groups()[0],))

            confessions_db.commit()
            confessions_db.close()

            self.sendMessage(chat_id, "User unbanned successfully.", reply_to_message_id=msg['message_id'])

        else:

            self.sendMessage(chat_id, "Invalid format.\nUsage: /unban [sha-256]", reply_to_message_id=msg['message_id'])



    def sauce(self, chat_id, msg):
        path, filename = os.path.split(os.path.realpath(__file__))
        repo = git.Repo(os.path.realpath(path))
        source_status = repo.git.status()

        answer = ""

        if ("modified" in source_status):
            answer = "The remote source is not current with what is being run!\n"

        self.sendMessage(chat_id, answer + "https://github.com/Arcaena/shithole-Confessions-Bot/", reply_to_message_id=msg['message_id'])

    def handle(self, msg):
        content_type, chat_type, chat_id = telepot.glance(msg)

        if (chat_type == "group"):
            print(content_type, chat_type, chat_id)
        else:
            print(content_type, chat_type) # I don't print out the thing in realtime but I will be storing them (temporarily) so that I can find people that abuse the bot and block them from using the bot

        if (content_type == 'text'): #I won't take images, because potential for abuse
            message_words = msg['text'].strip().lower().split()

            if (chat_type == 'private'):

                if (msg['text'][0] != "/"):
                    return
                else:

                    if (message_words[0].replace("/confess@shitholeconfessionsbot", "/confess") == '/confess'):
                        self.confess(chat_id, msg)

                    elif (message_words[0].replace("/contactadmin@shitholeconfessionsbot", "/contactadmin") == '/contactadmin'):
                        self.contactAdmin(chat_id, msg)

                    elif (message_words[0].replace("/help@shitholeconfessionsbot", "/help") == '/help'):
                        self.sendMessage(chat_id, "This bot sends a public, anonymous confession to the [shithole Confessions Channel](https://telegram.me/shithole_confessions) here on Telegram. \n\nTo send a confession in, just do /confess [confession].\n\nThis bot only accepts messages in private, and will not respond in groups.\n\nMessage @HorseySurprise#4274 with any bugs, issues, or suggestions.", reply_to_message_id=msg['message_id'], parse_mode='Markdown')

                    elif (message_words[0].replace("/github@shitholeconfessionsbot", "/github") == '/github'):
                        self.sauce(chat_id, msg)

            elif (chat_type == 'group' and chat_id == -106839678):

                if (message_words[0].replace("/ban@shitholeConfessionsBot", "/ban") == '/ban'):
                    self.ban(chat_id, msg)
                elif (message_words[0].replace("/unban@shitholeConfessionsBot", "/unban") == '/unban'):
                    self.unban(chat_id, msg)



TOKEN = sys.argv[1] # get token from command-line

bot = PandorasBot(TOKEN)
bot.message_loop()
print('Listening ...')

# Keep the program running.
while 1:
    time.sleep(10)
