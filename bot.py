"""
bot.py — ShadowRotate Telegram Bot
البوت الرئيسي
"""

import os
import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton,
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes,
)

from database import (
    init_db, get_user, create_user, update_user,
    is_subscribed, activate_subscription, get_user_orders,
    create_session, finish_session,
)
from plans import PLANS, PAYMENT_METHODS, BOT_NAME, BOT_VERSION, SUPPORT_CONTACT
from payments import (
    create_payment_request, confirm_payment, reject_payment,
    set_tx_id, set_screenshot, format_admin_notification,
)
from admin import (
    admin_panel, show_stats, show_users, show_pending,
    admin_confirm, admin_reject, admin_back, admin_exit,
)


# ============================================================
# الإعدادات (من Environment Variables)
# ============================================================
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
SERVER_URL = os.getenv("SERVER_URL", "http://127.0.0.1:8000")


# ============================================================
# Logging
# ============================================================
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO,
)
log = logging.getLogger(__name__)


# ============================================================
# الحالة المؤقتة
# ============================================================
user_state = {}  # {user_id: "state"}


# ============================================================
# القوائم
# ============================================================
def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎁 تجربة مجانية", callback_data="trial")],
        [InlineKeyboardButton("💳 اشتراك يومي — 3$", callback_data="buy_daily")],
        [InlineKeyboardButton("📆 اشتراك أسبوعي — 12$", callback_data="buy_weekly")],
        [InlineKeyboardButton("📅 اشتراك شهري — 35$", callback_data="buy_monthly")],
        [InlineKeyboardButton("💎 مدى الحياة — 199$", callback_data="buy_lifetime")],
        [InlineKeyboardButton("🛒 الكود المصدري — 500$", callback_data="buy_source")],
        [InlineKeyboardButton("💰 اشتراكي", callback_data="my_sub")],
        [InlineKeyboardButton("📞 تواصل معنا", callback_data="contact")],
    ])


def payment_menu(plan_key):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📱 فودافون كاش", callback_data=f"pay_vodafone_{plan_key}")],
        [InlineKeyboardButton("💳 إنستاباي", callback_data=f"pay_instapay_{plan_key}")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")],
    ])


def back_to_main():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="back_main")],
    ])


# ============================================================
# /start
# ============================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if not get_user(user.id):
        create_user(user.id, user.username or "", user.first_name or "")

    text = (
        "╔══════════════════════════════╗\n"
        f"║   ◈ *{BOT_NAME}* ◈          ║\n"
        "║   نظام إدارة الحسابات        ║\n"
        "╚══════════════════════════════╝\n\n"
        f"👋 أهلاً *{user.first_name}*!\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🎯 *اختر من القائمة:*"
    )

    await update.message.reply_text(
        text,
        reply_markup=main_menu(),
        parse_mode="Markdown"
    )


# ============================================================
# /menu
# ============================================================
async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎯 *القائمة الرئيسية:*",
        reply_markup=main_menu(),
        parse_mode="Markdown"
    )


# ============================================================
# /admin
# ============================================================
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ غير مصرح لك")
        return

    await admin_panel(update, context)


