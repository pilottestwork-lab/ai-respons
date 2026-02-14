import os
import logging
import threading
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from transformers import pipeline, set_seed

# 1. إعداد السجلات
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# 2. إعداد المفاتيح
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# --- إعداد موديل الذكاء الاصطناعي المجاني ---
SYSTEM_INSTRUCTION = """
أنت البروفيسور أطلس، خبير أكاديمي طبي متخصص.
دورك هو مساعدة الطلاب في حل الأسئلة الطبية وتحليل التقارير.
عندما تستلم سؤالاً، قم بحله وشرح السبب.
إذا طلب الطالب حل أسئلة (MCQs)، قم بتحليل كل خيار ولماذا هو صح أو خطأ.
لغة التواصل: العربية بشكل أساسي، مع ذكر المصطلحات الطبية بالإنجليزية بين أقواس.
في نهاية كل رسالة، ذكرهم بالقناة: https://t.me/atlas_medical.
"""

MODEL_NAME = "aubmindlab/aragpt2-base"

try:
    ai_chatbot = pipeline("text-generation", model=MODEL_NAME)
except Exception as e:
    logging.warning(f"حدث خطأ في تحميل الموديل العربي: {e}. سيتم استخدام distilgpt2 بدلًا منه.")
    ai_chatbot = pipeline("text-generation", model="distilgpt2")

set_seed(42)  # تثبيت النتائج

def ai_response(user_message):
    prompt = SYSTEM_INSTRUCTION + "\n" + user_message
    result = ai_chatbot(prompt, max_length=400, num_return_sequences=1)
    return result[0]['generated_text'].strip()

# --- سيرفر وهمي لإرضاء Render (حل مشكلة Timeout) ---
flask_app = Flask(__name__)
@flask_app.route('/')
def health_check():
    return "Professor Atlas is Alive!", 200

def run_flask():
    port = int(os.environ.get("PORT", 8000))
    flask_app.run(host='0.0.0.0', port=port)

# --- دوال البوت ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "أهلاً بك يا دكتور! أنا البروفيسور أطلس. أرسل لي أي سؤال طبي، وسأقوم بتحليله فوراً.\n"
        "نعتذر، في النسخة المجانية لا يمكن تحليل الصور أو ملفات PDF، فقط نصوص وأسئلة."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = None
    if update.message.text:
        user_text = update.message.text
    elif update.message.caption:
        user_text = update.message.caption
    else:
        user_text = "أكتب سؤالاً طبيًا أو تقرير وسيتم تحليله."

    # منع معالجة الصور والملفات
    if update.message.photo or update.message.document:
        await update.message.reply_text(
            "عذراً، الذكاء الاصطناعي المجاني الحالي يدعم فقط تحليل النصوص وليس الصور أو الملفات. أرسل نصًا أو سؤالًا طبيًا!"
        )
        return

    try:
        response = ai_response(user_text)
        # تقسيم الرسائل الطويلة لتجنب خطأ تليجرام
        if len(response) > 4000:
            for i in range(0, len(response), 4000):
                await update.message.reply_text(response[i:i+4000])
        else:
            await update.message.reply_text(response)
    except Exception as e:
        await update.message.reply_text(f"عذراً يا دكتور، حدث خطأ تقني: {str(e)}")

# --- التشغيل الرئيسي ---
if __name__ == '__main__':
    if not TELEGRAM_TOKEN:
        print("Error: مفتاح تليجرام غير موجود!")
    else:
        threading.Thread(target=run_flask, daemon=True).start()
        application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
        application.add_handler(CommandHandler('start', start))
        # استقبال رسائل نص فقط (تجاهل الصور والملفات)
        application.add_handler(MessageHandler(filters.ALL, handle_message))
        print("Professor Atlas is running with Flask health check (local Arabic AI)...")
        application.run_polling()
