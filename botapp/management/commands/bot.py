import django
from django.core.management.base import BaseCommand
from django.conf import settings
import os
import logging
from ...models import BotUser, Movie, Video
from aiogram import html
from aiogram import Bot, Dispatcher, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters import Command as SM
from aiogram import Router
from aiogram import F
from aiogram.enums import ParseMode
from aiogram.types import FSInputFile
from aiogram.types import InputFile
import asyncio
import yt_dlp
from bs4 import BeautifulSoup
import requests
import re
from asgiref.sync import sync_to_async
from pathlib import Path

# output_folder = r'C:\Users\Maks\PycharmProjects\pythonProject2\FinallProject\RemoteAccess\temp_audio'
folder_path = Path.home() / "temp_audio"
folder_path.mkdir(parents=True, exist_ok=True)
output_folder = folder_path

#збереження юзера і функції для роботи з БД

logging.basicConfig(level=logging.INFO)
bot = Bot(token=settings.TELEGRAM_BOT_API_KEY)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()

class Command(BaseCommand):
    help = 'Запускає Telegram-бота'

    def handle(self, *args, **kwargs):
        logging.info('Starting bot...')
        asyncio.run(main())

    async def start_bot(self):
        dp.include_router(router)
        await dp.start_polling(bot)

class Form(StatesGroup):
    auth = State()
    action = State()
    search_query = State()

def save_user(user):
    user.save()

def password_set(user, password):
    user.set_password(password)
    user.save()

def chek_password(user, password):
    return user.check_password(password)

def save_movies(user, movie):
    user.favorite_movies.add(movie)

def save_videos(user, video):
    user.favorite_videos.add(video)

#Авторизація користувача і початок роботи

@router.message(SM('start'))
async def start_bot(message: types.Message, state: FSMContext):

    telegram_id = message.from_user.id
    user, created = await sync_to_async(BotUser.objects.get_or_create, thread_sensitive=True)(telegram_id=telegram_id, defaults={
        'username': message.from_user.username,
        'full_name': message.from_user.full_name})

    if user.is_authenticated:
        await message.answer(f'Привіт, {html.bold(html.quote(message.from_user.full_name))}', parse_mode=ParseMode.HTML)
        await show_main_menu(message)

    else:
        await state.set_state(Form.auth)
        del_message = await message.answer("Введіть пароль для доступу:")
        message_id = del_message.message_id
        await asyncio.sleep(2)




@router.message(Form.auth)
async def process_bot(message: types.Message, state: FSMContext):
    user, created = await sync_to_async(BotUser.objects.get_or_create, thread_sensitive=True)(telegram_id=message.from_user.id)
    if not created:
        await sync_to_async(password_set)(user, message.text)
    if await sync_to_async(chek_password)(user, message.text):
        print(user)
        user.is_authorized = True
        await sync_to_async(save_user)(user)

        await state.clear()
        await message.delete()
        await message.answer(f'Привіт, {html.bold(html.quote(message.from_user.full_name))}', parse_mode=ParseMode.HTML)
        await show_main_menu(message)
    else:
        await message.answer("Неправильний пароль. Спробуйте ще раз.")



async def show_main_menu(message: types.Message):
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text='HdRezka', callback_data='films')
    keyboard.button(text='YouTube', callback_data='youtube')
    keyboard.button(text='Music', callback_data='music')
    keyboard.button(text='Улюблене', callback_data='favorite')
    keyboard.button(text='Exit', callback_data='exit')
    keyboard.adjust(1)
    await message.answer('Вибери опцію:', reply_markup=keyboard.as_markup())

#обробка колбеків основних

