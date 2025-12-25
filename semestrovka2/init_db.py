import psycopg2
import hashlib

conn = psycopg2.connect(
    dbname="basketball_bookings",
    user="postgres",
    password="basketbollistkaa",
    host="localhost"
)
cur = conn.cursor()

# пользователи
cur.execute("""
    CREATE TABLE users (
        id SERIAL PRIMARY KEY,
        username VARCHAR(50) UNIQUE NOT NULL,
        email VARCHAR(100) UNIQUE NOT NULL,
        password_hash VARCHAR(255) NOT NULL,
        role VARCHAR(20) DEFAULT 'user',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")

# профили
cur.execute("""
    CREATE TABLE user_profiles (
        user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
        full_name VARCHAR(100),
        phone VARCHAR(20),
        skill_level VARCHAR(20) DEFAULT 'beginner',
        preferred_time VARCHAR(20),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")

# корты
cur.execute("""
    CREATE TABLE courts (
        id SERIAL PRIMARY KEY,
        name VARCHAR(100) NOT NULL,
        location TEXT,
        price_per_hour DECIMAL(10,2) DEFAULT 0
    )
""")

# брони
cur.execute("""
    CREATE TABLE bookings (
        id SERIAL PRIMARY KEY,
        court_id INTEGER REFERENCES courts(id) ON DELETE CASCADE,
        user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
        start_time TIMESTAMP NOT NULL,
        end_time TIMESTAMP NOT NULL,
        status VARCHAR(20) DEFAULT 'active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")

# избранное
cur.execute("""
    CREATE TABLE favorites (
        user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
        court_id INTEGER REFERENCES courts(id) ON DELETE CASCADE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (user_id, court_id)
    )
""")



conn.commit()
cur.close()
conn.close()