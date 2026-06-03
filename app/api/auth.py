import base64
import hashlib
import hmac
import json
import os
import secrets
import shutil
import time
import uuid
from typing import Any, Dict, Optional

from fastapi import APIRouter, File, Header, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import or_

from app.config import get_public_base_url, get_upload_dir
from app.db.database import SessionLocal
from app.db.models import User


router = APIRouter(prefix="/auth", tags=["Авторизация"])

AUTH_SECRET = os.getenv("AUCTION_AUTH_SECRET", "auction-platform-demo-secret")


class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str
    display_name: Optional[str] = None
    recovery_question: str
    recovery_answer: str


class LoginRequest(BaseModel):
    identifier: str
    password: str


class PasswordRecoveryVerifyRequest(BaseModel):
    email: str
    recovery_question: str
    recovery_answer: str


class PasswordResetRequest(BaseModel):
    email: str
    recovery_question: str
    recovery_answer: str
    new_password: str


class ProfileUpdateRequest(BaseModel):
    display_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    age: Optional[int] = None
    city: Optional[str] = None
    bio: Optional[str] = None
    is_incognito: Optional[bool] = None


def _normalize(value: str) -> str:
    return (value or "").strip().lower()


def _normalize_answer(value: str) -> str:
    return " ".join((value or "").strip().lower().split())


def _hash_password(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        120_000,
    ).hex()


def _verify_password(password: str, salt: str, expected_hash: str) -> bool:
    actual_hash = _hash_password(password, salt)
    return hmac.compare_digest(actual_hash, expected_hash or "")


def _hash_recovery_answer(answer: str, salt: str) -> str:
    return _hash_password(_normalize_answer(answer), salt)


def _verify_recovery_answer(answer: str, salt: str, expected_hash: str) -> bool:
    if not salt or not expected_hash:
        return False
    actual_hash = _hash_recovery_answer(answer, salt)
    return hmac.compare_digest(actual_hash, expected_hash or "")


def _demo_account_rescue_enabled() -> bool:
    value = os.getenv("DEMO_ACCOUNT_RESCUE", "1").strip().lower()
    return value not in {"0", "false", "no", "off"}


def _make_username_from_email(db, email: str) -> str:
    local_part = (email.split("@", 1)[0] or "user").lower()
    safe_name = "".join(
        char if char.isalnum() or char == "_" else "_"
        for char in local_part
    ).strip("_")

    if len(safe_name) < 3:
        safe_name = f"user_{secrets.token_hex(2)}"

    base_name = safe_name[:28]
    username = base_name
    suffix = 1

    while db.query(User).filter(User.username == username).first():
        suffix += 1
        username = f"{base_name[:24]}_{suffix}"

    return username


def _set_user_password(user: User, password: str) -> None:
    salt = secrets.token_hex(16)
    user.password_salt = salt
    user.password_hash = _hash_password(password, salt)


def _set_user_recovery(user: User, question: str, answer: str) -> None:
    recovery_salt = secrets.token_hex(16)
    user.password_recovery_question = _normalize(question)
    user.password_recovery_answer_salt = recovery_salt
    user.password_recovery_answer_hash = _hash_recovery_answer(answer, recovery_salt)


def _create_rescued_user(db, email: str, question: str, answer: str, password: str) -> User:
    username = _make_username_from_email(db, email)
    display_name = email.split("@", 1)[0] or username
    user = User(
        username=username,
        email=email,
        display_name=display_name,
    )
    _set_user_password(user, password)
    _set_user_recovery(user, question, answer)

    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _has_recovery_credentials(user: User) -> bool:
    return bool(
        getattr(user, "password_recovery_question", None)
        and getattr(user, "password_recovery_answer_salt", None)
        and getattr(user, "password_recovery_answer_hash", None)
    )


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def _sign(payload: str) -> str:
    digest = hmac.new(
        AUTH_SECRET.encode("utf-8"),
        payload.encode("ascii"),
        hashlib.sha256,
    ).digest()
    return _b64encode(digest)


def create_token(user: User) -> str:
    payload = {
        "user_id": user.id,
        "username": user.username,
        "iat": int(time.time()),
    }
    body = _b64encode(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    )
    signature = _sign(body)
    return f"{body}.{signature}"


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        body, signature = token.split(".", 1)
    except ValueError:
        return None

    if not hmac.compare_digest(_sign(body), signature):
        return None

    try:
        return json.loads(_b64decode(body).decode("utf-8"))
    except (ValueError, json.JSONDecodeError):
        return None


def _read_bearer_token(authorization: Optional[str]) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="Требуется вход в аккаунт")

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="Некорректный токен авторизации")

    return token


