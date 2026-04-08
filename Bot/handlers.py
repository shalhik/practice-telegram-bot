from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.types import Message
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from services import *

router = Router()

@router.message(Command("start"))
async def start(msg: Message):
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='site', url='https://aiogram.dev')],
        [InlineKeyboardButton(text='ahah', callback_data='hi')]
    ])
    await msg.answer("Бот готов! /watch для событий", reply_markup=markup)
@router.callback_query()

@router.message(Command("connect"))
async def connect(msg: Message):
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='Space', callback_data='spacing')],
        [InlineKeyboardButton(text='Folder', callback_data='folding')],        
        [InlineKeyboardButton(text='List', callback_data='listing')]
    ])
    await msg.answer("Бот /watch для событий")


@router.callback_query(F.data == "spacing")
async def process_hi(callback: CallbackQuery):
    await change_to_list(callback)

@router.callback_query(F.data == "folding")
async def processing(callback: CallbackQuery):
    await change_to_folder(callback)

@router.callback_query(F.data == "listing")
async def processsz(callback: CallbackQuery):
    await change_to_list(callback)


@router.message(Command("watch"))
async def watch(msg: Message):
    await msg.answer("Бот watch для событий")

@router.message(Command("unwatch"))
async def unwatch(msg: Message):
    await msg.answer("bot not watch")

@router.message(Command("important"))
async def important(msg: Message):
    await msg.answer("imp")

@router.message(Command("task"))
async def cmd_task(msg: Message):
    parts = msg.text.split()
    task_id = parts[1] if len(parts) > 1 else "no id"
    await msg.answer(f"task {task_id}")
