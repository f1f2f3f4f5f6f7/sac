FROM node:20-alpine

WORKDIR /app

# Copiar el resto de los archivos
COPY . .

# Eliminar dependencias
RUN rm -rf node_modules
RUN rm -rf package-lock.json


# Instalar dependencias
RUN npm i

# Exponer el puerto de desarrollo
EXPOSE 4200

# Comando para iniciar Angular con live reload con polling
CMD ["npm", "start", "--", "--host", "0.0.0.0"]
