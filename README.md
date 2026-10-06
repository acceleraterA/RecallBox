# RecallBox

RecallBox is an open-source RAG learning project for saving links, extracting and chunking article content, retrieving relevant passages with pgvector, and answering questions with grounded citations.

V2 keeps the system intentionally compact for interview practice: Next.js, FastAPI, Postgres/pgvector, Supabase Auth, Hugging Face embeddings, and an optional Hugging Face or OpenAI answer model.

## Features For V1

- Save links manually with an optional note.
- Paste platform share text that contains a URL; RecallBox extracts the first URL automatically.
- Detect platform from URL, including YouTube, Bilibili, Xiaohongshu, Douyin, WeChat articles, Weibo, Douban, Instagram, Snapchat, TikTok, X, Medium, Reddit, and generic web pages.
- Auto-tag common platform saves as `post`, `profile`, `collection`, `community`, or `video` when the URL/share text makes that clear.
- Avoid duplicate saves by returning the existing item when the same URL is saved again.
- Extract basic metadata with Open Graph tags first: title, description, and thumbnail.
- Save URLs even when metadata extraction fails, with `status="failed"`.
- View all saved items.
- Search by keyword across URL, title, description, summary, note, and tag names.
- Filter by platform, tag, and created date range.
- Open an item detail page.
- Add or edit title, notes, and tags.
- Edit an item thumbnail by pasting a custom image URL.
- Delete saved items.
- Keep optional LLM summary/tag enrichment disabled behind config.
- Deploy frontend to Vercel and backend to Render, Railway, or Fly.io.

## Features For V2

- Extract readable article text without bypassing anti-bot protections.
- Split saved content into bounded overlapping chunks.
- Embed chunks with the configured embedding provider.
- Retrieve user-scoped passages with pgvector cosine similarity.
- Ask questions across saved links from the web UI.
- Generate grounded answers with numbered source citations.
- Carry a small amount of conversational history for follow-up questions.
- Fall back to retrieved passages when LLM credits are unavailable.
- Backfill existing items with a bounded command for free-tier demos.

## Tech Stack

- Frontend: Next.js + TypeScript
- Backend: FastAPI + Python
- Auth: Supabase Auth, optional for local development
- Database: Postgres with pgvector for item and chunk retrieval
- ORM: SQLAlchemy
- Migrations: Alembic
- Content ingestion: `requests` + BeautifulSoup
- RAG answer providers: Hugging Face Inference or OpenAI
- Local database: Docker Compose
- Frontend deployment: Vercel
- Backend deployment: Render, Railway, or Fly.io
- Remote database: Neon, Supabase, Railway Postgres, or another managed Postgres provider

## Repository Structure

```text
.
├── frontend/          # Next.js app
├── backend/           # FastAPI app, SQLAlchemy models, Alembic migrations
├── scripts/           # local development helper scripts
├── .github/workflows/ # GitHub Actions CI
├── Makefile           # one-command local workflows
├── docker-compose.yml # local Postgres
├── render.yaml        # optional Render blueprint for the backend
├── LICENSE
├── .gitignore
└── README.md
```

## Local Development Setup

Prerequisites:

- Python 3.9+
- Node.js 20.9+ and npm
- Docker Desktop or another Docker runtime

Fast path:

```bash
make dev
```

`make dev` starts local Postgres, installs missing backend/frontend dependencies, runs migrations, starts FastAPI on `http://localhost:8000`, and starts Next.js on `http://localhost:3000`. Press `Ctrl+C` to stop the backend and frontend processes.

Useful local commands:

```bash
make help
make install
make db
make migrate
make backend
make frontend
make check
make backfill-embeddings
make backfill-rag
```

Manual setup is still available if you want to run each service yourself.

Start Postgres:

```bash
docker compose up -d postgres
```

Run the backend:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

Check the API:

```bash
curl http://localhost:8000/health
```

Run the frontend in a second terminal:

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

Open `http://localhost:3000`.

## CI And Auto-Deploy

The repo includes GitHub Actions at `.github/workflows/ci.yml`.

CI runs on pushes to `main` and `feature/**` branches, and on pull requests into `main`:

- Backend job: installs Python dependencies, starts pgvector Postgres, runs Alembic migrations, compiles backend code, and verifies app imports.
- Frontend job: installs Node dependencies, runs TypeScript checks, and builds the Next.js app.

Recommended deployment automation:

- Production services should track `main`.
- Experimental/demo services can track `feature/v2-rag` or another feature branch.
- Render backend: use `render.yaml` or set the service manually, then enable auto-deploy after checks pass. The blueprint uses `autoDeployTrigger: checksPass`, `preDeployCommand: alembic upgrade head`, and starts Uvicorn with `$PORT`.
- Vercel frontend: connect the GitHub repo, set the project root to `frontend`, and enable Git auto-deploy. Vercel will build production from the production branch and previews from feature branches.

