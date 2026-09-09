import os
import configparser

config = configparser.ConfigParser()
config.read('bot-settings.cfg')

family = 'soyjak'
mylang = 'en'

usernames['soyjak']['en'] = 'GemBot'

password_file = "user-password.cfg"

user_agent_format = config.get('BotSettings', 'UA_AGENT')

put_throttle = 20
