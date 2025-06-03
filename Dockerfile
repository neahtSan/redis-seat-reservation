# Use Node.js LTS image
FROM node:18-alpine

# Install pnpm globally
RUN npm install -g pnpm

# Create app directory
WORKDIR /usr/src/app

# Install app dependencies (all, including dev)
COPY backend/pnpm-lock.yaml ./
COPY backend/package.json ./
RUN pnpm install

# Copy the source code and build files
COPY backend/tsconfig*.json ./
COPY backend/src ./src

# Build the app
RUN pnpm build

# Remove devDependencies for smaller image
RUN pnpm prune --prod

# Expose the NestJS app port
EXPOSE 3000

# Run the compiled app (assuming output in dist folder)
CMD ["node", "dist/main.js"]