The CI workflow can also trigger provider deploy hooks after backend and frontend checks pass. Add any of these GitHub repository secrets as needed:

```bash
RENDER_DEPLOY_HOOK_URL       # production backend from main
VERCEL_DEPLOY_HOOK_URL       # production frontend from main
RENDER_V2_DEPLOY_HOOK_URL    # v2 preview backend from feature/v2-rag
VERCEL_V2_DEPLOY_HOOK_URL    # v2 preview frontend from feature/v2-rag
```

Use either provider-native Git auto-deploy or deploy hooks for a given service. Enabling both can create duplicate deployments. If the deploy-hook secrets are not set, the deploy jobs will safely skip that provider.

With this setup, the normal development flow becomes:

```bash
make dev
git add .
git commit -m "Describe the change"
git push
```

GitHub Actions runs automatically. If the branch is configured for auto-deploy, Vercel and Render can redeploy automatically after the checks pass.

## Environment Variables

Backend, stored locally in `backend/.env`:

```bash
DATABASE_URL=postgresql+psycopg://recallbox:recallbox@localhost:5433/recallbox
FRONTEND_ORIGIN=http://localhost:3000,http://127.0.0.1:3000
DEFAULT_USER_EMAIL=demo@recallbox.local
ENABLE_AUTH=false
SUPABASE_URL=
SUPABASE_ANON_KEY=
ENABLE_LLM=false
LLM_PROVIDER=huggingface
HUGGINGFACE_CHAT_MODEL=openai/gpt-oss-20b
OPENAI_CHAT_MODEL=gpt-4.1-mini
RAG_MIN_SIMILARITY=0.55
RAG_TOP_K=5
RAG_CHUNK_SIZE=1800
RAG_CHUNK_OVERLAP=200
RAG_MAX_CHUNKS_PER_ITEM=4
RAG_MAX_CONTENT_CHARS=7000
RAG_MAX_ANSWER_TOKENS=400
ENABLE_EMBEDDINGS=false
EMBEDDING_MIN_SIMILARITY=0.55
EMBEDDING_PROVIDER=huggingface
HUGGINGFACE_TOKEN=
HUGGINGFACE_EMBEDDING_MODEL=BAAI/bge-small-en-v1.5
OPENAI_API_KEY=
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_EMBEDDING_DIMENSIONS=1536
```

Frontend, stored locally in `frontend/.env.local`:

```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
```

Use a comma-separated `FRONTEND_ORIGIN` value if more than one frontend origin should be allowed. Leave `ENABLE_AUTH=false` for local demo mode, or set `ENABLE_AUTH=true` with Supabase values to require accounts. Leave `ENABLE_EMBEDDINGS=false` unless your database has pgvector and you have a token for the selected embedding provider. Do not commit `.env`, `.env.local`, API keys, database credentials, or provider secrets. The included `.env.example` files are safe templates only.

## Database Setup

Local development uses the Postgres service in `docker-compose.yml`.

For deployment, create a managed Postgres database with Neon, Supabase, Railway Postgres, Render Postgres, Fly Postgres, or another provider. Copy the provider connection string into the backend host as `DATABASE_URL`.

The v1.5 semantic-search migrations add `embedding_text` for all databases. If pgvector is available, they also enable the `vector` extension and add a dimension-neutral `vector` column. Provider, model, and dimension metadata are stored with every vector so different embedding providers can coexist safely. Use a Postgres provider that supports pgvector, such as Supabase or Neon, if you want to enable embeddings.

## Auth Setup

RecallBox v1.5 supports Supabase Auth. Local development can still run in demo mode with `ENABLE_AUTH=false`.

To enable auth:

1. Create a Supabase project.
2. In Supabase Auth, enable email/password signups.
3. Copy the project URL and anon/publishable key.
4. Backend env:
   ```bash
   ENABLE_AUTH=true
   SUPABASE_URL=https://YOUR_PROJECT.supabase.co
   SUPABASE_ANON_KEY=YOUR_SUPABASE_ANON_OR_PUBLISHABLE_KEY
   ```
5. Frontend env:
   ```bash
   NEXT_PUBLIC_SUPABASE_URL=https://YOUR_PROJECT.supabase.co
   NEXT_PUBLIC_SUPABASE_ANON_KEY=YOUR_SUPABASE_ANON_OR_PUBLISHABLE_KEY
   ```

When auth is enabled, the frontend sends the Supabase access token to FastAPI using `Authorization: Bearer ...`. The backend verifies the session with Supabase and stores items under the matching local user.

## Semantic Search Setup

RecallBox v1.5 can optionally generate embeddings for saved items and rank search results by meaning instead of exact keywords. This is disabled by default.

The backend supports multiple embedding providers through `EMBEDDING_PROVIDER`:

