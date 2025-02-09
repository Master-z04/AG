import logging
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes
)

import os

# دریافت توکن ربات از متغیر محیطی
TOKEN = os.getenv('BOT_TOKEN')

if TOKEN:
    print("توکن ربات دریافت شد!")
else:
    print("توکن ربات یافت نشد! لطفاً متغیر محیطی را تنظیم کنید.")

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# دیکشنری برای نگه‌داشتن اطلاعات پست‌هایی که در کانال ساخته میشن (سناریوی قبلی)
# key = post_id (str), value = (channel_id, message_id)
POSTS_DATA = {}

# دیکشنری برای نگه داشتن کد اختصاصی هر کاربر در "ثبت پست"
# key = user_id, value = user_code
USER_CODES = {}

# اگر خواستید تمام نظرات به یک کانال خاص برود، آیدی عددی آن را اینجا بگذارید
CHANNEL_ID = -5611709234  # مثال. در صورت نیاز تغییر بدید.


# تابعی ساده برای تولید یک کد تصادفی
def generate_post_id():
    from random import randint
    return str(randint(100000, 999999))


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    این تابع وقتی فراخوانی میشه که کاربر /start رو بدون پارامتر (deep link) بفرسته.
    ما یک خوش آمد میگیم و بعد منوی اصلی رو نشون میدیم.
    """
    # پیام خوش آمد اول
    await update.message.reply_text(
        "سلام داداش خوش اومدی! اینجا میتونی نظر ناشناس بدی یا پست ثبت کنی."
    )
    # پیام دوم با منوی شیشه‌ای
    main_menu_keyboard = [
        [InlineKeyboardButton("ثبت پست", callback_data="make_post")],
        [InlineKeyboardButton("پیام های من", callback_data="my_messages")],
        [InlineKeyboardButton("پروفایل من", callback_data="my_profile")],
        [InlineKeyboardButton("پشتیبانی ربات", callback_data="support")],
        [InlineKeyboardButton("درباره ما", callback_data="about")]
    ]
    reply_markup = InlineKeyboardMarkup(main_menu_keyboard)
    await update.message.reply_text(
        "از منوی زیر یکی رو انتخاب کن:",
        reply_markup=reply_markup
    )


async def start_with_param(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    این تابع زمانی صدا زده میشه که کاربر با پارامتر وارد بشه (لینک deep link).
    مثلا t.me/YourBot?start=123456
    ممکنه این 123456 مربوط به پست کانال باشه (POSTS_DATA)
    یا مربوط به کد اختصاصی کاربر (USER_CODES).
    """
    if not update.message:
        return

    args = context.args  # لیست پارامترها
    if not args:
        await update.message.reply_text(
            "پارامتر لازم رو نفرستادی یا لینک رو درست کلیک نکردی."
        )
        return

    post_id_or_code = args[0]
    # 1) اگه این کد در POSTS_DATA باشه، یعنی مربوط به پست کانال هست
    if post_id_or_code in POSTS_DATA:
        # سناریوی قبلی: کاربر میخواد ناشناس جواب پست کانال رو بده
        context.user_data["active_post_id"] = post_id_or_code
        await update.message.reply_text(
            "شما داری درمورد یه پست کانالی نظر میدی. پیامت رو بفرست تا ناشناس بره."
        )
        return

    # 2) اگه این کد در USER_CODES باشه، یعنی مربوط به کد اختصاصی کاربر
    # در این سناریو، هر کسی این کد رو داشته باشه میتونه ناشناس پیام بده به اون کاربر (یا کانال).
    # بسته به مدل استفاده شما، میتونید پیام رو به خود کاربر بفرستید یا جایی دیگه.
    # اینجا نمونه ساده: پیام های ناشناس برای همونCHANNEL_ID ارسال میشن
    found_user_id = None
    for uid, ucode in USER_CODES.items():
        if ucode == post_id_or_code:
            found_user_id = uid
            break

    if found_user_id is not None:
        # یعنی لینک مربوط به کد یه کاربره. حالا هر کسی روی این لینک کلیک کنه میتونه ناشناس براش پیام بده
        context.user_data["active_user_code"] = post_id_or_code
        # مثلا میگیم: "اوکی! پیامت رو بفرست تا ناشناس بره."
        await update.message.reply_text(
            "این لینک مخصوص ارسال پیام ناشناس به صاحب این کد هست. هرچی میخوای بگو."
        )
        return

    # اگر هیچ کدوم نبود، یعنی پارامتر نامعتبره
    await update.message.reply_text("کد یا شناسه نامعتبره.")


