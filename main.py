import os
import json
import asyncio
import logging
from telegram import Update, Poll
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, 
    filters, ContextTypes, TypeHandler
)

import config
import database
import formatter
import prompts
import ai_providers
from config import logger

# ---------------------------------------------------------
# 1. Basic Commands & Subject Management
# ---------------------------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await database.init_db()
    welcome_msg = (
        "नमस्ते! 🎓 मैं आपका Class 12 Board Exam Study Bot हूँ।\n\n"
        "मेरे पास 6 Subjects का सपोर्ट है:\n"
        "/physics, /chemistry, /maths, /biology, /hindi, /english\n\n"
        "👉 सबसे पहले ऊपर दिए गए किसी एक subject पर क्लिक करें, फिर मुझे उस subject की PDF भेजें।\n"
        "मदद के लिए /help टाइप करें।"
    )
    await update.message.reply_text(welcome_msg)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "📚 **कमांड्स की लिस्ट:**\n\n"
        "**Subjects चुनें:**\n"
        "/physics, /chemistry, /maths, /biology, /hindi, /english\n\n"
        "**पढ़ाई के लिए (Active Subject पर काम करेंगे):**\n"
        "/notes - चैप्टर की समरी और फॉर्मूले\n"
        "/revision - क्विक रिवीजन पॉइंट्स\n"
        "/keypoints - 8-15 सबसे जरूरी पॉइंट्स\n"
        "/one_liner - 10+ वन-लाइनर फैक्ट्स\n"
        "/subjective - संभावित Subjective प्रश्न और उत्तर\n"
        "/objective - संभावित Objective प्रश्न और उत्तर\n"
        "/topics - सभी टॉपिक्स और उनका महत्व\n"
        "/quiz - MCQ टेस्ट (Telegram Poll)\n\n"
        "**स्टेटस:**\n"
        "/current - अभी कौन सा विषय एक्टिव है\n"
        "/subjects - किन विषयों की PDF सेव है\n"
        "/test - AI सर्वर्स का स्टेटस चेक करें"
    )
    await update.message.reply_text(help_text)

async def set_subject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    command = update.message.text.lower().strip('/')
    user_id = update.effective_user.id
    
    if command in config.SUBJECTS:
        await database.set_active_subject(user_id, command)
        await update.message.reply_text(f"✅ आपका Active Subject अब **{command.capitalize()}** है।\nअब आप मुझे PDF भेज सकते हैं या /notes, /quiz आदि कमांड्स का इस्तेमाल कर सकते हैं।")

async def current_subject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    subject = await database.get_active_subject(user_id)
    if subject:
        await update.message.reply_text(f"📌 अभी आपका Active Subject **{subject.capitalize()}** है।")
    else:
        await update.message.reply_text("❌ अभी कोई विषय चुना नहीं गया है। कृपया /physics या कोई अन्य विषय चुनें।")

