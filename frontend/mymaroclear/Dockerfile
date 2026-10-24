FROM node:18

WORKDIR /app

# Copiez package.json
COPY package*.json ./

# Installez les dépendances
RUN npm install

# Copiez le reste du code
COPY . .

# Exposez le port
EXPOSE 3000

# Commande de démarrage
CMD ["npm", "start"]