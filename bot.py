import os
import logging
from datetime import datetime, timedelta
from collections import defaultdict
from pytube import YouTube
from telegram import Update, ForceReply
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Track downloads per user per day
download_tracker = defaultdict(lambda: {'count': 0, 'reset_time': datetime.utcnow() + timedelta(days=1)})

# Helper function to check and update user download limit
def can_download(user_id):
    now = datetime.utcnow()
    tracker = download_tracker[user_id]
    if now >= tracker['reset_time']:
        tracker['count'] = 0
        tracker['reset_time'] = now + timedelta(days=1)
    return tracker['count'] < 5

def increment_download(user_id):
    download_tracker[user_id]['count'] += 1

# Start command
def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    update.message.reply_html(
        rf"Hi {user.mention_html()}! Send me a video link and I will download it for you. You can download up to 5 videos per day."
    )

# Download video
def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    if not can_download(user_id):
        update.message.reply_text("❌ You have reached your daily limit of 5 downloads. Please try again tomorrow.")
        return

    try:
        yt = YouTube(text)
        stream = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc().first()
        if not stream:
            update.message.reply_text("❌ Could not find a downloadable video stream.")
            return

        file_path = f"{yt.title}.mp4"
        stream.download(filename=file_path)

        with open(file_path, 'rb') as f:
            update.message.reply_video(f)

        os.remove(file_path)
        increment_download(user_id)
    except Exception as e:
        logger.error(f"Download failed: {e}")
        update.message.reply_text("❌ Failed to download video. Please ensure the link is valid and try again.")

# Main function
def main():
    TOKEN = os.getenv("BOT_TOKEN")
    if not TOKEN:
        raise ValueError("BOT_TOKEN environment variable not set")

    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    application.run_polling()

if __name__ == '__main__':
    main()