def _user_to_dict(user: User) -> Dict[str, Any]:
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "display_name": user.display_name or user.username,
        "avatar_url": getattr(user, "avatar_url", None),
        "phone": getattr(user, "phone", None),
        "age": getattr(user, "age", None),
        "city": getattr(user, "city", None),
        "bio": getattr(user, "bio", None),
        "is_incognito": bool(getattr(user, "is_incognito", False)),
        "password_recovery_question": getattr(user, "password_recovery_question", None),
        "has_password_recovery": bool(
            getattr(user, "password_recovery_question", None)
            and getattr(user, "password_recovery_answer_hash", None)
        ),
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


def _get_current_user(db, authorization: Optional[str]) -> User:
    token = _read_bearer_token(authorization)
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Сессия недействительна")

    user = db.query(User).filter(User.id == payload.get("user_id")).first()
    if not user:
        raise HTTPException(status_code=401, detail="Пользователь не найден")

    return user


@router.post("/register")
def register(payload: RegisterRequest):
    username = _normalize(payload.username)
    email = _normalize(payload.email)
    display_name = (payload.display_name or payload.username or "").strip()

    if len(username) < 3:
        raise HTTPException(status_code=400, detail="Логин должен быть не короче 3 символов")
    if "@" not in email or "." not in email:
        raise HTTPException(status_code=400, detail="Введите корректный email")
    if len(payload.password or "") < 6:
        raise HTTPException(status_code=400, detail="Пароль должен быть не короче 6 символов")
    if not _normalize(payload.recovery_question):
        raise HTTPException(status_code=400, detail="Выберите вопрос для восстановления пароля")
    if len(_normalize_answer(payload.recovery_answer)) < 2:
        raise HTTPException(status_code=400, detail="Ответ для восстановления должен быть не короче 2 символов")

    db = SessionLocal()
    try:
        existing = (
            db.query(User)
            .filter(or_(User.username == username, User.email == email))
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=409,
                detail="Пользователь с таким логином или email уже существует",
            )

        salt = secrets.token_hex(16)
        recovery_salt = secrets.token_hex(16)
        user = User(
            username=username,
            email=email,
            display_name=display_name or username,
            password_salt=salt,
            password_hash=_hash_password(payload.password, salt),
            password_recovery_question=_normalize(payload.recovery_question),
            password_recovery_answer_salt=recovery_salt,
            password_recovery_answer_hash=_hash_recovery_answer(
                payload.recovery_answer,
                recovery_salt,
            ),
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        return {
            "message": "Регистрация завершена",
            "token": create_token(user),
            "user": _user_to_dict(user),
        }
    finally:
        db.close()


@router.post("/password-recovery/verify")
def verify_password_recovery(payload: PasswordRecoveryVerifyRequest):
    email = _normalize(payload.email)
    question = _normalize(payload.recovery_question)

    if "@" not in email or "." not in email:
        raise HTTPException(status_code=400, detail="Введите корректный email")
    if not question:
        raise HTTPException(status_code=400, detail="Выберите вопрос для восстановления пароля")
    if len(_normalize_answer(payload.recovery_answer)) < 2:
        raise HTTPException(status_code=400, detail="Ответ должен быть не короче 2 символов")

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user and _demo_account_rescue_enabled():
            return {
                "message": "Аккаунт можно восстановить",
                "can_reset": True,
                "account_missing": True,
            }

        if user and not _has_recovery_credentials(user) and _demo_account_rescue_enabled():
            return {
                "message": "Доступ можно восстановить",
                "can_reset": True,
                "recovery_missing": True,
            }

        if (
            not user
            or _normalize(getattr(user, "password_recovery_question", "")) != question
            or not _verify_recovery_answer(
                payload.recovery_answer,
                getattr(user, "password_recovery_answer_salt", ""),
                getattr(user, "password_recovery_answer_hash", ""),
            )
        ):
            raise HTTPException(status_code=401, detail="Ответ на секретный вопрос не совпал")

        return {"message": "Ответ подтверждён", "can_reset": True}
    finally:
        db.close()


@router.post("/password-recovery/reset")
def reset_password(payload: PasswordResetRequest):
    email = _normalize(payload.email)
    question = _normalize(payload.recovery_question)

    if "@" not in email or "." not in email:
        raise HTTPException(status_code=400, detail="Введите корректный email")
    if not question:
        raise HTTPException(status_code=400, detail="Выберите вопрос для восстановления пароля")
    if len(_normalize_answer(payload.recovery_answer)) < 2:
        raise HTTPException(status_code=400, detail="Ответ должен быть не короче 2 символов")

    if len(payload.new_password or "") < 6:
        raise HTTPException(status_code=400, detail="Новый пароль должен быть не короче 6 символов")

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user and _demo_account_rescue_enabled():
            user = _create_rescued_user(
                db,
                email,
                question,
                payload.recovery_answer,
                payload.new_password,
            )
            return {
                "message": "Аккаунт восстановлен",
                "token": create_token(user),
                "user": _user_to_dict(user),
                "account_created": True,
            }

        if user and not _has_recovery_credentials(user) and _demo_account_rescue_enabled():
            _set_user_password(user, payload.new_password)
            _set_user_recovery(user, question, payload.recovery_answer)
            db.commit()
            db.refresh(user)

            return {
                "message": "Доступ к аккаунту восстановлен",
                "token": create_token(user),
                "user": _user_to_dict(user),
                "recovery_repaired": True,
            }

        if (
            not user
            or _normalize(getattr(user, "password_recovery_question", "")) != question
            or not _verify_recovery_answer(
                payload.recovery_answer,
                getattr(user, "password_recovery_answer_salt", ""),
                getattr(user, "password_recovery_answer_hash", ""),
            )
        ):
            raise HTTPException(status_code=401, detail="Не удалось подтвердить владельца аккаунта")

        _set_user_password(user, payload.new_password)
        db.commit()
        db.refresh(user)

        return {
            "message": "Пароль обновлён",
            "token": create_token(user),
            "user": _user_to_dict(user),
        }
    finally:
        db.close()


@router.post("/login")
def login(payload: LoginRequest):
    identifier = _normalize(payload.identifier)

    db = SessionLocal()
    try:
        user = (
            db.query(User)
            .filter(or_(User.username == identifier, User.email == identifier))
            .first()
        )
        if not user or not _verify_password(
            payload.password,
            user.password_salt,
            user.password_hash,
        ):
            raise HTTPException(status_code=401, detail="Неверный логин или пароль")

        return {
            "message": "Вход выполнен",
            "token": create_token(user),
            "user": _user_to_dict(user),
        }
    finally:
        db.close()


@router.get("/me")
def me(authorization: Optional[str] = Header(default=None)):
    db = SessionLocal()
    try:
        user = _get_current_user(db, authorization)
        return {"user": _user_to_dict(user)}
    finally:
        db.close()


@router.patch("/me")
def update_me(
    payload: ProfileUpdateRequest,
    authorization: Optional[str] = Header(default=None),
):
    db = SessionLocal()
    try:
        user = _get_current_user(db, authorization)
        data = payload.dict(exclude_unset=True)

        if "email" in data and data["email"] is not None:
            email = _normalize(data["email"])
            if "@" not in email or "." not in email:
                raise HTTPException(status_code=400, detail="Введите корректный email")
            existing = (
                db.query(User)
                .filter(User.email == email, User.id != user.id)
                .first()
            )
            if existing:
                raise HTTPException(status_code=409, detail="Этот email уже привязан к другому аккаунту")
            user.email = email

        if "display_name" in data and data["display_name"] is not None:
            display_name = data["display_name"].strip()
            if len(display_name) < 2:
                raise HTTPException(status_code=400, detail="Имя должно быть не короче 2 символов")
            user.display_name = display_name

        if "phone" in data:
            user.phone = (data["phone"] or "").strip() or None

        if "age" in data:
            age = data["age"]
            if age is not None and not 14 <= int(age) <= 100:
                raise HTTPException(status_code=400, detail="Возраст должен быть от 14 до 100")
            user.age = int(age) if age is not None else None

        if "city" in data:
            user.city = (data["city"] or "").strip() or None

        if "bio" in data:
            bio = (data["bio"] or "").strip()
            user.bio = bio[:500] if bio else None

        if "is_incognito" in data:
            user.is_incognito = bool(data["is_incognito"])

        db.commit()
        db.refresh(user)
        return {"message": "Профиль обновлён", "user": _user_to_dict(user)}
    finally:
        db.close()


@router.post("/avatar")
def upload_avatar(
    file: UploadFile = File(...),
    authorization: Optional[str] = Header(default=None),
):
    if not (file.content_type or "").startswith("image/"):
        raise HTTPException(status_code=400, detail="Можно загружать только изображения")

    db = SessionLocal()
    try:
        user = _get_current_user(db, authorization)
        upload_dir = os.path.join(get_upload_dir(), "avatars")
        os.makedirs(upload_dir, exist_ok=True)

        _, extension = os.path.splitext(file.filename or "")
        safe_extension = extension.lower() if extension else ".jpg"
        filename = f"{uuid.uuid4().hex}{safe_extension}"
        file_path = os.path.join(upload_dir, filename)

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        user.avatar_url = f"{get_public_base_url()}/uploads/avatars/{filename}"
        db.commit()
        db.refresh(user)

        return {
            "message": "Аватар обновлён",
            "avatar_url": user.avatar_url,
            "user": _user_to_dict(user),
        }
    finally:
        db.close()


@router.post("/logout")
def logout():
    return {"message": "Сессия завершена"}
