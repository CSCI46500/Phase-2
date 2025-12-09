FROM node:25-slim

# Set working directory
WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy application code
COPY . .

# Build the production bundle
RUN npm run build

# Install serve to host the production build
RUN npm install -g serve

# Expose port
EXPOSE 5173

# Serve the built files
CMD ["serve", "-s", "dist", "-l", "5173"]