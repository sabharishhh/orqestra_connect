FROM node:20-alpine

WORKDIR /app

# Copy package files and install dependencies
COPY package*.json ./
RUN npm install

# Copy the rest of the code 
# (In dev, your docker-compose volumes will override this, which is what we want)
COPY . .

# Expose the Vite development port
EXPOSE 5173

# Default command to start the Vite dev server
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]