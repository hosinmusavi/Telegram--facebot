import os
import logging
import cv2
import numpy as np
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# توکن ربات (از متغیر محیطی)
TOKEN = os.environ.get('BOT_TOKEN')

# تنظیمات لاگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ذخیره عکس‌های کاربران
user_photos = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """شروع ربات"""
    user_id = update.effective_user.id
    user_photos[user_id] = []
    
    await update.message.reply_text(
        "🤖 **FaceSwap Bot - نسخه واقعی**\n\n"
        "📸 **نحوه کار:**\n"
        "1. این پیام رو ببین 👇\n"
        "2. عکس اول رو بفرست\n"
        "3. عکس دوم رو بفرست\n"
        "4. عکس جابه‌جا شده رو دریافت کن\n\n"
        "📎 الان **عکس اول** رو بفرست..."
    )

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت و پردازش عکس"""
    user_id = update.effective_user.id
    
    # اگر کاربر جدیده، لیست بساز
    if user_id not in user_photos:
        user_photos[user_id] = []
    
    try:
        # گرفتن عکس با بهترین کیفیت
        photo = update.message.photo[-1]
        file = await photo.get_file()
        
        # دانلود عکس
        await update.message.reply_text("📥 در حال دریافت عکس...")
        photo_bytes = await file.download_as_bytearray()
        
        # تبدیل به OpenCV format
        nparr = np.frombuffer(photo_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        # ذخیره عکس
        user_photos[user_id].append(img)
        
        # بررسی تعداد عکس‌ها
        if len(user_photos[user_id]) == 1:
            await update.message.reply_text(
                "✅ **عکس اول دریافت شد!**\n"
                "📸 حالا **عکس دوم** رو بفرست..."
            )
            
        elif len(user_photos[user_id]) == 2:
            await update.message.reply_text(
                "✅ **هر دو عکس دریافت شدند!**\n"
                "⚡ در حال پردازش FaceSwap...\n"
                "⏳ لطفاً 10-15 ثانیه صبر کن..."
            )
            
            # پردازش FaceSwap
            img1 = user_photos[user_id][0]
            img2 = user_photos[user_id][1]
            result = await process_faceswap(img1, img2)
            
            if result is not None:
                # ارسال عکس نتیجه
                _, buffer = cv2.imencode('.jpg', result)
                photo_bytes = buffer.tobytes()
                
                await update.message.reply_photo(
                    photo=photo_bytes,
                    caption="🎉 **FaceSwap کامل شد!**\n\n"
                           "چهره‌ها با موفقیت جابه‌جا شدند.\n"
                           "برای شروع جدید /start رو بفرست."
                )
            else:
                await update.message.reply_text(
                    "❌ **نتوانستم چهره‌ها رو پردازش کنم!**\n\n"
                    "لطفاً:\n"
                    "• عکس‌های واضح با چهره کامل بفرست\n"
                    "• نور کافی باشد\n"
                    "• چهره مستقیم به دوربین باشد\n\n"
                    "/start رو بفرست تا دوباره شروع کنیم."
                )
            
            # پاک کردن عکس‌های کاربر
            user_photos[user_id] = []
            
        else:
            await update.message.reply_text(
                "⚠️ **بیش از دو عکس فرستادی!**\n"
                "لطفاً /start رو بفرست تا از اول شروع کنیم."
            )
            user_photos[user_id] = []
            
    except Exception as e:
        logger.error(f"خطا: {e}")
        await update.message.reply_text(f"❌ خطا در پردازش: {str(e)[:100]}")
        if user_id in user_photos:
            user_photos[user_id] = []

async def process_faceswap(img1, img2):
    """تابع اصلی پردازش FaceSwap"""
    try:
        # تشخیص چهره با Haar Cascade
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        
        # تبدیل به خاکستری
        gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
        
        # تشخیص چهره‌ها
        faces1 = face_cascade.detectMultiScale(gray1, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
        faces2 = face_cascade.detectMultiScale(gray2, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
        
        if len(faces1) == 0 or len(faces2) == 0:
            logger.warning("چهره‌ای تشخیص داده نشد")
            return None
        
        # بزرگترین چهره را بگیر
        (x1, y1, w1, h1) = max(faces1, key=lambda rect: rect[2] * rect[3])
        (x2, y2, w2, h2) = max(faces2, key=lambda rect: rect[2] * rect[3])
        
        # برش چهره‌ها
        face1 = img1[y1:y1+h1, x1:x1+w1]
        face2 = img2[y2:y2+h2, x2:x2+w2]
        
        # تغییر سایز چهره دوم به اندازه اول
        face2_resized = cv2.resize(face2, (w1, h1))
        
        # ایجاد ماسک بیضی برای ترکیب بهتر
        mask = np.zeros((h1, w1), dtype=np.float32)
        cv2.ellipse(mask, (w1//2, h1//2), (w1//2, h1//2), 0, 0, 360, 1, -1)
        mask = cv2.GaussianBlur(mask, (15, 15), 0)
        mask = mask[:, :, np.newaxis]  # برای broadcast با RGB
        
        # ترکیب چهره‌ها
        result = img1.copy()
        result_face_area = result[y1:y1+h1, x1:x1+w1]
        
        # blend چهره جدید با پس‌زمینه
        blended = result_face_area * (1 - mask) + face2_resized * mask
        result[y1:y1+h1, x1:x1+w1] = blended.astype(np.uint8)
        
        # اضافه کردن متن
        cv2.putText(result, "FaceSwap", (20, 40), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 3)
        cv2.putText(result, "by @hosinmusavi", (20, 80), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2)
        
        return result
        
    except Exception as e:
        logger.error(f"خطا در پردازش: {e}")
        return None

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """راهنما"""
    help_text = """
🤖 **FaceSwap Bot - راهنما**

📸 **دستورات:**
/start - شروع کار جدید
/help - نمایش این راهنما

🔄 **نحوه کار:**
1. /start رو بفرست
2. **عکس اول** (با چهره واضح)
3. **عکس دوم** (با چهره واضح)
4. منتظر **عکس نتیجه** باش

⚠️ **نکات مهم:**
• هر عکس باید **یک چهره واضح** داشته باشد
• **نور** کافی باشد
• چهره **مستقیم** به دوربین باشد
• برای شروع جدید /start رو بفرست

⏱️ **زمان پردازش:** 10-20 ثانیه
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')

def main():
    """تابع اصلی"""
    # ساخت اپلیکیشن
    application = Application.builder().token(TOKEN).build()
    
    # اضافه کردن دستورات
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    
    # شروع ربات
    logger.info("🚀 FaceSwap Bot شروع به کار کرد...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
