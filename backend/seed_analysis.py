# seed_analysis.py
import sys
import os
sys.path.append(os.path.abspath('.'))

from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.usuario import Usuario
from app.models.analisis import Analisis, Deteccion
from app.models.clases_celulas import ClaseCelula
from app.core.security import hash_password

def seed():
    db = SessionLocal()
    try:
        # 1. Crear el usuario de prueba
        email = "test@frotis.com"
        user = db.query(Usuario).filter(Usuario.email == email).first()
        if not user:
            user = Usuario(
                email=email,
                password=hash_password("Password123")
            )
            db.add(user)
            db.flush()
            print(f"Usuario creado: {email}")
        else:
            print(f"Usuario ya existe: {email}")

        # 2. Inicializar clases celulares
        classes = ["Neutrófilo", "Linfocito", "Monocito", "Eosinófilo", "Basófilo"]
        class_map = {}
        for name in classes:
            c = db.query(ClaseCelula).filter(ClaseCelula.nombre == name).first()
            if not c:
                c = ClaseCelula(nombre=name)
                db.add(c)
                db.flush()
            class_map[name] = c.id
        print("Clases celulares inicializadas.")

        # 3. Crear análisis de prueba
        analisis = Analisis(
            usuario_id=user.id,
            imagen_url="https://res.cloudinary.com/demo/image/upload/sample.jpg",
            estado="COMPLETED"
        )
        db.add(analisis)
        db.flush()

        # 4. Crear detecciones asociadas
        det1 = Deteccion(
            analisis_id=analisis.id,
            clase_id=class_map["Neutrófilo"],
            confianza=0.94,
            bbox=[10.5, 20.0, 110.5, 120.0]
        )
        det2 = Deteccion(
            analisis_id=analisis.id,
            clase_id=class_map["Linfocito"],
            confianza=0.85,
            bbox=[150.0, 160.0, 250.0, 270.0]
        )
        db.add_all([det1, det2])
        db.commit()
        print(f"Análisis creado exitosamente!")
        print(f"ANALYSIS_ID={analisis.id}")

    except Exception as e:
        db.rollback()
        print(f"Error al sembrar datos: {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    seed()
