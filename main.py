import asyncio
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
from config import Config
from database import add_url, remove_url, get_urls, load_user_data, save_user_data, init_db, get_all_users
from checker import URLStatus

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize checker
checker = URLStatus()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    welcome_text = f"""
🚀 Welcome {user.first_name} to Website Uptime Bot!

I'll monitor your websites and alert you immediately when they go down or come back up.

📋 Available Commands:
/add <url>     - Add a website to monitor
/remove <url>  - Remove a website from monitoring
/list          - Show all monitored URLs
/status        - Check current status of all URLs
/pingnow       - Immediately check all URLs
/settings      - Configure notification preferences
/help          - Show this message

Example: /add https://example.com

⚡️ I'll check your URLs every {Config.PING_INTERVAL} seconds!
"""
    keyboard = [
        [InlineKeyboardButton("➕ Add URL", callback_data="add")],
        [InlineKeyboardButton("📊 Check Status", callback_data="status")],
        [InlineKeyboardButton("⚙️ Settings", callback_data="settings")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
🆘 Help Center

🔹 /add <url> - Add a website to monitor
   Example: /add https://example.com

🔹 /remove <url> - Remove a website from monitoring
   Example: /remove https://example.com

🔹 /list - Show all websites you're monitoring

🔹 /status - Get current status of all your URLs

🔹 /pingnow - Force an immediate check of all URLs

🔹 /settings - Customize your notification preferences

🔹 /help - Show this help message

📌 Important:
• Include http:// or https:// in URLs
• Maximum 50 URLs per user
• I'll notify you when sites go down AND when they come back up!
"""
    await update.message.reply_text(help_text)

async def add_url_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not context.args:
        await update.message.reply_text("❌ Please provide a URL!\nExample: /add https://example.com")
        return
    
    url = context.args[0]
    
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    urls = get_urls(user_id)
    if len(urls) >= 50:
        await update.message.reply_text("❌ You've reached the maximum of 50 URLs!")
        return
    
    if add_url(user_id, url):
        await update.message.reply_text(f"✅ Added {url} to monitoring list!")
        
        status = await checker.check_url(url)
        checker.update_status(user_id, url, status)
        await update.message.reply_text(f"🔍 Initial check: {status['status'].upper()} (Status: {status['status_code'] or 'N/A'})")
    else:
        await update.message.reply_text(f"❌ {url} is already in your monitoring list!")

async def remove_url_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not context.args:
        await update.message.reply_text("❌ Please provide a URL!\nExample: /remove https://example.com")
        return
    
    url = context.args[0]
    
    if remove_url(user_id, url):
        await update.message.reply_text(f"✅ Removed {url} from monitoring list!")
    else:
        await update.message.reply_text(f"❌ {url} is not in your monitoring list!")

async def list_urls(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    urls = get_urls(user_id)
    
    if not urls:
        await update.message.reply_text("📭 You're not monitoring any URLs yet!\nUse /add to start monitoring.")
        return
    
    message = "📋 Your monitored URLs:\n\n"
    for i, url in enumerate(urls, 1):
        status = checker.get_last_status(user_id, url)
        status_emoji = "🟢" if status.get('status') == 'up' else "🔴" if status.get('status') == 'down' else "⚪"
        message += f"{i}. {status_emoji} {url}\n"
    
    await update.message.reply_text(message)

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    urls = get_urls(user_id)
    
    if not urls:
        await update.message.reply_text("📭 No URLs to check!\nUse /add to start monitoring.")
        return
    
    await update.message.reply_text("🔍 Checking all URLs... Please wait.")
    
    status_messages = ["📊 Current Status:\n"]
    all_up = True
    
    for url in urls:
        status = await checker.check_url(url)
        checker.update_status(user_id, url, status)
        
        emoji = "🟢" if status['status'] == 'up' else "🔴"
        if status['status'] == 'down':
            all_up = False
        
        status_line = f"{emoji} {url}\n"
        status_line += f"   Status: {status['status'].upper()}\n"
        if status['status_code']:
            status_line += f"   Code: {status['status_code']}\n"
        if status['response_time']:
            status_line += f"   Response: {status['response_time']}s\n"
        if status['error']:
            status_line += f"   Error: {status['error']}\n"
        status_messages.append(status_line)
    
    if all_up:
        status_messages.append("\n✅ All sites are UP!")
    else:
        status_messages.append("\n⚠️ Some sites are DOWN!")
    
    await update.message.reply_text('\n'.join(status_messages))

async def pingnow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await status_command(update, context)

async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = load_user_data(user_id)
    settings = user_data.get('settings', {})
    
    message = f"""
⚙️ Notification Settings

🔔 Down Notifications: {'✅ ON' if settings.get('notify_down', True) else '❌ OFF'}
🔔 Up Notifications: {'✅ ON' if settings.get('notify_up', True) else '❌ OFF'}

Use these buttons to toggle:
"""
    keyboard = [
        [InlineKeyboardButton(
            f"{'✅' if settings.get('notify_down', True) else '❌'} Down Alerts",
            callback_data="toggle_down"
        )],
        [InlineKeyboardButton(
            f"{'✅' if settings.get('notify_up', True) else '❌'} Up Alerts",
            callback_data="toggle_up"
        )],
        [InlineKeyboardButton("🔙 Back to Menu", callback_data="back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(message, reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    user_data = load_user_data(user_id)
    settings = user_data.get('settings', {'notify_down': True, 'notify_up': True})
    
    if query.data == "add":
        await query.edit_message_text("📝 Send me the URL to monitor.\nExample: https://example.com")
        return
    
    elif query.data == "status":
        await query.edit_message_text("📊 Checking status...")
        await status_command(update, context)
        return
    
    elif query.data == "settings" or query.data == "back":
        await settings_command(update, context)
        return
    
    elif query.data == "toggle_down":
        settings['notify_down'] = not settings.get('notify_down', True)
        user_data['settings'] = settings
        save_user_data(user_id, user_data)
        await settings_command(update, context)
        return
    
    elif query.data == "toggle_up":
        settings['notify_up'] = not settings.get('notify_up', True)
        user_data['settings'] = settings
        save_user_data(user_id, user_data)
        await settings_command(update, context)
        return

async def monitor_loop():
    logger.info("🔄 Starting monitoring loop...")
    
    while True:
        try:
            users = get_all_users()
            logger.info(f"📊 Checking {len(users)} users' URLs...")
            
            for user_id in users:
                urls = get_urls(user_id)
                user_data = load_user_data(user_id)
                settings = user_data.get('settings', {'notify_down': True, 'notify_up': True})
                
                for url in urls:
                    current_status = await checker.check_url(url)
                    old_status = checker.get_last_status(user_id, url)
                    
                    if current_status['status'] != old_status.get('status'):
                        checker.update_status(user_id, url, current_status)
                        
                        if current_status['status'] == 'down' and settings.get('notify_down', True):
                            message = f"""
⚠️ <b>URL IS DOWN!</b>

🔗 {url}
⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
📊 Status: {current_status['status_code'] or 'N/A'}
❌ Error: {current_status['error'] or 'Unknown'}

{checker.get_downtime(user_id, url)} of downtime so far.
"""
                            await send_telegram_message(user_id, message, parse_mode='HTML')
                            
                        elif current_status['status'] == 'up' and old_status.get('status') == 'down' and settings.get('notify_up', True):
                            downtime = checker.get_downtime(user_id, url)
                            message = f"""
✅ <b>URL IS BACK UP!</b>

🔗 {url}
⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
⚡️ Response: {current_status['response_time']}s
⏱ Downtime: {downtime}

All systems operational!
"""
                            await send_telegram_message(user_id, message, parse_mode='HTML')
            
            await asyncio.sleep(Config.PING_INTERVAL)
            
        except Exception as e:
            logger.error(f"Error in monitor loop: {e}")
            await asyncio.sleep(Config.PING_INTERVAL)

async def send_telegram_message(user_id: int, text: str, parse_mode: str = None):
    try:
        app = Application.builder().token(Config.BOT_TOKEN).build()
        await app.bot.send_message(chat_id=user_id, text=text, parse_mode=parse_mode)
    except Exception as e:
        logger.error(f"Failed to send message to {user_id}: {e}")

def main():
    Config.validate()
    init_db()
    logger.info("✅ Database initialized")
    
    application = Application.builder().token(Config.BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("add", add_url_command))
    application.add_handler(CommandHandler("remove", remove_url_command))
    application.add_handler(CommandHandler("list", list_urls))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("pingnow", pingnow))
    application.add_handler(CommandHandler("settings", settings_command))
    application.add_handler(CallbackQueryHandler(button_handler))
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.create_task(monitor_loop())
    
    logger.info("🚀 Starting bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
