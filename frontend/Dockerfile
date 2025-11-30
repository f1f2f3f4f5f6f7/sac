FROM node:20-alpine

WORKDIR /app

# Copiar archivos de configuración de dependencias
COPY package*.json ./

# Instalar dependencias
RUN npm ci

# Copiar el resto de los archivos
COPY . .

# Exponer el puerto de desarrollo
EXPOSE 4200

# Comando para iniciar Angular con live reload con polling
CMD ["npm", "start", "--", "--host", "0.0.0.0", "--poll=1000"]
