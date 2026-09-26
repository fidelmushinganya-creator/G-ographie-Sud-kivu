from database import get_db
from werkzeug.security import generate_password_hash


username = input("Nom d'utilisateur admin : ").strip()
password = input("Mot de passe admin : ").strip()


if not username or not password:
    print("Erreur : le nom et le mot de passe sont obligatoires.")
    exit()


conn = get_db()


existing = conn.execute(
    "SELECT id FROM users WHERE username = ?",
    (username,)
).fetchone()


if existing:
    print("Cet administrateur existe déjà.")
    conn.close()
    exit()


password_hash = generate_password_hash(password)


conn.execute(
    """
    INSERT INTO users (username, password, role)
    VALUES (?, ?, ?)
    """,
    (username, password_hash, "admin")
)


conn.commit()
conn.close()


print()
print("================================")
print(" ADMINISTRATEUR CRÉÉ AVEC SUCCÈS")
print("================================")
print(f"Nom : {username}")
print("Mot de passe : enregistré de manière sécurisée")
