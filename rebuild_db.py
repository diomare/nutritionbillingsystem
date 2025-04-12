from app import app, db

with app.app_context():
    print("Eliminazione delle tabelle esistenti...")
    db.drop_all()
    print("Creazione delle nuove tabelle...")
    db.create_all()
    print("Database ricreato con successo!")