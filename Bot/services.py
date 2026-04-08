import json
from config import JSON_PATH

def load_events():
    pass

def filter_events():
    pass

def send_notification(bot, chat_id, event):
    pass

async def change_to_list(callback):
    await callback.message.answer("Привет")
    await callback.answer()

async def change_to_folder(callback):
    await callback.message.answer("Привет")
    await callback.answer()
    
async def change_to_space(callback):
    await callback.message.answer("Привет")
    await callback.answer()