# Frontend image. Build context is the repo root. P0 runs the Vite dev server with the
# placeholder shell; the real UI lands in P6. Production build target is added later.
FROM node:22-alpine

WORKDIR /app

COPY web/package.json ./
COPY web/package-lock.json* ./
RUN npm install

COPY web/ ./

EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]
