# Admin (ticket-counter) frontend image. Build context is the repo root.
FROM node:22-alpine

WORKDIR /app

COPY admin/package.json ./
COPY admin/package-lock.json* ./
RUN npm install

COPY admin/ ./

EXPOSE 5174
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5174"]