# ============================================================
# callbacks
# ============================================================
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    # ---------- رجوع للقائمة ----------
    if data == "back_main":
        await query.edit_message_text(
            "🎯 *القائمة الرئيسية:*",
            reply_markup=main_menu(),
            parse_mode="Markdown"
        )

    # ---------- تجربة مجانية ----------
    elif data == "trial":
        user = get_user(user_id)
        if user and user["trial_used"]:
            await query.edit_message_text(
                "❌ استخدمت التجربة المجانية بالفعل.\n\n"
                "اختر اشتراك من القائمة.",
                reply_markup=back_to_main(),
            )
            return

        update_user(user_id, trial_used=1)
        activate_subscription(user_id, "trial", 1)

        await query.edit_message_text(
            "╔══════════════════════════════╗\n"
            "║   🎁 *تجربة مجانية*           ║\n"
            "╚══════════════════════════════╝\n\n"
            "✅ *تم تفعيل التجربة!*\n\n"
            "👥 *الحسابات:* 5\n"
            "⏰ *المدة:* 24 ساعة\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🚀 اكتب /run للبدء",
            reply_markup=back_to_main(),
            parse_mode="Markdown"
        )

    # ---------- اشتراكي ----------
    elif data == "my_sub":
        user = get_user(user_id)
        if not user:
            await query.edit_message_text("❌ خطأ")
            return

        sub_type = user["subscription_type"]
        expires = user["subscription_expires"]

        if not sub_type or not expires:
            text = (
                "╔══════════════════════════════╗\n"
                "║   💰 *اشتراكي*                ║\n"
                "╚══════════════════════════════╝\n\n"
                "❌ *غير مشترك*\n\n"
                "اختر اشتراك من القائمة."
            )
        else:
            plan = PLANS.get(sub_type, {})
            try:
                exp_date = datetime.fromisoformat(expires)
                days_left = (exp_date - datetime.now()).days
                exp_str = exp_date.strftime("%Y-%m-%d")
            except Exception:
                days_left = 0
                exp_str = expires

            text = (
                "╔══════════════════════════════╗\n"
                "║   💰 *اشتراكي*                ║\n"
                "╚══════════════════════════════╝\n\n"
                f"📦 *الخطة:* {plan.get('name', sub_type)}\n"
                f"⏰ *ينتهي:* {exp_str}\n"
                f"📅 *متبقي:* {days_left} يوم\n"
                f"👥 *الحسابات:* {plan.get('accounts', 0)}\n"
            )

        await query.edit_message_text(
            text,
            reply_markup=back_to_main(),
            parse_mode="Markdown"
        )

    # ---------- تواصل ----------
    elif data == "contact":
        await query.edit_message_text(
            "╔══════════════════════════════╗\n"
            "║   📞 *تواصل معنا*             ║\n"
            "╚══════════════════════════════╝\n\n"
            f"💬 *Telegram:* {SUPPORT_CONTACT}\n"
            f"📱 *WhatsApp:* 01227176398",
            reply_markup=back_to_main(),
            parse_mode="Markdown"
        )

    # ---------- اختيار خطة ----------
    elif data.startswith("buy_"):
        plan_key = data.replace("buy_", "")
        plan = PLANS.get(plan_key)
        if not plan:
            return

        text = (
            "╔══════════════════════════════╗\n"
            f"║   {plan['name']}          ║\n"
            "╚══════════════════════════════╝\n\n"
            f"💰 *السعر:* {plan['price']} $\n"
            f"⏰ *المدة:* {plan['duration_days']} يوم\n"
            f"👥 *الحسابات:* {plan['accounts']}\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "✨ *المميزات:*\n"
        )
        for feat in plan["features"]:
            text += f"  ✅ {feat}\n"
        text += "\n━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        text += "💳 *اختر طريقة الدفع:*"

        await query.edit_message_text(
            text,
            reply_markup=payment_menu(plan_key),
            parse_mode="Markdown"
        )

    # ---------- اختيار طريقة دفع ----------
    elif data.startswith("pay_"):
        parts = data.split("_")
        method = parts[1]
        plan_key = "_".join(parts[2:])

        result = create_payment_request(user_id, plan_key, method)
        if "error" in result:
            await query.edit_message_text(f"❌ {result['error']}")
            return

        user_state[user_id] = f"paying_{result['order_id']}"

        await query.edit_message_text(
            result["instruction"],
            parse_mode="Markdown"
        )
        return

    # ---------- أوامر الأدمن ----------
    elif data == "admin_stats":
        await show_stats(update, context)

    elif data == "admin_users":
        await show_users(update, context)

    elif data == "admin_pending":
        await show_pending(update, context)

    elif data.startswith("adm_ok_"):
        await admin_confirm(update, context)

    elif data.startswith("adm_no_"):
        await admin_reject(update, context)

    elif data == "admin_back":
        await admin_back(update, context)

    elif data == "admin_exit":
        await admin_exit(update, context)


