# -------------------------------------------------------------
# Stage 1: Build Frontend & Install Nodemailer
# -------------------------------------------------------------
FROM node:22-alpine AS frontend-builder
WORKDIR /app

# Install root dependencies
COPY package*.json ./
RUN npm install

# Copy source and build static frontend bundle
COPY . .
RUN npm run build

# Install backend nodemailer dependencies
WORKDIR /app/backend
COPY backend/package*.json ./
RUN npm install --production

# -------------------------------------------------------------
# Stage 2: Python Runtime with Node.js support for Nodemailer
# -------------------------------------------------------------
FROM python:3.11-slim

# Install Node.js (for backend/mailer.js) and curl
RUN apt-get update && apt-get install -y --no-install-recommends \
    nodejs \
    npm \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY backend/requirements.txt ./backend/
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy project source
COPY . .

# Copy built frontend dist and backend node_modules from builder
COPY --from=frontend-builder /app/dist ./dist
COPY --from=frontend-builder /app/backend/node_modules ./backend/node_modules

# Environment & Port
ENV PORT=8000
ENV PYTHONUNBUFFERED=1
EXPOSE 8000

# Start FastAPI application
CMD ["sh", "-c", "python -m uvicorn backend.server:app --host 0.0.0.0 --port ${PORT:-8000}"]
