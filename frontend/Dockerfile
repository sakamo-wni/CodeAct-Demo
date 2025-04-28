# frontend/Dockerfile
# --- build stage --------------------------------------------------
    FROM node:20-bookworm AS builder
    WORKDIR /app
    
    # package.json と lock ファイルをコピーして依存解決
    COPY package*.json ./
    RUN npm ci --prefer-offline --no-audit
    
    # 残りのソースをコピー → ビルド
    COPY . .
    RUN npm run build
    
    # --- run stage ----------------------------------------------------
    FROM node:20-bookworm AS runner
    WORKDIR /app
    
    # production 依存だけインストール
    COPY package*.json ./
    RUN npm ci --only=production --prefer-offline --no-audit
    
    # Next.js の静的ファイルをコピー
    COPY --from=builder /app/.next ./.next
    COPY --from=builder /app/public ./public
    
    ENV NODE_ENV=production
    # 3000 番でリッスン
    EXPOSE 3000
    
    CMD ["npm", "start"]
    