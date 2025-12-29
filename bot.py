import os
import logging
import cv2
import numpy as np
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import dlib
from PIL import Image
import io

# توکن از محیط می‌گیره
TOKEN = os.environ.get('BOT_TOKEN')

# تنظیمات لاگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# بارگیری مدل تشخیص چهره (dlib)
detector = dlib.get_frontal_face_detector()
predictor = dlib.shape_predictor("shape_predictor_68_face_landmarks.dat")  # نیاز به دانلود فایل

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 **FaceSwap Bot**\n\n"
        "📸 **دو تا عکس بفرست:**\n"
        "۱. عکس شخص اول\n"
        "۲. عکس شخص دوم\n\n"
        "سپس جای چهره‌ها رو عوض می‌کنم!"
    )

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        
        # ایجاد پوشه برای کاربر اگر وجود ندارد
        user_folder = f"user_{user_id}"
        os.makedirs(user_folder, exist_ok=True)
        
        # دریافت عکس
        photo = update.message.photo[-1]
        file = await photo.get_file()
        
        # دانلود عکس
        photo_bytes = await file.download_as_bytearray()
        nparr = np.frombuffer(photo_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        # ذخیره عکس
        photo_count = len([f for f in os.listdir(user_folder) if f.endswith('.jpg')])
        photo_path = f"{user_folder}/photo_{photo_count + 1}.jpg"
        cv2.imwrite(photo_path, img)
        
        # بررسی تعداد عکس‌های دریافت شده
        photos = [f for f in os.listdir(user_folder) if f.endswith('.jpg')]
        
        if len(photos) == 1:
            await update.message.reply_text(
                "✅ عکس اول دریافت شد!\n"
                "📸 حالا عکس دوم رو بفرست."
            )
        elif len(photos) == 2:
            await update.message.reply_text(
                "✅ هر دو عکس دریافت شدند!\n"
                "⚡ در حال پردازش FaceSwap..."
            )
            
            # پردازش FaceSwap
            result = await process_faceswap(user_folder)
            
            if result:
                # ارسال عکس نتیجه
                with open(result, 'rb') as photo_file:
                    await update.message.reply_photo(
                        photo=photo_file,
                        caption="🎉 **FaceSwap کامل شد!**\n\n"
                                "چهره‌ها با موفقیت جابه‌جا شدند."
                    )
                
                # پاک کردن فایل‌های موقت
                for file in os.listdir(user_folder):
                    os.remove(f"{user_folder}/{file}")
                os.rmdir(user_folder)
            else:
                await update.message.reply_text(
                    "❌ در پردازش مشکلی پیش آمد.\n"
                    "مطمئن شوید عکس‌ها چهره واضح دارند."
                )
        else:
            await update.message.reply_text(
                "⚠️ بیشتر از دو عکس دریافت کردی.\n"
                "دوباره از اول شروع می‌کنم..."
            )
            # پاک کردن پوشه قدیمی
            for file in os.listdir(user_folder):
                os.remove(f"{user_folder}/{file}")
            
    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text(f"❌ خطا: {str(e)}")

async def process_faceswap(user_folder):
    """پردازش FaceSwap واقعی"""
    try:
        # خواندن دو عکس
        photos = sorted([f for f in os.listdir(user_folder) if f.endswith('.jpg')])
        
        if len(photos) < 2:
            return None
        
        img1 = cv2.imread(f"{user_folder}/{photos[0]}")
        img2 = cv2.imread(f"{user_folder}/{photos[1]}")
        
        # تشخیص چهره‌ها
        faces1 = detector(img1)
        faces2 = detector(img2)
        
        if len(faces1) == 0 or len(faces2) == 0:
            return None
        
        # ساده‌ترین روش: crop و جایگزینی
        # (این نسخه ساده‌ست، نسخه کامل نیاز به تکنیک‌های پیشرفته‌تر داره)
        
        # گرفتن اولین چهره از هر عکس
        face1 = faces1[0]
        face2 = faces2[0]
        
        # برش چهره‌ها
        x1, y1, w1, h1 = face1.left(), face1.top(), face1.width(), face1.height()
        x2, y2, w2, h2 = face2.left(), face2.top(), face2.width(), face2.height()
        
        # resize چهره دوم به اندازه اول
        face2_resized = cv2.resize(img2[y2:y2+h2, x2:x2+w2], (w1, h1))
        
        # جایگزینی
        result = img1.copy()
        result[y1:y1+h1, x1:x1+w1] = face2_resized
        
        # ذخیره نتیجه
        output_path = f"{user_folder}/result.jpg"
        cv2.imwrite(output_path, result)
        
        return output_path
        
    except Exception as e:
        logger.error(f"FaceSwap error: {e}")
        return None

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
🎭 **دستورات:**
/start - شروع کار
/help - راهنما
/swap - شروع FaceSwap جدید

📸 **نحوه کار:**
۱. دستور /swap رو بفرست
۲. دو عکس با چهره واضح بفرست
۳. منتظر نتیجه باش

⚠️ **نیازها:**
• هر عکس باید حداقل یک چهره واضح داشته باشد
• نور کافی باشد
• چهره مستقیم به دوربین باشد
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def swap_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_folder = f"user_{user_id}"
    
    # پاک کردن پوشه قدیمی
    if os.path.exists(user_folder):
        for file in os.listdir(user_folder):
            os.remove(f"{user_folder}/{file}")
        os.rmdir(user_folder)
    
    await update.message.reply_text(
        "🔄 **آماده برای FaceSwap جدید**\n\n"
        "لطفاً اولین عکس رو بفرست..."
    )

def main():
    # ساخت اپلیکیشن
    application = Application.builder().token(TOKEN).build()
    
    # اضافه کردن دستورات
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("swap", swap_command))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    
    # شروع ربات
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
