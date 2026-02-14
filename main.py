import os
import threading
from dotenv import load_dotenv
from flask import Flask
from telegram.ext import Updater, MessageHandler, Filters
from transformers import pipeline, set_seed

# --- تحميل متغيرات البيئة ---
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# --- إعداد الموديل العربي للذكاء الاصطناعي ---
# النموذج الأساسي: AraGPT2-base (يدعم توليد النص العربي)
MODEL_NAME = "aubmindlab/aragpt2-base"  # يمكن تغييره لأي موديل عربي مطلوب

try:
    ai_chatbot = pipeline("text-generation", model=MODEL_NAME)
except Exception as e:
    print("حدث خطأ في تحميل الموديل:", e)
    print("سيتم استخدام DistilGPT2 بدلاً منه")
    ai_chatbot = pipeline("text-generation", model="distilgpt2")

set_seed(42)  # تثبيت نتائج الذكاء الاصطناعي لتكون متشابهة دائماً

def ai_response(user_message):
    # توليد رد ذكاء اصطناعي (العربية مدعومة في الموديل)
    result = ai_chatbot(user_message, max_length=70, num_return_sequences=1)
    return result[0]['generated_text']

def handle_message(update, context):
    user_text = update.message.text
    response = ai_response(user_text)
    # الرد بنص مختصر (يعتمد على الموديل)
    update.message.reply_text(response.strip())

def run_telegram():
    updater = Updater(TELEGRAM_TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(MessageHandler(Filters.text & (~Filters.command), handle_message))
    updater.start_polling()
    print("Bot is running...")
    updater.idle()

# --- سيرفر وهمي لإرضاء Render (حل مشكلة Timeout) ---
flask_app = Flask(__name__)

@flask_app.route("/")
def health_check():
    return "Professor Atlas is Alive!", 200

def run_flask():
    # Render يمرر البورت في متغير بيئة اسمه PORT
    port = int(os.environ.get("PORT", 8000))
    flask_app.run(host='0.0.0.0', port=port)

if __name__ == "__main__":
    # تشغيل البوت والسيرفر معًا
    threading.Thread(target=run_telegram).start()
    run_flask()