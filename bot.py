#!/usr/bin/env python3
import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# توکن ربات (از محیط می‌گیریم)
TOKEN = os.environ.get('BOT_TOKEN', 'YOUR_TOKEN_HERE')

# تنظیمات لاگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# دستور /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"👋 سلام {user.first_name}!\n"
        "🤖 من ربات FaceSwap هستم\n"
        "📸 یک عکس با چهره بفرست تا جایشو عوض کنم!"
    )

# دستور /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
🎭 **دستورات ربات:**
/start - شروع کار با ربات
/help - نمایش این راهنما

📸 **نحوه استفاده:**
۱. یک عکس با چهره واضح بفرست
۲. منتظر پردازش باش
۳. نتیجه رو دریافت کن

⚠️ **نسخه نمایشی**
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')

# دریافت عکس
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.reply_text("📥 در حال دریافت عکس...")
        
        # گرفتن بهترین کیفیت عکس
        photo = update.message.photo[-1]
        file = await photo.get_file()
        
        await update.message.reply_text("✅ عکس دریافت شد!\n⚡ در حال پردازش...")
        
        # شبیه‌سازی پردازش
        import time
        time.sleep(2)
        
        await update.message.reply_text(
            "🎉 **پردازش کامل شد!**\n\n"
            "این نسخه نمایشی است. در نسخه کامل:\n"
            "• چهره‌ها تشخیص داده می‌شوند\n"
            "• جای چهره‌ها عوض می‌شود\n"
            "• عکس جدید برایت ارسال می‌شود"
        )
        
    except Exception as e:
        logger.error(f"خطا: {e}")
        await update.message.reply_text(f"❌ خطا در پردازش: {str(e)}")

# تابع اصلی
def main():
    # ساخت اپلیکیشن
    application = Application.builder().token(TOKEN).build()
    
    # اضافه کردن handlerها
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    
    # شروع ربات
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