async def list_subjects(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    subjects = await database.get_available_subjects(user_id)
    if subjects:
        sub_list = ", ".join([s.capitalize() for s in subjects])
        await update.message.reply_text(f"📂 आपके पास इन विषयों का डेटा सेव है:\n{sub_list}")
    else:
        await update.message.reply_text("📂 अभी तक आपने कोई PDF सेव नहीं की है।")

async def test_providers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔄 AI सर्वर्स का स्टेटस चेक कर रहा हूँ...")
    status = []
    if config.GEMINI_API_KEY: status.append("✅ Gemini (PDF Reader): Active")
    else: status.append("❌ Gemini: Missing Key")
    
    if config.GROQ_API_KEY: status.append("✅ Groq: Active")
    else: status.append("❌ Groq: Missing Key")
        
    if config.CEREBRAS_API_KEY: status.append("✅ Cerebras: Active")
    else: status.append("❌ Cerebras: Missing Key")
        
    await update.message.reply_text("\n".join(status))

# ---------------------------------------------------------
# 2. PDF Handling (One-Time Read -> Save to SQLite)
# ---------------------------------------------------------

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    subject = await database.get_active_subject(user_id)
    
    if not subject:
        await update.message.reply_text("❌ PDF भेजने से पहले कृपया कोई विषय चुनें (जैसे /physics)।")
        return

    document = update.message.document
    if not document.file_name.lower().endswith('.pdf'):
        await update.message.reply_text("❌ कृपया सिर्फ PDF फाइल ही भेजें।")
        return

    status_msg = await update.message.reply_text("📥 PDF डाउनलोड हो रही है...")
    
    try:
        # Download file
        file = await context.bot.get_file(document.file_id)
        file_path = f"temp_{user_id}.pdf"
        await file.download_to_drive(file_path)
        
        await status_msg.edit_text("⚙️ Gemini AI द्वारा PDF पढ़ी जा रही है (इसमें 1-2 मिनट लग सकते हैं)...")
        
        # Extract text using Gemini
        extracted_text = await ai_providers.extract_text_from_pdf(file_path)
        
        # Save to SQLite
        await database.save_document_text(user_id, subject, extracted_text)
        
        # Cleanup
        if os.path.exists(file_path):
            os.remove(file_path)
            
        await status_msg.edit_text(f"✅ शानदार! {subject.capitalize()} की PDF सफलतापूर्वक पढ़ ली गई है और हमेशा के लिए सेव हो गई है।\n\nअब आप /notes, /subjective, /quiz आदि का इस्तेमाल कर सकते हैं।")
        
    except Exception as e:
        logger.error(f"Document Error: {e}")
        await status_msg.edit_text(f"❌ PDF प्रोसेस करने में त्रुटि आई: {str(e)}")
        if os.path.exists(f"temp_{user_id}.pdf"):
            os.remove(f"temp_{user_id}.pdf")

# ---------------------------------------------------------
# 3. Content Generation Commands (Notes, Revision, etc.)
# ---------------------------------------------------------

async def process_content_command(update: Update, context: ContextTypes.DEFAULT_TYPE, command_name: str):
    user_id = update.effective_user.id
    subject = await database.get_active_subject(user_id)
    
    if not subject:
        await update.message.reply_text("❌ कृपया पहले कोई विषय चुनें (जैसे /physics)।")
        return
        
    # Check Cache First
    cached_response = await database.get_from_cache(user_id, subject, command_name)
    if cached_response:
        await send_long_message(update, context, cached_response)
        return

    # Get Extracted Text from DB
    document_text = await database.get_document_text(user_id, subject)
    if not document_text:
        await update.message.reply_text(f"❌ {subject.capitalize()} के लिए कोई PDF सेव नहीं है। कृपया पहले PDF भेजें।")
        return

    status_msg = await update.message.reply_text("⏳ AI आपके लिए कंटेंट तैयार कर रहा है, कृपया प्रतीक्षा करें...")

    try:
        system_prompt = prompts.get_system_prompt(subject)
        user_prompt = prompts.get_command_prompt(command_name, document_text)
        
        # Generate Text via Multi-AI Fallback
        raw_response = await ai_providers.generate_text_with_fallback(system_prompt, user_prompt)
        
        # Clean LaTeX and Markdown
        clean_response = formatter.clean_latex_and_markdown(raw_response)
        
        # Save to Cache
        await database.save_to_cache(user_id, subject, command_name, clean_response)
        
        # Send Message
        await status_msg.delete()
        await send_long_message(update, context, clean_response)
        
    except Exception as e:
        logger.error(f"Content Generation Error: {e}")
        await status_msg.edit_text(f"❌ त्रुटि: {str(e)}")

async def send_long_message(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    """Splits and sends long messages safely."""
    chunks = formatter.split_message(text)
    for chunk in chunks:
        await update.message.reply_text(chunk, parse_mode=None) # parse_mode=None is CRITICAL
        await asyncio.sleep(0.5) # Prevent Telegram flood limit

# Command Wrappers
async def cmd_notes(update: Update, context: ContextTypes.DEFAULT_TYPE): await process_content_command(update, context, "/notes")
async def cmd_revision(update: Update, context: ContextTypes.DEFAULT_TYPE): await process_content_command(update, context, "/revision")
async def cmd_keypoints(update: Update, context: ContextTypes.DEFAULT_TYPE): await process_content_command(update, context, "/keypoints")
async def cmd_one_liner(update: Update, context: ContextTypes.DEFAULT_TYPE): await process_content_command(update, context, "/one_liner")
async def cmd_subjective(update: Update, context: ContextTypes.DEFAULT_TYPE): await process_content_command(update, context, "/subjective")
async def cmd_objective(update: Update, context: ContextTypes.DEFAULT_TYPE): await process_content_command(update, context, "/objective")
async def cmd_topics(update: Update, context: ContextTypes.DEFAULT_TYPE): await process_content_command(update, context, "/topics")

# ---------------------------------------------------------
# 4. Quiz Handling (Native Telegram Poll)
# ---------------------------------------------------------

async def cmd_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    subject = await database.get_active_subject(user_id)
    
    if not subject:
        await update.message.reply_text("❌ कृपया पहले कोई विषय चुनें।")
        return
        
    document_text = await database.get_document_text(user_id, subject)
    if not document_text:
        await update.message.reply_text("❌ पहले PDF भेजें।")
        return

    topic = " ".join(context.args) if context.args else "पूरे चैप्टर"
    status_msg = await update.message.reply_text(f"⏳ {topic} पर Quiz तैयार हो रहा है...")

    system_prompt = prompts.get_system_prompt(subject) + "\nReturn ONLY a valid JSON object."
    user_prompt = f"""
    दिए गए text के आधार पर '{topic}' से एक बेहतरीन MCQ सवाल बनाओ।
    JSON format में जवाब दो:
    {{
        "question": "सवाल यहाँ (max 250 characters)",
        "options": ["Option A", "Option B", "Option C", "Option D"],
        "correct_index": 0, // 0, 1, 2, या 3
        "explanation": "सही जवाब का कारण (max 150 characters)"
    }}
    ध्यान रहे: कोई भी option 90 characters से बड़ा न हो। LaTeX का प्रयोग न करें।
    TEXT: {document_text[:5000]} # Sending partial text to save tokens for quick quiz
    """

    try:
        raw_response = await ai_providers.generate_text_with_fallback(system_prompt, user_prompt, require_json=True)
        
        # Parse JSON safely
        try:
            # Sometimes AI wraps JSON in markdown blocks
            if "```json" in raw_response:
                raw_response = raw_response.split("```json")[1].split("```")[0]
            elif "```" in raw_response:
                raw_response = raw_response.split("```")[1].split("```")[0]
                
            quiz_data = json.loads(raw_response.strip())
        except json.JSONDecodeError:
            raise Exception("AI ने सही फॉर्मेट में सवाल नहीं बनाया। कृपया दोबारा /quiz लिखें।")

        question = formatter.clean_latex_and_markdown(quiz_data['question'])
        options = [formatter.clean_latex_and_markdown(opt) for opt in quiz_data['options']]
        correct_id = int(quiz_data['correct_index'])
        explanation = formatter.clean_latex_and_markdown(quiz_data.get('explanation', ''))

        # Check Telegram Limits
        if len(question) > 290 or any(len(opt) > 95 for opt in options):
            # Fallback to Text Message if too long (especially for Physics/Maths)
            text_quiz = f"❓ **सवाल:**\n{question}\n\n"
            for i, opt in enumerate(options):
                text_quiz += f"{chr(65+i)}. {opt}\n"
            text_quiz += f"\n✅ **सही जवाब:** {chr(65+correct_id)}\n💡 **कारण:** {explanation}"
            
            await status_msg.delete()
            await update.message.reply_text(text_quiz, parse_mode=None)
        else:
            # Send Native Telegram Quiz
            await status_msg.delete()
            await context.bot.send_poll(
                chat_id=update.effective_chat.id,
                question=question,
                options=options,
                type=Poll.QUIZ,
                correct_option_id=correct_id,
                explanation=explanation,
                is_anonymous=True
            )

    except Exception as e:
        logger.error(f"Quiz Error: {e}")
        await status_msg.edit_text(f"❌ Quiz बनाने में त्रुटि: {str(e)}")

# ---------------------------------------------------------
# 5. General Text Questions
# ---------------------------------------------------------

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_question = update.message.text
    
    # Ignore commands
    if user_question.startswith('/'):
        return

    subject = await database.get_active_subject(user_id)
    document_text = ""
    if subject:
        document_text = await database.get_document_text(user_id, subject)

    status_msg = await update.message.reply_text("⏳ सोच रहा हूँ...")

    try:
        system_prompt = prompts.get_system_prompt(subject if subject else "general")
        
        if document_text:
            user_prompt = f"नीचे दिए गए TEXT के आधार पर student के सवाल का जवाब दो।\n\nTEXT: {document_text}\n\nSTUDENT QUESTION: {user_question}"
        else:
            user_prompt = f"STUDENT QUESTION: {user_question}"

        raw_response = await ai_providers.generate_text_with_fallback(system_prompt, user_prompt)
        clean_response = formatter.clean_latex_and_markdown(raw_response)
        
        await status_msg.delete()
        await send_long_message(update, context, clean_response)
        
    except Exception as e:
        logger.error(f"Text Handle Error: {e}")
        await status_msg.edit_text("❌ माफ़ करना, जवाब देने में कोई समस्या आ गई।")

# ---------------------------------------------------------
# 6. Error Handler & Main
# ---------------------------------------------------------

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Exception while handling an update: {context.error}")
    if isinstance(update, Update) and update.effective_message:
        await update.effective_message.reply_text("❌ कोई तकनीकी खराबी आ गई है। कृपया थोड़ी देर बाद प्रयास करें।")

def main():
    if not config.TELEGRAM_TOKEN:
        logger.error("TELEGRAM_TOKEN is missing!")
        return

    # Initialize Application
    application = ApplicationBuilder().token(config.TELEGRAM_TOKEN).build()

    # Setup DB on startup
    loop = asyncio.get_event_loop()
    loop.run_until_complete(database.init_db())

    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("test", test_providers))
    application.add_handler(CommandHandler("current", current_subject))
    application.add_handler(CommandHandler("subjects", list_subjects))
    
    # Subject Commands
    for sub in config.SUBJECTS:
        application.add_handler(CommandHandler(sub, set_subject))

    # Content Commands
    application.add_handler(CommandHandler("notes", cmd_notes))
    application.add_handler(CommandHandler("revision", cmd_revision))
    application.add_handler(CommandHandler("keypoints", cmd_keypoints))
    application.add_handler(CommandHandler("one_liner", cmd_one_liner))
    application.add_handler(CommandHandler("subjective", cmd_subjective))
    application.add_handler(CommandHandler("objective", cmd_objective))
    application.add_handler(CommandHandler("topics", cmd_topics))
    application.add_handler(CommandHandler("quiz", cmd_quiz))

    # Document & Text Handlers
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # Error Handler
    application.add_error_handler(error_handler)

    # Start Bot
    logger.info("Bot is starting...")
    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