async def callback_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    این تابع تمام دکمه های شیشه ای منوی اصلی رو مدیریت میکنه.
    """
    query = update.callback_query
    data = query.data

    # حتما callback رو تایید کن که ربات هنگ نکنه
    await query.answer()

    if data == "make_post":
        # ثبت پست: باید برای کاربر یه کد منحصر به فرد بسازیم
        user_id = query.from_user.id
        if user_id in USER_CODES:
            code = USER_CODES[user_id]
        else:
            code = generate_post_id()
            USER_CODES[user_id] = code

        # لینکی برای ارسال پاسخ ناشناس: هرکی روی این لینک کلیک کنه،
        # میتونه ناشناس پیام بده که در نهایت میره به کانال شما (یا جای دیگه)
        bot_username = context.bot.username
        deep_link = f"https://t.me/{bot_username}?start={code}"

        text = (
            "دمت گرم! این لینک اختصاصی توئه. اگه کسی روش کلیک کنه میتونه ناشناس برات پیام بذاره.\n"
            "لینک: " + deep_link + "\n\n"
            "فعلا هر پیامی که اینجا بنویسی، به کانال ارسال میشه با کد اختصاصی تو."
        )
        await query.message.reply_text(text)

    elif data == "my_messages":
        # اینجا میتونید لیست پیام های کاربر رو از دیتابیس بگیرید یا هرچی
        await query.message.reply_text("فعلا لیست پیام هات خالیه یا این بخش پیاده سازی نشده!")
    elif data == "my_profile":
        user = query.from_user
        await query.message.reply_text(
            f"این بخش پروفایلته:\n"
            f"اسم: {user.first_name} {user.last_name or ''}\n"
            f"یوزرنیم: @{user.username or 'نداری'}\n"
            f"آیدی عددی: {user.id}"
        )
    elif data == "support":
        await query.message.reply_text("اگه باگی یا مشکلی هست، به آی دی @YourSupport پیام بده.")
    elif data == "about":
        await query.message.reply_text("این ربات توسط فلانی ساخته شده برای دریافت نظرات ناشناس. سپاس از استفاده شما!")


async def publish_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    دستور /publish مربوط به سناریوی پست کانال.
    ادمین با /publish + متن پست رو میفرسته، ربات پست رو در همون کانال میسازه
    با یه دکمه مخصوص ارسال ناشناس (deep link).
    """
    if not update.message:
        return

    text_for_post = update.message.text.replace("/publish", "").strip()
    if not text_for_post:
        text_for_post = "چیزی ننوشتی؟!"

    post_id = generate_post_id()
    bot_username = context.bot.username
    deep_link = f"https://t.me/{bot_username}?start={post_id}"

    message_text = (
        f"{text_for_post}\n\n"
        "برای ارسال نظر ناشناس در مورد این پست، روی دکمه زیر کلیک کن."
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("ارسال ناشناس", url=deep_link)]
    ])

    sent_message = await update.message.reply_text(
        message_text,
        reply_markup=keyboard
    )

    channel_id = sent_message.chat_id
    message_id = sent_message.message_id
    POSTS_DATA[post_id] = (channel_id, message_id)

    logger.info(f"New post created. ID={post_id}, channel_id={channel_id}, message_id={message_id}")


async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    هر پیام متنی که دستور یا چیز دیگه نباشه میاد اینجا.
    ممکنه کاربر در حال پاسخ به:
      1) پست کانالی (active_post_id)
      2) لینک اختصاصی کاربر (active_user_code)
    باشه.
    """
    if not update.message:
        return

    user_text = update.message.text
    user_id = update.effective_user.id

    # 1) چک میکنیم شاید کاربر داره به پست کانال پاسخ میده
    post_id = context.user_data.get("active_post_id")
    if post_id and post_id in POSTS_DATA:
        channel_id, original_msg_id = POSTS_DATA[post_id]

        feedback_text = (
            f"یه پیام ناشناس برای پست #{post_id}:\n\n"
            f"{user_text}"
        )
        # ارسال پیام به کانال
        await context.bot.send_message(chat_id=channel_id, text=feedback_text)
        await update.message.reply_text("پیامت ناشناس ارسال شد به کانال!")
        return

    # 2) اگه کاربر کد اختصاصی داره (make_post)، هر پیامی که بده میره کانال
    #   یا ممکنه کاربر با لینک deep link مربوط به یه user_code وارد شده باشه
    user_code = None

    # حالت: کاربر خودش صاحب کد باشه
    if user_id in USER_CODES:
        user_code = USER_CODES[user_id]

    # حالت: کاربر وارد لینک deep link یه نفر دیگه شده
    if "active_user_code" in context.user_data:
        user_code = context.user_data["active_user_code"]

    if user_code:
        # داریم یه پیام ناشناس برای این user_code میفرستیم به کانال
        feedback_text = (
            f"یه پیام ناشناس برای کد {user_code}:\n"
            f"{user_text}"
        )
        await context.bot.send_message(chat_id=CHANNEL_ID, text=feedback_text)
        await update.message.reply_text("پیامت به صورت ناشناس ارسال شد!")
        return

    # اگر هیچ کدوم نبودن
    await update.message.reply_text(
        "فعلا معلوم نیست میخوای چیکار کنی! از منوی اصلی استفاده کن یا با لینک مناسب وارد شو."
    )


async def start_no_param(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    هندلر کمکی برای متمایز کردن start بدون پارامتر از start_with_param.
    برای این که proper Regex یا فیلترها رو تنظیم کنیم.
    """
    # اگر قطعاً هیچ آرگومانی نیست، میریم به start_command
    await start_command(update, context)


async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """اگه یه دستور ناشناخته وارد بشه."""
    if update.message:
        await update.message.reply_text("داداش چنین دستوری نداریم!")


def main():
    app = ApplicationBuilder().token(TOKEN).build()

    # /start بدون پارامتر
    app.add_handler(CommandHandler("start", start_no_param, filters=filters.Regex(r"^/start$")))
    # /start با پارامتر
    app.add_handler(CommandHandler("start", start_with_param))

    # هندلر دکمه های منوی اصلی
    app.add_handler(CallbackQueryHandler(callback_query_handler))

    # دستور /publish برای سناریوی پست کانال
    app.add_handler(CommandHandler("publish", publish_command))

    # پیام های متنی عادی
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    # دستورات ناشناخته
    app.add_handler(MessageHandler(filters.COMMAND, unknown_command))

    app.run_polling()


if __name__ == "__main__":
    main()
