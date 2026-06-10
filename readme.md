# 🩸 Frotis AI — Sistema de Análisis Inteligente de Frotis Sanguíneos

Frotis AI es una aplicación web full-stack de última generación diseñada para bioquímica clínica. Utiliza modelos de Inteligencia Artificial para la detección y clasificación automatizada de leucocitos (glóbulos blancos) a partir de imágenes de frotis de sangre digitalizadas.

La aplicación integra una arquitectura ágil, procesamiento de imágenes en tiempo real y una interfaz moderna.

---

## 🚀 Pila Tecnológica (Tech Stack)

### Frontend
- **Framework**: React 18 & TypeScript (buildeado con **Vite**)
- **Estilos**: Vanilla CSS con un sistema robusto de variables y tokens de diseño
- **Ruteo**: React Router v6
- **Cliente HTTP**: Axios (con interceptores para inyección de JWT, manejo de errores y reintentos automáticos)
- **Contextos**: Context API para notificaciones globales (`ToastContext`) y control de autenticación (`AuthContext`)

### Backend
- **Framework**: FastAPI (Python 3.11)
- **Base de Datos**: PostgreSQL
- **ORM & Migraciones**: SQLAlchemy 2.0 y Alembic
- **Pipeline de IA**:
  - **Inferencia**: **ONNX Runtime** ejecutando un modelo **YOLOv8n** optimizado y serializado
  - **Procesamiento de imágenes**: OpenCV-headless y Pillow
- **Almacenamiento de Muestras**: Cloudinary (Cloud Storage)
- **Seguridad**: Autenticación JWT y encriptación de contraseñas con Passlib (Bcrypt)

### DevOps & Despliegue
- **Contenedores**: Docker & Docker Compose
- **Platform-as-a-Service**: Compatible con Heroku via `heroku.yml` (construcción multi-stage Docker)

---

## 🛠️ Características Principales (Features)

1. **Detección Automatizada con IA**: Carga de imágenes de frotis de sangre (formatos JPG, PNG). El backend procesa, detecta la ubicación física y clasifica los leucocitos en 10 categorías clínicas en menos de un segundo.
2. **Consolidación de Métricas**: Calcula en tiempo real la cantidad total de células detectadas y la distribución porcentual correspondiente a cada clase (neutrófilos, linfocitos, monocitos, eosinófilos, basófilos, etc.).
3. **Bucle de Feedback Interactivo (Corrección Manual)**:
   - **Marcar Falsos Positivos**: El bioquímico puede remover detecciones erróneas generadas por el modelo de IA.
   - **Cambiar Tipo Celular**: Opción de corregir y reclasificar el tipo celular de una detección existente.
   - **Dibujar Células Manualmente**: Permite trazar un rectángulo (`bbox`) arrastrando el ratón sobre la imagen para añadir células omitidas por el modelo.
4. **Baja Lógica de Análisis (Soft Delete)**: Posibilidad de eliminar lógicamente análisis anteriores del historial personal (`DELETE /analysis/{id}`). El backend registra la fecha de baja del análisis y lo excluye automáticamente de listados y consultas futuras por privacidad.
5. **Autenticación e Inicio de Sesión Persistente**:
   - Registro e inicio de sesión seguro.
   - Sesiones persistentes durante 14 días (2 semanas) usando cookies del navegador con protección contra ataques CSRF.
6. **Diseño Mobile-First**: Panel lateral de navegación (`Sidebar`) colapsable de tipo cajón deslizable para pantallas de dispositivos móviles (≤768px), con fondo traslúcido y auto-cierre dinámico.

---

## 📁 Estructura del Proyecto

```text
├── backend/                  # Código del servidor FastAPI
│   ├── app/
│   │   ├── api/routes/       # Controladores (auth, analyze, predict)
│   │   ├── core/             # Configuración y utilidades de seguridad
│   │   ├── ml/               # Pipeline de YOLOv8n y modelo.onnx
│   │   ├── models/           # Definiciones de tablas (SQLAlchemy)
│   │   ├── schemas/          # Modelos de validación (Pydantic)
│   │   ├── service/          # Lógica de negocio (procesamiento de imágenes, auth)
│   │   └── tests/            # Pruebas automatizadas (Pytest)
│   ├── alembic/              # Scripts de migración de base de datos
│   ├── seed_analysis.py      # Script de semilla para base de datos local
│   ├── requirements.txt      # Dependencias del backend
│   └── Dockerfile            # Construcción de la imagen del backend
│
├── frontend/                 # Código de la aplicación web React
│   ├── src/
│   │   ├── components/       # Componentes reusables (ImageViewer, Sidebar, etc.)
│   │   ├── contexts/         # Contextos globales (Auth, Toast)
│   │   ├── pages/            # Vistas (LoginPage, DashboardPage, WorkspacePage, etc.)
│   │   ├── services/         # Cliente API Axios
│   │   ├── styles/           # CSS global y tokens de diseño
│   │   └── types/            # Tipos estáticos TypeScript
│   └── package.json          # Dependencias y scripts del frontend
│
├── Dockerfile                # Configuración multi-stage para producción (Heroku)
├── compose.yaml              # Configuración local de Docker Compose
└── readme.md                 # Documentación general del proyecto
```

---

## ⚙️ Configuración y Ejecución Local

### Opción A: Ejecutar mediante Docker Compose (Recomendado)

1. Asegúrate de tener instalado [Docker](https://www.docker.com/) y que el servicio esté activo.
2. Copia el archivo `.env.example` en la raíz del proyecto y renómbralo a `.env`:
   ```bash
   cp .env.example .env
   ```
   *Nota: Completa las variables de entorno necesarias, en particular los credenciales de Cloudinary (`CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET`).*

3. Construye y levanta los contenedores:
   ```bash
   docker compose up --build
   ```

4. Corre la migración de base de datos y los datos de semilla en el contenedor de backend:
   ```bash
   # Aplicar migraciones de Alembic
   docker exec -it frotis_backend alembic upgrade head
   
   # Sembrar la base de datos con un usuario de prueba (test@frotis.com / Password123)
   docker exec -it frotis_backend python seed_analysis.py
   ```

5. Abre [http://localhost:5174](http://localhost:5174) (o el puerto que te indique tu servidor Vite) para acceder a la aplicación.

---

### Opción B: Ejecución Manual en Entornos de Desarrollo

Si prefieres ejecutar el backend y el frontend por separado de forma nativa en tu sistema operativo:

#### Requisitos de Backend (Python 3.11)
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # En Windows usa: .venv\Scripts\activate
pip install -r requirements.txt
# Configura tu archivo .env local
uvicorn app.main:app --reload
```

#### Requisitos de Frontend (NodeJS + pnpm)
```bash
cd frontend
pnpm install
pnpm run dev
```

---

## 🧪 Testing

### Pruebas de Backend (FastAPI + Pytest)
El backend incluye una amplia cobertura de pruebas de endpoints, seguridad e inferencia. Para correrlas ejecuta:
```bash
# Si corres en Docker:
docker exec -it frotis_backend pytest

# Si corres de forma nativa:
cd backend
pytest
```