- `huggingface`: the current default, using Hugging Face Inference Providers.
- `openai`: retained for future use with the OpenAI embeddings API.

To enable Hugging Face embeddings:

1. Create a Hugging Face account and a fine-grained token at `https://huggingface.co/settings/tokens`. Give it permission to make calls to Inference Providers.
2. Use a Postgres database that supports pgvector.
3. Run `alembic upgrade head`.
4. Add backend env vars:
   ```bash
   ENABLE_EMBEDDINGS=true
   EMBEDDING_MIN_SIMILARITY=0.55
   EMBEDDING_PROVIDER=huggingface
   HUGGINGFACE_TOKEN=hf_YOUR_TOKEN
   HUGGINGFACE_EMBEDDING_MODEL=BAAI/bge-small-en-v1.5
   ```
5. Restart the backend. New and updated items will use Hugging Face embeddings.
6. Backfill existing items:
   ```bash
   cd backend
   source .venv/bin/activate
   python -m app.backfill_embeddings
   ```

To switch to OpenAI later, keep the same database and change the provider settings:

```bash
ENABLE_EMBEDDINGS=true
EMBEDDING_MIN_SIMILARITY=0.55
EMBEDDING_PROVIDER=openai
OPENAI_API_KEY=YOUR_OPENAI_API_KEY
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_EMBEDDING_DIMENSIONS=1536
```

Each saved vector records its provider, model, and dimension. Semantic search compares only items generated by the currently active provider/model, so incompatible vectors are not mixed. Run the backfill command after switching providers.

The search UI includes a `Semantic` checkbox. For BGE models, RecallBox applies the model-recommended retrieval instruction to search queries only. Semantic results must meet `EMBEDDING_MIN_SIMILARITY`, which defaults to `0.55`; increase it for fewer, stricter matches or decrease it for broader recall. If embeddings are disabled or an embedding request fails, the backend falls back to normal keyword search.

## RAG Assistant Setup

V2 extracts readable article text, stores up to four chunks per item by default, and embeds those chunks for grounded question answering. The limits are intentionally conservative for free-tier interview demos.

Run the V2 migration and index a few existing links:

```bash
cd backend
source .venv/bin/activate
alembic upgrade head
python -m app.backfill_rag --limit 3
```

Retrieval-only mode costs no chat-completion credits and remains useful for debugging the RAG pipeline:

```bash
ENABLE_LLM=false
```

To enable Hugging Face grounded answers with the same token used for embeddings:

```bash
ENABLE_LLM=true
LLM_PROVIDER=huggingface
HUGGINGFACE_CHAT_MODEL=openai/gpt-oss-20b
RAG_MIN_SIMILARITY=0.55
RAG_TOP_K=5
```

When Hugging Face free credits are exhausted, RecallBox returns the retrieved passages and citations instead of failing the request. To index one item while conserving credits, run `python -m app.backfill_rag --item-id ITEM_ID`.

For Neon and other SSL-required providers, the value often looks like:

```bash
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST/DBNAME?sslmode=require
```

## How To Run Migrations

Migrations live in `backend/alembic`.

Run migrations locally:

```bash
cd backend
source .venv/bin/activate
alembic upgrade head
```

Create a future migration after model changes:

```bash
cd backend
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```

For deployment, run `alembic upgrade head` against the remote `DATABASE_URL` before starting the API. The included `render.yaml` does this in the backend start command.

## How To Deploy The Frontend

Vercel deployment from GitHub:

1. Push the repository to GitHub.
2. Import the repo in Vercel.
3. Set the Vercel project root directory to `frontend`.
4. Set `NEXT_PUBLIC_API_BASE_URL` to your deployed backend URL, for example `https://recallbox-api.onrender.com`.
5. If auth is enabled, set `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY`.
6. Keep the default install/build commands:
   - Install: `npm install`
   - Build: `npm run build`
7. Deploy.

After the backend is deployed, update `FRONTEND_ORIGIN` on the backend host to your Vercel URL, for example `https://your-project.vercel.app`.

## How To Deploy The Backend

The backend must receive these environment variables from the hosting provider:

```bash
DATABASE_URL=postgresql+psycopg://...
FRONTEND_ORIGIN=https://your-project.vercel.app
DEFAULT_USER_EMAIL=demo@recallbox.local
ENABLE_AUTH=true
SUPABASE_URL=https://YOUR_PROJECT.supabase.co
SUPABASE_ANON_KEY=YOUR_SUPABASE_ANON_OR_PUBLISHABLE_KEY
ENABLE_LLM=false
LLM_PROVIDER=huggingface
HUGGINGFACE_CHAT_MODEL=openai/gpt-oss-20b
OPENAI_CHAT_MODEL=gpt-4.1-mini
RAG_MIN_SIMILARITY=0.55
RAG_TOP_K=5
RAG_CHUNK_SIZE=1800
RAG_CHUNK_OVERLAP=200
RAG_MAX_CHUNKS_PER_ITEM=4
RAG_MAX_CONTENT_CHARS=7000
RAG_MAX_ANSWER_TOKENS=400
ENABLE_EMBEDDINGS=false
EMBEDDING_MIN_SIMILARITY=0.55
EMBEDDING_PROVIDER=huggingface
HUGGINGFACE_TOKEN=
HUGGINGFACE_EMBEDDING_MODEL=BAAI/bge-small-en-v1.5
OPENAI_API_KEY=
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_EMBEDDING_DIMENSIONS=1536
```

