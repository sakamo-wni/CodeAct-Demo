# ---- 1️⃣ ベースイメージ ---------------------------------
    FROM python:3.11-slim AS base

    # ---- 2️⃣ システム依存ライブラリ（必要最小限） ----------
    RUN apt-get update && \
        apt-get install -y --no-install-recommends gcc g++ build-essential && \
        rm -rf /var/lib/apt/lists/*
    
    # ---- 3️⃣ Poetry インストール ----------------------------
    ENV POETRY_VERSION=1.8.2
    RUN pip install "poetry==$POETRY_VERSION"
    
    # ---- 4️⃣ 作業ディレクトリ設定 ----------------------------
    WORKDIR /code
    
    # ---- 5️⃣ pyproject.toml と poetry.lock をコピー ---------
    COPY pyproject.toml poetry.lock* /code/
    COPY app /code/app

    # ---- 6️⃣ 依存インストール（本番のみ） -------------------
    RUN poetry config virtualenvs.create false \
     && poetry install --no-dev --only main
    
    # ---- 7️⃣ アプリコードコピー ------------------------------
    COPY app /code/app
    
    # ---- 8️⃣ ポート環境変数と起動コマンド -------------------
    ENV PORT=7000
    CMD ["poetry", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7000"]
    