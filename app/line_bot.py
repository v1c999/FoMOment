from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from app.firebase import get_messages, clear_messages, add_message, get_summary_count, set_summary_count
from app.gemini import summarize_with_gemini
from app.config import Config
import threading

line_bot_api = LineBotApi(Config.LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(Config.LINE_CHANNEL_SECRET)

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    if event.source.type == 'group':
        group_id = event.source.group_id
        user_message = event.message.text
        user_profile = line_bot_api.get_group_member_profile(group_id, event.source.user_id)
        user_name = user_profile.display_name
        if user_message.startswith("設定摘要訊息數"):
            try:
                count = int(user_message.split(" ")[1])
                set_summary_count(group_id, count)
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text=f"好的！每經過 {count} 則訊息會整理摘要給您")
                )
            except (ValueError, IndexError):
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text="請輸入有效的數字，例如：設定摘要訊息數 5")
                )
            return
    
        if user_message == "立即摘要":
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="正在整理訊息，請稍候...")
            )
            
            def process_summary():
                messages = get_messages(group_id)
                if messages:
                    summary = summarize_with_gemini(messages)
                    line_bot_api.push_message(
                        event.source.group_id,
                        TextSendMessage(text=f"訊息摘要\n\n{summary}")
                    )
                    clear_messages(group_id)
                else:
                    line_bot_api.push_message(
                        event.source.group_id,
                        TextSendMessage(text="沒有新訊息")
                    )
            
            threading.Thread(target=process_summary).start()
            return
        
        add_message(group_id, user_message, user_name)
        
        summary_count = get_summary_count(group_id)
        messages = get_messages(group_id)
        
        if len(messages) >= summary_count:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="正在整理訊息，請稍候...")
            )
            
            def process_summary():
                messages = get_messages(group_id)
                if messages:
                    summary = summarize_with_gemini(messages)
                    line_bot_api.push_message(
                        event.source.group_id,
                        TextSendMessage(text=f"訊息摘要\n\n{summary}")
                    )
                    clear_messages(group_id)
                else:
                    line_bot_api.push_message(
                        event.source.group_id,
                        TextSendMessage(text="沒有新訊息")
                    )
            
            threading.Thread(target=process_summary).start()
            return

def handle_line_event(body, signature):
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        raise ValueError("Invalid signature. Check your channel access token/channel secret.")
