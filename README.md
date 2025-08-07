# SAC - Sistema de Autenticación

Este proyecto implementa una pantalla de login moderna usando React con Tailwind CSS para el frontend y Django REST Framework para el backend.

## Características

- **Frontend**: React con Tailwind CSS
- **Backend**: Django REST Framework
- **Autenticación**: Token-based authentication
- **Diseño**: Interfaz moderna y responsive

## Estructura del Proyecto

```
sac/
├── backend/          # Django backend
│   ├── api/         # Aplicación de API
│   ├── backend/     # Configuración principal
│   └── manage.py
├── frontend/        # React frontend
│   ├── src/
│   │   ├── components/
│   │   │   └── Login.js
│   │   └── App.js
│   └── package.json
└── README.md
```

## Instalación y Ejecución

### Backend (Django)

1. **Navegar al directorio backend:**
   ```bash
   cd backend
   ```

2. **Instalar dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Ejecutar migraciones:**
   ```bash
   python manage.py migrate
   ```

4. **Crear superusuario (opcional):**
   ```bash
   python manage.py createsuperuser
   ```

5. **Ejecutar el servidor:**
   ```bash
   python manage.py runserver
   ```

El backend estará disponible en: `http://localhost:8000`

### Frontend (React)

1. **Navegar al directorio frontend:**
   ```bash
   cd frontend
   ```

2. **Instalar dependencias:**
   ```bash
   npm install
   ```

3. **Ejecutar el servidor de desarrollo:**
   ```bash
   npm start
   ```

El frontend estará disponible en: `http://localhost:3000`

## API Endpoints

### Autenticación

- `POST /api/auth/login/` - Iniciar sesión
- `POST /api/auth/logout/` - Cerrar sesión
- `GET /api/auth/user/` - Obtener información del usuario
- `POST /api/auth/register/` - Registrar nuevo usuario

### Ejemplo de uso del login:

```json
POST /api/auth/login/
{
  "username": "admin",
  "password": "admin123"
}
```

## Credenciales de Prueba

- **Usuario**: admin
- **Contraseña**: admin123

## Características del Frontend

- Diseño responsive con Tailwind CSS
- Validación de formularios
- Manejo de estados de carga
- Mensajes de error y éxito
- Toggle para mostrar/ocultar contraseña
- Animaciones y transiciones suaves

## Tecnologías Utilizadas

### Frontend
- React 19.1.1
- Tailwind CSS 3.4.17
- React Scripts 5.0.1

### Backend
- Django 5.2.4
- Django REST Framework
- Django CORS Headers
- SQLite (base de datos)

## Docker (Opcional)

Para ejecutar con Docker:

```bash
docker-compose up --build
```

## Desarrollo

### Agregar nuevas funcionalidades

1. **Backend**: Agregar nuevas vistas en `backend/api/views.py`
2. **Frontend**: Crear nuevos componentes en `frontend/src/components/`
3. **URLs**: Configurar rutas en `backend/api/urls.py`

### Estructura de archivos importantes

- `frontend/src/components/Login.js` - Componente principal de login
- `backend/api/views.py` - Vistas de autenticación
- `backend/api/urls.py` - Rutas de la API
- `backend/backend/settings.py` - Configuración de Django

## Notas

- El proyecto incluye CORS configurado para desarrollo
- Los tokens de autenticación se almacenan en localStorage
- El diseño es completamente responsive
- Incluye manejo de errores tanto en frontend como backend 