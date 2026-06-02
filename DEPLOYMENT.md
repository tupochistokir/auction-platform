# Деплой Auction Platform

Эта инструкция поднимает платформу в интернете: backend на Render, frontend на Vercel, затем добавляет сайт в поиск через Google Search Console и Яндекс.Вебмастер.

## 1. Подготовить репозиторий

1. Создай приватный или публичный репозиторий на GitHub.
2. Убедись, что в коммит не попадают `venv`, `uploads`, локальная база, черновики диплома и сырые датасеты. В проекте уже настроен `.gitignore`, поэтому для нового репозитория достаточно:

```powershell
git add .
git commit -m "Prepare platform for production deploy"
git branch -M main
git remote add origin https://github.com/<username>/<repo>.git
git push -u origin main
```

Если Git уже отслеживал лишние локальные файлы, сначала выполни:

```powershell
git rm -r --cached --ignore-unmatch venv uploads auction.db
git rm -r --cached --ignore-unmatch app/__pycache__ app/api/__pycache__ app/db/__pycache__ app/pricing/__pycache__ app/schemas/__pycache__
git rm -r --cached --ignore-unmatch data/raw data/external data/processed
```

Если `origin` уже существует, используй:

```powershell
git remote set-url origin https://github.com/<username>/<repo>.git
git push -u origin main
```

## 2. Backend на Render

1. Открой Render и создай `New Web Service`.
2. Подключи GitHub-репозиторий.
3. Укажи:
   - Runtime: `Python`;
   - Build Command: `pip install -r requirements.txt`;
   - Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
4. В Environment добавь:
   - `PUBLIC_BASE_URL=https://<render-backend-url>`;
   - `FRONTEND_ORIGINS=https://<vercel-frontend-url>,https://<your-domain>`;
   - `DATABASE_URL=sqlite:///./auction.db` для быстрого запуска;
   - `AUCTION_AUTH_SECRET=<длинная случайная строка>` для подписи токенов авторизации.

Для постоянной базы лучше создать PostgreSQL на Render и вставить его `DATABASE_URL`. SQLite на бесплатном хостинге может терять данные при пересборке сервиса.

## 3. Frontend на Vercel

1. Открой Vercel и создай `New Project`.
2. Импортируй тот же GitHub-репозиторий.
3. В настройках проекта укажи Root Directory: `frontend`.
4. Build Command оставь `npm run build`, Output Directory: `dist`.
5. В Environment Variables добавь:
   - `VITE_API_URL=https://<render-backend-url>`.
6. Запусти Deploy.

## 4. Подключить домен

1. Купи домен или используй бесплатный домен Vercel.
2. В Vercel открой Project Settings -> Domains и подключи домен.
3. В Render обнови `FRONTEND_ORIGINS`, чтобы там был финальный домен frontend.
4. В Render обнови `PUBLIC_BASE_URL`, чтобы там был финальный адрес backend.

## 5. Обновить sitemap и robots

В файлах `frontend/public/robots.txt` и `frontend/public/sitemap.xml` замени `https://your-domain.ru` на настоящий адрес сайта.

После замены запушь изменения:

```powershell
git add frontend/public/robots.txt frontend/public/sitemap.xml
git commit -m "Set production sitemap domain"
git push
```

## 6. Добавить сайт в поиск

1. Google Search Console:
   - добавь домен или URL-префикс;
   - подтверди владение;
   - отправь sitemap: `https://<your-domain>/sitemap.xml`.
2. Яндекс.Вебмастер:
   - добавь сайт;
   - подтверди владение;
   - отправь sitemap: `https://<your-domain>/sitemap.xml`.

Индексация не происходит мгновенно. Обычно поисковикам нужно от нескольких дней до нескольких недель, особенно если сайт новый.

## 7. Что проверить после деплоя

1. Открывается главная страница frontend.
2. В браузере нет CORS-ошибок.
3. Работает регистрация/вход.
4. Создается лот.
5. Загружается изображение.
6. Открывается `https://<render-backend-url>/docs`.
7. Открывается `https://<your-domain>/robots.txt`.
8. Открывается `https://<your-domain>/sitemap.xml`.

## 8. Официальные инструкции

- Vercel: деплой Vite-приложения — https://vercel.com/docs/frameworks/vite
- Render: деплой FastAPI — https://render.com/docs/deploy-fastapi
- Google Search Central: sitemap — https://developers.google.com/search/docs/crawling-indexing/sitemaps/overview
- Яндекс.Вебмастер: sitemap — https://yandex.ru/support/webmaster/en/indexing-options/sitemap
