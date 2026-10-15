"""
payments.py — نظام الدفع (فودافون كاش + إنستاباي)
"""

import uuid
from datetime import datetime
from database import create_order, update_order, get_order
from plans import PLANS, PAYMENT_METHODS


# ============================================================
# إنشاء طلب دفع جديد
# ============================================================
def create_payment_request(user_id: int, plan_key: str, method: str) -> dict:
    """
    ينشئ طلب دفع جديد.
    يرجّع dict فيه:
        - order_id
        - instruction
        - amount
        - method_name
    """
    if plan_key not in PLANS:
        return {"error": "خطة غير صالحة"}

    if method not in PAYMENT_METHODS:
        return {"error": "طريقة دفع غير صالحة"}

    plan = PLANS[plan_key]
    pay_method = PAYMENT_METHODS[method]

    # إنشاء ID فريد للطلب
    order_id = uuid.uuid4().hex[:12].upper()

    # حفظ الطلب في قاعدة البيانات
    create_order(
        order_id=order_id,
        user_id=user_id,
        plan=plan_key,
        amount=plan["price"],
        method=method,
    )

    # صيغة التعليمات
    instruction = (
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"*{pay_method['name']}*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💰 *المبلغ:* {plan['price']} $\n"
        f"📦 *الخطة:* {plan['name']}\n\n"
        f"📞 *حوّل إلى:*\n"
        f"`{pay_method['number']}`\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📝 *بعد التحويل:*\n\n"
        f"1️⃣ ابعت *رقم العملية*\n"
        f"2️⃣ ابعت *صورة التحويل*\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 *رقم طلبك:* `{order_id}`\n\n"
        f"✍️ اكتب `تم` بعد التحويل"
    )

    return {
        "order_id": order_id,
        "instruction": instruction,
        "amount": plan["price"],
        "plan_name": plan["name"],
        "method_name": pay_method["name"],
        "method_number": pay_method["number"],
    }


# ============================================================
# تأكيد الدفع (من الأدمن)
# ============================================================
def confirm_payment(order_id: str, admin_id: int) -> dict:
    """
    الأدمن يأكد الدفع.
    """
    order = get_order(order_id)
    if not order:
        return {"error": "طلب غير موجود"}

    if order["status"] == "confirmed":
        return {"error": "تم تأكيده بالفعل"}

    # تحديث الطلب
    now = datetime.now().isoformat(timespec="seconds")
    update_order(
        order_id,
        status="confirmed",
        confirmed_at=now,
    )

    return {
        "success": True,
        "order_id": order_id,
        "user_id": order["user_id"],
        "plan": order["plan"],
        "amount": order["amount"],
    }


# ============================================================
# رفض الدفع (من الأدمن)
# ============================================================
def reject_payment(order_id: str, reason: str = "") -> dict:
    """
    الأدمن يرفض الدفع.
    """
    order = get_order(order_id)
    if not order:
        return {"error": "طلب غير موجود"}

    if order["status"] == "confirmed":
        return {"error": "لا يمكن رفض طلب مؤكد"}

    update_order(
        order_id,
        status="rejected",
    )

    return {
        "success": True,
        "order_id": order_id,
        "user_id": order["user_id"],
        "reason": reason,
    }


# ============================================================
# تحديث رقم العملية
# ============================================================
def set_tx_id(order_id: str, tx_id: str) -> bool:
    """
    العميل يبعت رقم العملية.
    """
    order = get_order(order_id)
    if not order:
        return False

    update_order(order_id, tx_id=tx_id)
    return True


# ============================================================
# تحديث صورة التحويل
# ============================================================
def set_screenshot(order_id: str, file_path: str) -> bool:
    """
    العميل يبعت صورة التحويل.
    """
    order = get_order(order_id)
    if not order:
        return False

    update_order(order_id, screenshot=file_path)
    return True


# ============================================================
# إشعار الأدمن
# ============================================================
def format_admin_notification(order_id: str, username: str, first_name: str) -> str:
    """
    صيغة الإشعار للأدمن.
    """
    order = get_order(order_id)
    if not order:
        return "❌ طلب غير موجود"

    plan = PLANS.get(order["plan"], {})
    method = PAYMENT_METHODS.get(order["method"], {})

    text = (
        f"🔔 *طلب دفع جديد*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 *العميل:* {first_name}\n"
        f"🆔 *Username:* @{username}\n"
        f"🔢 *User ID:* `{order['user_id']}`\n\n"
        f"📦 *الخطة:* {plan.get('name', '—')}\n"
        f"💰 *المبلغ:* {order['amount']} $\n"
        f"💳 *الطريقة:* {method.get('name', '—')}\n\n"
        f"🆔 *رقم الطلب:* `{order_id}`\n"
    )

    if order["tx_id"]:
        text += f"📝 *رقم العملية:* `{order['tx_id']}`\n"

    if order["screenshot"]:
        text += f"📸 *صورة:* موجودة ✅\n"

    return text


# ============================================================
# إشعار العميل (بعد التأكيد)
# ============================================================
def format_client_confirmation(plan_key: str, duration_days: int, expires: str) -> str:
    """
    صيغة التأكيد للعميل.
    """
    plan = PLANS.get(plan_key, {})

    return (
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"✅ *تم تأكيد الدفع!*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🎉 *مبروك!*\n\n"
        f"📦 *اشتراكك:* {plan.get('name', '—')}\n"
        f"⏰ *ينتهي:* {expires}\n"
        f"👥 *الحسابات:* {plan.get('accounts', 0)}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🚀 *ابدأ الآن:*\n\n"
        f"اكتب /menu للبدء"
    )


# ============================================================
# إشعار العميل (بعد الرفض)
# ============================================================
def format_client_rejection(reason: str = "") -> str:
    return (
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"❌ *تم رفض الدفع*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"السبب: {reason or 'غير محدد'}\n\n"
        f"تواصل معنا: @ahmed_naser"
    )#