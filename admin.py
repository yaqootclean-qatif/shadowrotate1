"""
admin.py — لوحة تحكم الأدمن
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import (
    get_stats, get_all_users, get_pending_orders,
    get_order, update_user, activate_subscription
)
from payments import confirm_payment, reject_payment
from plans import PLANS, PAYMENT_METHODS


# ============================================================
# لوحة الأدمن الرئيسية
# ============================================================
def admin_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 الإحصائيات", callback_data="admin_stats")],
        [InlineKeyboardButton("👥 المستخدمين", callback_data="admin_users")],
        [InlineKeyboardButton("💰 الطلبات المعلقة", callback_data="admin_pending")],
        [InlineKeyboardButton("🔍 بحث مستخدم", callback_data="admin_search")],
        [InlineKeyboardButton("📢 إرسال جماعي", callback_data="admin_broadcast")],
        [InlineKeyboardButton("🔙 خروج", callback_data="admin_exit")],
    ])


async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض لوحة الأدمن"""
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text(
            "╔══════════════════════════════╗\n"
            "║   🛠️ *لوحة التحكم*            ║\n"
            "╚══════════════════════════════╝\n\n"
            "اختر من الأزرار:",
            reply_markup=admin_menu(),
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            "╔══════════════════════════════╗\n"
            "║   🛠️ *لوحة التحكم*            ║\n"
            "╚══════════════════════════════╝\n\n"
            "اختر من الأزرار:",
            reply_markup=admin_menu(),
            parse_mode="Markdown"
        )


# ============================================================
# الإحصائيات
# ============================================================
async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    stats = get_stats()

    text = (
        "╔══════════════════════════════╗\n"
        "║   📊 *الإحصائيات*            ║\n"
        "╚══════════════════════════════╝\n\n"
        f"👥 *إجمالي المستخدمين:* {stats['total_users']}\n"
        f"✅ *اشتراكات نشطة:* {stats['active_subs']}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💰 *الطلبات:* {stats['total_orders']}\n"
        f"💵 *الإيرادات:* {stats['total_revenue']:.2f} $\n"
        f"⏳ *قيد الانتظار:* {stats['pending_orders']}\n"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 تحديث", callback_data="admin_stats")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="admin_back")],
    ])

    await query.edit_message_text(
        text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


# ============================================================
# المستخدمين
# ============================================================
async def show_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    users = get_all_users(limit=20)

    if not users:
        text = "❌ مفيش مستخدمين"
    else:
        text = (
            "╔══════════════════════════════╗\n"
            "║   👥 *آخر 20 مستخدم*         ║\n"
            "╚══════════════════════════════╝\n\n"
        )
        for u in users:
            user_id = u[0]
            username = u[1] or "—"
            first_name = u[2] or "—"
            expires = u[6] or "غير مشترك"
            status = "🟢" if expires != "غير مشترك" else "⚪"
            text += f"{status} *{first_name}* | @{username}\n"
            text += f"   🆔 `{user_id}`\n\n"

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 رجوع", callback_data="admin_back")],
    ])

    await query.edit_message_text(
        text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


# ============================================================
# الطلبات المعلقة
# ============================================================
async def show_pending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    orders = get_pending_orders()

    if not orders:
        text = (
            "╔══════════════════════════════╗\n"
            "║   💰 *الطلبات المعلقة*        ║\n"
            "╚══════════════════════════════╝\n\n"
            "✅ مفيش طلبات معلقة"
        )
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 رجوع", callback_data="admin_back")],
        ])
    else:
        text = (
            "╔══════════════════════════════╗\n"
            "║   💰 *الطلبات المعلقة*        ║\n"
            "╚══════════════════════════════╝\n\n"
        )
        buttons = []
        for o in orders[:10]:
            order_id = o[0]
            user_id = o[1]
            plan = o[2]
            amount = o[3]
            method = o[4]
            plan_name = PLANS.get(plan, {}).get("name", plan)
            method_name = PAYMENT_METHODS.get(method, {}).get("name", method)
            text += f"🆔 `{order_id}`\n"
            text += f"   {plan_name} — {amount}$ — {method_name}\n\n"
            buttons.append([
                InlineKeyboardButton(f"✅ {order_id}", callback_data=f"adm_ok_{order_id}"),
                InlineKeyboardButton(f"❌", callback_data=f"adm_no_{order_id}"),
            ])
        buttons.append([InlineKeyboardButton("🔙 رجوع", callback_data="admin_back")])
        keyboard = InlineKeyboardMarkup(buttons)

    await query.edit_message_text(
        text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


# ============================================================
# تأكيد دفع
# ============================================================
async def admin_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    order_id = query.data.replace("adm_ok_", "")
    result = confirm_payment(order_id, query.from_user.id)

    if "error" in result:
        await query.edit_message_text(
            f"❌ خطأ: {result['error']}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 رجوع", callback_data="admin_pending")],
            ])
        )
        return

    # تفعيل الاشتراك
    plan_key = result["plan"]
    plan = PLANS.get(plan_key, {})
    duration = plan.get("duration_days", 30)

    activate_subscription(
        result["user_id"],
        plan_key,
        duration,
    )

    # إشعار العميل
    try:
        from datetime import datetime, timedelta
        expires = (datetime.now() + timedelta(days=duration)).strftime("%Y-%m-%d")

        await context.bot.send_message(
            chat_id=result["user_id"],
            text=(
                "╔══════════════════════════════╗\n"
                "║   ✅ *تم تأكيد الدفع!*        ║\n"
                "╚══════════════════════════════╝\n\n"
                f"🎉 *مبروك!*\n\n"
                f"📦 *اشتراكك:* {plan.get('name', '—')}\n"
                f"⏰ *ينتهي:* {expires}\n"
                f"👥 *الحسابات:* {plan.get('accounts', 0)}\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🚀 اكتب /menu للبدء"
            ),
            parse_mode="Markdown"
        )
    except Exception as e:
        print(f"[ADMIN] فشل إشعار العميل: {e}")

    await query.edit_message_text(
        f"✅ *تم تأكيد الطلب* `{order_id}`",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 رجوع", callback_data="admin_pending")],
        ]),
        parse_mode="Markdown"
    )


# ============================================================
# رفض دفع
# ============================================================
async def admin_reject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    order_id = query.data.replace("adm_no_", "")
    result = reject_payment(order_id, "لم يتم التأكد من الدفع")

    if "error" in result:
        await query.edit_message_text(f"❌ {result['error']}")
        return

    # إشعار العميل
    try:
        await context.bot.send_message(
            chat_id=result["user_id"],
            text=(
                "╔══════════════════════════════╗\n"
                "║   ❌ *تم رفض الدفع*           ║\n"
                "╚══════════════════════════════╝\n\n"
                "لم يتم التأكد من عملية الدفع.\n\n"
                "تواصل معنا: @ahmed_naser"
            ),
            parse_mode="Markdown"
        )
    except Exception as e:
        print(f"[ADMIN] فشل إشعار العميل: {e}")

    await query.edit_message_text(
        f"❌ *تم رفض الطلب* `{order_id}`",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 رجوع", callback_data="admin_pending")],
        ]),
        parse_mode="Markdown"
    )


# ============================================================
# رجوع
# ============================================================
async def admin_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await admin_panel(update, context)


async def admin_exit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "✅ تم الخروج من لوحة التحكم",
    )