@router.callback_query(F.data == 'music')
async def process_music(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await callback.message.answer('Введи назву пісні:')
    await state.set_state(Form.search_query)
    await state.update_data(action='music')

@router.callback_query(F.data == 'films')
async def process_films(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await callback.message.answer('Введи назву фільму:')
    await state.set_state(Form.search_query)
    await state.update_data(action='hdrezka')

@router.callback_query(F.data == 'youtube')
async def process_youtube(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await callback.message.answer('Яке відео знайти?:')
    await state.set_state(Form.search_query)
    await state.update_data(action='youtube')

#процес пошуку і виклик функцій для пошуку

@router.message(Form.search_query)
async def process_search(message: types.Message, state: FSMContext):

    search_text = message.text
    await asyncio.sleep(1.5)
    await message.delete()
    data = await state.get_data()
    action = data.get('action')

    if action == 'hdrezka':

        links = hd_rezka_search(search_text)

        name = 'https://hdrezka.ag/'

        if links:
            await message.answer(f'Шукаю фільм: {search_text}')

            for link in links:
                url = name + link
                keyboard = InlineKeyboardBuilder()
                keyboard.button(text='Перегляд на PC', callback_data=f'open_hdrezka:{link}')
                keyboard.button(text='Перегляд на телефоні', url=url)
                keyboard.button(text='Додати в "Улюблене"', callback_data=f'save_movie:{link}')
                keyboard.adjust(1, 1)
                await message.answer(url, reply_markup=keyboard.as_markup())

        else:
            await message.answer('Нічого не знайдено, спробуйте ще раз.')

        await asyncio.sleep(2)
        await show_main_menu(message)

    elif action == 'youtube':
        links = youtube_search(search_text)

        if links:
            await message.answer(f'Знайдено результати за запитом "{search_text}":')

            for link in links:
                keyboard = InlineKeyboardBuilder()
                keyboard.button(text='Запустити на компʼютері', callback_data=f'open_youtube:{link}')
                keyboard.button(text='Запустити на телефоні', url=link)
                keyboard.button(text='Додати в "Улюблене"', callback_data=f'save_video:{link}')
                keyboard.adjust(1, 1)
                await message.answer(link, reply_markup=keyboard.as_markup())

        else:
            await message.answer("Нічого не знайдено, спробуйте ще раз.")

        await asyncio.sleep(2)
        await show_main_menu(message)

    elif action == 'music':
        title = search_music(search_text)
        if title:
            for name in title:
                keyboard = InlineKeyboardBuilder()
                keyboard.button(text='Download', callback_data=f'download:{name}')
                keyboard.adjust(1, 1)
                await message.answer(name , reply_markup=keyboard.as_markup())
        else:
            await message.answer("Нічого не знайдено, спробуйте ще раз.")

        await asyncio.sleep(2)
        await show_main_menu(message)

    await state.clear()

#пошук відео і фільмів

def hd_rezka_search(query):
    url_hd_rezka = f'https://hdrezka.ag/search/?do=search&subaction=search&q={query.replace(" ", "+")}'

    headers = {
        'user-agent': 'Mozilla / 5.0(Windows NT 10.0;Win64;x64) AppleWebKit / 537.36(KHTML, likeGecko) Chrome / 128.0.0.0Safari / 537.36OPR / 114.0.0.0',}
    r = requests.get(url_hd_rezka, headers=headers)
    data = r.text
    soup = BeautifulSoup(data, 'lxml')
    films = soup.findAll('div', class_='b-content__inline_item-link')
    links = []

    for urls in films:
        a = urls.find('a', href=True).get('href')
        last_part = a.split('/')[-1]
        links.append(last_part)

    return links[:5]

def youtube_search(query):
    url_youtube = f'https://www.youtube.com/results?search_query={query.replace(" ", "+")}'

    headers = {
        'user-agent': 'Mozilla / 5.0(Windows NT 10.0;Win64;x64) AppleWebKit / 537.36(KHTML, likeGecko) Chrome / 128.0.0.0Safari / 537.36OPR / 114.0.0.0',}

    r = requests.get(url_youtube, headers=headers)
    send = BeautifulSoup(r.text, 'html.parser')
    search = send.findAll('script')
    key = '"videoId":"'
    data = re.findall(key + r'([^"]{11})', str(search))
    links = []
    seen_links = set()
    name = 'https://www.youtube.com/watch?v='

    for i in data:
        link = name + i
        if link not in seen_links:
            links.append(link)
            seen_links.add(link)

    return links[:5]


#обробка колбеків для відкриття посилань

@router.callback_query(F.data.startswith('download:'))
async def load_m(callback: CallbackQuery):
    await callback.message.delete()
    link = callback.data.split(':', 1)[1].strip()
    print(link)
    await callback.message.answer('Зачекайте...')
    file_path = os.path.join(output_folder, f"{link}.mp3")
    if os.path.exists(file_path):
        audio = FSInputFile(file_path)
        await callback.bot.send_audio(chat_id=callback.message.chat.id, audio=audio, caption="Ось ваше аудіо 🎵")
        await show_main_menu(callback.message)
    elif not os.path.exists(file_path):
        await callback.message.answer('Ще виконую пошук...')
        muz_download(link)
        if os.path.exists(file_path):
            audio = FSInputFile(file_path)
            await callback.bot.send_audio(chat_id=callback.message.chat.id, audio=audio, caption="Ось ваше аудіо 🎵")
            await show_main_menu(callback.message)
    else:
        await callback.message.answer("Файл не знайдено.")
        await show_main_menu(callback.message)

@router.callback_query(F.data.startswith('open_youtube:'))
async def open_on_PC(callback: CallbackQuery):
    link = callback.data.split(':', 1)[1].strip()
    print(link)
    await callback.message.answer(f"Відкриваю на комп'ютері: {link}")
    os.system(f'start Opera "{link}"')


@router.callback_query(F.data.startswith('open_hdrezka:'))
async def open_film(callback: CallbackQuery):
    link = callback.data.split(':', 1)[1].strip()
    name = 'https://hdrezka.ag/'
    print(link)
    full_url = name + link
    await callback.message.answer(f"Відкриваю на комп'ютері")
    os.system(f'start Opera "{full_url}"')

#процес збереження в 'Улюблене'

@router.callback_query(F.data == 'favorite')
async def show_favorite(callback: CallbackQuery):
    await callback.message.delete()
    user = await sync_to_async(BotUser.objects.get)(telegram_id=callback.from_user.id)
    favorite_mov = await sync_to_async(list)(user.favorite_movies.all())
    favorite_youtube = await sync_to_async(list)(user.favorite_videos.all())

    if len(favorite_mov) == 0 and len(favorite_youtube) > 0:

        await callback.message.answer("Ваші улюблені фільми:")
        await callback.message.answer("Тут покищо порожньо.")
        await asyncio.sleep(2)
        await callback.message.answer("Ваші улюблені відео:")
        for video in favorite_youtube:
            keyboard = InlineKeyboardBuilder()
            keyboard.button(text='Видалити', callback_data=f'delete_video:{video.id}')
            await callback.message.answer(video.url, reply_markup=keyboard.as_markup())

    elif len(favorite_mov) > 0 and len(favorite_youtube) == 0:

        await callback.message.answer("Ваші улюблені фільми:")
        for link in favorite_mov:
            keyboard = InlineKeyboardBuilder()
            keyboard.button(text='Видалити', callback_data=f'delete_movie:{link.id}')
            keyboard.adjust(1, 1)
            await callback.message.answer(f'"{link.title}":{link.url}', reply_markup=keyboard.as_markup())
        await asyncio.sleep(2)
        await callback.message.answer("Ваші улюблені відео: ")
        await callback.message.answer("Тут покищо порожньо.")

    elif len(favorite_youtube) == 0 and len(favorite_mov) == 0:

        await callback.message.answer('Тут ще немає збережених фільмів та відео.')

    else:
        await callback.message.answer("Ваші улюблені фільми:")
        for link in favorite_mov:
            keyboard = InlineKeyboardBuilder()
            keyboard.button(text='Видалити', callback_data=f'delete_movie:{link.id}')
            keyboard.adjust(1, 1)
            await callback.message.answer(f'"{link.title}":{link.url}', reply_markup=keyboard.as_markup())
        await asyncio.sleep(2)
        await callback.message.answer("Ваші улюблені відео:")
        for video in favorite_youtube:
            keyboard = InlineKeyboardBuilder()
            keyboard.button(text='Видалити', callback_data=f'delete_video:{video.id}')
            await callback.message.answer(video.url, reply_markup=keyboard.as_markup())

    await asyncio.sleep(2)
    await show_main_menu(callback.message)

#збереження пошуку

@router.callback_query(F.data.startswith('save_video:'))
async def save_video(callback: CallbackQuery):
    link = callback.data.split(':', 1)[1].strip()
    print(link)
    video, created = await sync_to_async(Video.objects.get_or_create)(url=link)
    user = await sync_to_async(BotUser.objects.get)(telegram_id=callback.from_user.id)
    await sync_to_async(save_videos)(user, video)
    await callback.message.answer('Відео додано!')

#saved hdrezka search

@router.callback_query(F.data.startswith('save_movie:'))
async def save_movie(callback: CallbackQuery):
    link = callback.data.split(':', 1)[1].strip()
    name = 'https://hdrezka.ag/'
    full_url = name + link

    headers = {
        'user-agent': 'Mozilla / 5.0(Windows NT 10.0;Win64;x64) AppleWebKit / 537.36(KHTML, likeGecko) Chrome / 128.0.0.0Safari / 537.36OPR / 114.0.0.0',}

    r = requests.get(full_url, headers=headers)
    data = r.text
    soup = BeautifulSoup(data, 'lxml')
    title = soup.h1.text.strip()
    movie, created = await sync_to_async(Movie.objects.get_or_create)(url=full_url, defaults={'title': title})
    user = await sync_to_async(BotUser.objects.get)(telegram_id=callback.from_user.id)
    await sync_to_async(save_movies)(user, movie)
    await callback.message.answer('Фільм додано!')

#видалення з улюбленого

@router.callback_query(F.data.startswith('delete_video:'))
async def delete_favorite_video(callback: CallbackQuery):
    await callback.message.delete()
    video_id = callback.data.split(':')[1]
    user = await sync_to_async(BotUser.objects.get)(telegram_id=callback.from_user.id)
    video = await sync_to_async(Video.objects.get)(id=video_id)
    await sync_to_async(user.favorite_videos.remove)(video)
    await callback.message.answer("Відео видалено з улюблених!")

@router.callback_query(F.data.startswith('delete_movie:'))
async def delete_favorite_movie(callback: CallbackQuery):
    await callback.message.delete()
    movie_id = callback.data.split(':')[1]
    print(movie_id)
    user = await sync_to_async(BotUser.objects.get)(telegram_id=callback.from_user.id)
    movie = await sync_to_async(Movie.objects.get)(id=movie_id)
    await sync_to_async(user.favorite_movies.remove)(movie)
    await callback.message.answer("Фільм видалено з улюблених!")

#search music

def search_music(query):
    search_url = f"ytsearch5:{query}"

    ydl_opts = {
        'quiet': True,
        'extract_flat': 'in_playlist',  # Отримує лише метадані відео, без завантаження
    }

    titles = []

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            search_results = ydl.extract_info(search_url, download=False)

            for entry in search_results['entries']:
                video_info = entry.get('title')
                    # "url": f"https://www.youtube.com/watch?v={entry.get('id')}"
                titles.append(video_info)

        except Exception as e:
            print("Помилка при пошуку:", e)

    return truncate_text_to_word(titles)

def truncate_text_to_word(results, max_length=30):
    res = []
    for result in results:
        if len(result) <= max_length:
            res.append(result)
        else:
            truncated = result[:max_length].rsplit(' ', 1)[0]  # Обрізає до останнього цілого слова
            res.append(truncated)
    return res

def muz_download(search_query):
    search_url = f"ytsearch:{search_query}"
    ydl_opts = {
        'format': 'bestaudio/best',  # вибір найкращої якості аудіо
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',  # обираємо формат mp3
            'preferredquality': '320',  # встановлюємо якість аудіо
        }],
        'outtmpl': os.path.join(output_folder, f'{search_query}.%(ext)s'),
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([search_url])

#завершення роботи

@router.callback_query(F.data == 'exit')
async def process_exit(callback: CallbackQuery):
    await callback.message.delete()
    user, created = await sync_to_async(BotUser.objects.get_or_create, thread_sensitive=True)(telegram_id=callback.from_user.id)
    user.is_authorized = False
    await sync_to_async(save_user)(user)
    await callback.message.answer("Сесію завершено. Дякую за користування ботом!")



async def main():
    dp.include_router(router)
    await dp.start_polling(bot)