FROM node:20

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

EXPOSE 5173

# ✅ Remplacez "npm start" par "npm run dev"
CMD ["npm", "run", "dev", "--", "--host"]