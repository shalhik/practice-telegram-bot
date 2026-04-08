from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.types import Message
from services import load_events, filter_events, send_notification
router = Router()

@router.message(Command("start"))
async def start(msg: Message):
    await msg.answer("Бот готов! /watch для событий")

@router.message(Command("watch"))
async def start(msg: Message):
    await msg.answer("Бот watch для событий")

@router.message(Command("unwatch"))
async def start(msg: Message):
    await msg.answer("bot not watch")

@router.message(Command("important"))
async def start(msg: Message):
    await msg.answer("imp")

@router.message(Command(f"task {id}"))
async def start(msg: Message):
    await msg.answer(f"task {id}")

@router.message_handler()
async def info(message: Message):
    markup = types.inline_keyboard_markup()
    markup.add(types.inline_keyboard_button('site', url='https://aiogram.dev'))
    markup.add(types.inline_keyboard_button('ahah', callback_data='hi'))
    await message.reply('hello', reply_markup=markup)