# ============================================================
# استقبال الرسائل
# ============================================================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    state = user_state.get(user_id, "")

    # ---------- العميل في حالة دفع ----------
    if state.startswith("paying_"):
        order_id = state.replace("paying_", "")

        if text.strip() == "تم":
            # إشعار الأدمن
            user = get_user(user_id)
            notification = format_admin_notification(
                order_id,
                user["username"] or "—",
                user["first_name"] or "—",
            )

            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ تأكيد", callback_data=f"adm_ok_{order_id}"),
                    InlineKeyboardButton("❌ رفض", callback_data=f"adm_no_{order_id}"),
                ]
            ])

            try:
                await context.bot.send_message(
                    chat_id=ADMIN_ID,
                    text=notification,
                    reply_markup=keyboard,
                    parse_mode="Markdown"
                )
            except Exception as e:
                log.error(f"فشل إشعار الأدمن: {e}")

            await update.message.reply_text(
                "✅ *تم استلام طلبك!*\n\n"
                "سيتم مراجعة الدفع والتأكيد قريباً.\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🆔 *رقم طلبك:* `{order_id}`",
                parse_mode="Markdown"
            )

            user_state[user_id] = ""
            return

        # رقم عملية
        if text.strip().isdigit():
            set_tx_id(order_id, text.strip())
            await update.message.reply_text(
                "✅ تم استلام رقم العملية\n\n"
                "ابعت صورة التحويل (اختياري)"
            )
            return

        await update.message.reply_text(
            "✍️ اكتب `تم` بعد التحويل",
            parse_mode="Markdown"
        )
        return

    # ---------- افتراضي ----------
    await update.message.reply_text(
        "🎯 اختر من القائمة:",
        reply_markup=main_menu(),
        parse_mode="Markdown"
    )


# ============================================================
# استقبال الصور
# ============================================================
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    state = user_state.get(user_id, "")

    if not state.startswith("paying_"):
        return

    order_id = state.replace("paying_", "")

    # تحميل الصورة
    photo = update.message.photo[-1]
    file = await photo.get_file()

    upload_dir = Path(__file__).parent / "uploads"
    upload_dir.mkdir(exist_ok=True)

    file_path = upload_dir / f"{order_id}_{user_id}.jpg"
    await file.download_to_drive(file_path)

    set_screenshot(order_id, str(file_path))

    # إرسال للأدمن
    try:
        await context.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=open(file_path, "rb"),
            caption=f"📸 صورة تحويل\n🆔 `{order_id}`\n👤 @{update.effective_user.username or '—'}",
            parse_mode="Markdown"
        )
    except Exception as e:
        log.error(f"فشل إرسال الصورة للأدمن: {e}")

    await update.message.reply_text(
        "✅ *تم استلام الصورة!*\n\n"
        "✍️ اكتب `تم` لتأكيد الطلب",
        parse_mode="Markdown"
    )


# ============================================================
# Main
# ============================================================
def main():
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN مش موجود في Environment Variables")
        return

    if not ADMIN_ID:
        print("❌ ADMIN_ID مش موجود في Environment Variables")
        return

    init_db()

    app = Application.builder().token(BOT_TOKEN).build()

    # الأوامر
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", menu))
    app.add_handler(CommandHandler("admin", admin_command))

    # Callbacks
    app.add_handler(CallbackQueryHandler(callback_handler))

    # الرسائل
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    print("=" * 50)
    print(f"  🤖 {BOT_NAME} Bot v{BOT_VERSION}")
    print(f"  👤 Admin ID: {ADMIN_ID}")
    print("=" * 50)
    print("  ✅ Bot is running...")
    print("=" * 50)

    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()