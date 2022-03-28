import telebot

"""
Create a telegram bot that will allow our user to get information from their positions
"""

bot_name = 'novalabs_trading_bot'

token_bot = '5285099180:AAENzEt3cji9V2eIMXlyv0P3hz9EzalGJMQ'
bot = telebot.TeleBot(token_bot)

@bot.message_handler(commands=['Greet'])
def greet(message):
    bot.send_message(message.chat.id, "Hey! Hows it going?")

bot.polling()