Use `ENABLE_AUTH=false` only for demo/local deployments that should use the single default user.

Render option:

1. Push the repository to GitHub.
2. Create a new Render web service from the repo, or use the included `render.yaml`.
3. Use `backend` as the root directory.
4. Use build command:
   ```bash
   pip install -r requirements.txt
   ```
5. Use pre-deploy command:
   ```bash
   alembic upgrade head
   ```
6. Use start command:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port $PORT
   ```
7. Add the environment variables above.
8. Set auto-deploy to run after CI checks pass.
9. Deploy and verify `/health`.

Railway option:

1. Create a Railway service from the GitHub repo.
2. Set the service root to `backend`.
3. Add a Postgres plugin or use an external Postgres provider.
4. Set `DATABASE_URL`, `FRONTEND_ORIGIN`, and the other backend env vars.
5. Use the same start command:
   ```bash
   alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT
   ```

Fly.io option:

1. Use `backend/Dockerfile` as the app image.
2. Set secrets with `fly secrets set DATABASE_URL=... FRONTEND_ORIGIN=...`.
3. Run migrations with a one-off command before or during release:
   ```bash
   alembic upgrade head
   ```
4. Start the container with Uvicorn.

## API Overview

```http
POST /items
POST /rag/ask
GET /items?q=keyword&platform=web&tag=profile&date_from=2026-01-01&date_to=2026-01-31&semantic=false&limit=50&offset=0
GET /items/tags
GET /items/{id}
PATCH /items/{id}
DELETE /items/{id}
```

`POST /rag/ask` accepts:

```json
{
  "question": "Why do Kafka consumers rebalance?",
  "history": [],
  "top_k": 5
}
```

The response includes `answer`, `citations`, `mode`, and the answer-model name. `mode` is `llm`, `retrieval_only`, or `no_context`.

`PATCH /items/{id}` accepts:

```json
{
  "title": "Clear custom title",
  "note": "updated note",
  "thumbnail_url": "https://example.com/image.jpg",
  "tags": ["kafka", "interview"]
}
```

`POST /items` accepts either a plain URL or share text containing a URL:

```json
{
  "url": "我在小红书收获了18.9K次赞与收藏，来看看我的主页>> https://xhslink.com/m/1MNi9bPOhUm",
  "note": "creator to revisit"
}
```

The backend stores the extracted URL and may add tags such as `profile`, `collection`, or `post`.

## How To Contribute

1. Fork the repository.
2. Create a feature branch.
3. Keep changes focused and easy to review.
4. Do not commit secrets, `.env` files, local database dumps, or generated build output.
5. Run backend migrations and checks before opening a pull request.
6. Run the frontend locally and verify the main save/search/edit/delete flow.
7. Open a pull request with a short description, screenshots for UI changes, and any migration notes.

## Roadmap

V1:

- Web app only.
- Save links manually.
- Extract basic metadata.
- Add and edit notes and tags.
- Keyword search.
- Platform, tag, and date filters.
- Remote deployment.
- Open-source GitHub repo.

V1.5:

- Add account authentication and move from the default demo user to real per-user saved items. Implemented with Supabase Auth.
- Add optional semantic search using Hugging Face or OpenAI embeddings. Implemented behind `ENABLE_EMBEDDINGS`.
- Use `pgvector` with Postgres and track provider/model metadata.
- Generate embeddings for title, description, note, and tags.
- Support natural language search such as "that Kafka rebalance video" or "SF photography spot".
- Add an optional Chrome extension to save the current page and right-click save a link.
- Add a background worker or queue if metadata extraction becomes slow.

V2:

- Add article-content ingestion, chunk embeddings, grounded answers, citations, and follow-up context. Implemented on `feature/v2-rag`.
- Add RAG evaluation datasets and retrieval/groundedness metrics.
- Add explicit agent tools for searching, inspecting, summarizing, and organizing saved content.
- Add resurfacing suggestions based on recent search behavior or user context.
- Example: "You searched for Kafka. Here are 3 related items you saved before."
- Add collections or folders if needed.
- Add import/export.
- Add analytics for most saved topics, stale saved items, and recently resurfaced useful items.
- Improve the mobile experience with PWA support.

## License

MIT
