import time
import threading
import json
import os
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# توكن البوت الخاص بك
BOT_TOKEN = "8237082252:AAGhh0TXC5GhSkZNciO8Ulng-rrCMcYFxPI"
bot = telebot.TeleBot(BOT_TOKEN)

DB_FILE = "database.json"

# تحميل وحفظ البيانات لحمايتها من الضياع
def load_data():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)

accounts_queue = load_data()

# 1. توليد قاموس الرموز الذكي
def generate_smart_dictionary():
    common_pins = ["123456", "000000", "112233", "123123", "111111", "987654"]
    years = [str(year) for year in range(1980, 2026)]
    smart_pins = list(common_pins)
    for y in years:
        smart_pins.extend([f"00{y}", f"{y}00", f"19{y[2:]}00", f"20{y[2:]}00"])
    return list(set(smart_pins))

# 2. محاكاة جلب معلومات فري فاير عبر التوكن
def fetch_garena_info(token_url):
    # هنا تضع كود الـ API الفعلي الخاص بك للاتصال بغارينا لاحقاً
    return {
        "player_name": "Badr_Hero",
        "player_id": "987654321"
    }

# 3. دالة الفحص الخلفية المستمرة (تعمل كل ثانيتين)
def process_queue():
    pins_pool = generate_smart_dictionary()
    while True:
        data_changed = False
        for chat_id, account in list(accounts_queue.items()):
            if account['status'] != 'running':
                continue
                
            # حماية: مهلة 10 ثوانٍ بين المحاولات
            if time.time() - account['last_attempt_time'] < 10:
                continue
                
            # تفادي تخطي عدد المحاولات اليومية
            if account['attempts'] >= 10:
                account['status'] = 'limit'
                bot.send_message(chat_id, f"⏳ **حد يومي!**\nتم الوصول لـ 10 محاولات للحساب ({account['player_name']}). تم الإيقاف تلقائياً لمدة 24 ساعة لحماية التوكن.")
                data_changed = True
                continue

            current_index = account['current_pin_index']
            if current_index >= len(pins_pool):
                account['status'] = 'finished'
                bot.send_message(chat_id, f"🏁 انتهت جميع الرموز المتاحة للحساب {account['player_name']}.")
                data_changed = True
                continue

            current_pin = pins_pool[current_index]
            
            # محاكاة إرسال الطلب لغارينا
            response = "wrong_pin" 

            account['attempts'] += 1
            account['current_pin_index'] += 1
            account['last_attempt_time'] = time.time()
            data_changed = True

            if response == "success":
                account['status'] = 'success'
                bot.send_message(chat_id, f"🎉 **مبارك! تم سحب رمز الأمان بنجاح!**\n👤 الحساب: {account['player_name']}\n🔑 الرمز الصحيح: `{current_pin}`")
            elif response == "error_login_limit":
                account['status'] = 'limit'
                bot.send_message(chat_id, f"⚠️ **نظام الطوارئ!** سيرفر غارينا أرجع خطأ حظر وشيك. تم تفعيل الهدنة 24 ساعة لحسابك.")

        if data_changed:
            save_data(accounts_queue)
        time.sleep(2)

# تشغيل الخيط الخلفي في الخلفية
threading.Thread(target=process_queue, daemon=True).start()

# 4. استقبال أوامر تليجرام
@bot.message_handler(commands=['start'])
def send_welcome(message):
    msg = bot.reply_to(message, "👋 أهلاً بك في بوت تخمين رمز أمان فري فاير.\n\n📥 من فضلك، **أرسل رابط التوكن الخاص بك الآن** للبدء:")
    bot.register_next_step_handler(msg, process_token)

def process_token(message):
    token_url = message.text
    chat_id = str(message.chat.id)

    if not token_url.startswith("http"):
        bot.reply_to(message, "❌ الرابط غير صحيح. يرجى إرسال أمر /start وإدخال رابط توكن صالح.")
        return

    bot.reply_to(message, "🔍 جاري الفحص وجلب معلومات الحساب من غارينا...")
    
    # جلب معلومات فري فاير
    info = fetch_garena_info(token_url)
    
    # تسجيل الحساب في الذاكرة وحفظه كـ "مستعد"
    accounts_queue[chat_id] = {
        "token": token_url,
        "player_name": info["player_name"],
        "player_id": info["player_id"],
        "attempts": 0,
        "current_pin_index": 0,
        "last_attempt_time": 0,
        "status": "ready"
    }
    save_data(accounts_queue)

    # إنشاء المستطيل (الزر التفاعلي) للتفعيل
    markup = InlineKeyboardMarkup()
    btn_text = f"🤖 تفعيل التخمين الآلي للحساب: {info['player_name']} ({info['player_id']})"
    markup.add(InlineKeyboardButton(text=btn_text, callback_data="start_brute"))

    bot.send_message(chat_id, "✅ تم العثور على الحساب بنجاح!\nاضغط على الزر أدناه لبدء عملية التخمين الذكي:", reply_markup=markup)

# 5. التعامل مع ضغطة الزر المستطيل
@bot.callback_query_handler(func=lambda call: call.data == "start_brute")
def callback_start_brute(call):
    chat_id = str(call.message.chat.id)
    
    if chat_id in accounts_queue and accounts_queue[chat_id]['status'] == 'ready':
        accounts_queue[chat_id]['status'] = 'running'
        save_data(accounts_queue)
        
        bot.answer_callback_query(call.id, "🚀 تم تفعيل البوت بنجاح!")
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, 
                              text=f"⚙️ **البوت يعمل الآن في الخلفية...**\n👤 الحساب: {accounts_queue[chat_id]['player_name']}\n⏳ سيتم تجربة رمز كل 10 ثوانٍ (بحد أقصى 10 محاولات يومياً). سنخطرك فوراً عند إيجاد الرمز!")
    else:
        bot.answer_callback_query(call.id, "❌ هذا الحساب مفعّل بالفعل أو غير مسجل.")

# تشغيل البوت باستمرار لاستقبال الرسائل
bot.infinity_polling()
