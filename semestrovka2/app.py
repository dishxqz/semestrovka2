from flask import Flask, request, session, redirect, url_for, render_template
import psycopg2
from psycopg2.extras import RealDictCursor
import hashlib

app = Flask(__name__)
app.secret_key = 'admin'


def get_db():
    conn = psycopg2.connect(
        dbname="basketball_bookings",
        user="postgres",
        password="basketbollistkaa",
        host="localhost",
        cursor_factory=RealDictCursor
    )
    return conn


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


# пользователи

@app.route('/')
def index():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM courts")
    courts = cur.fetchall()

    cur.execute("""
        SELECT b.*, c.name as court_name, u.username 
        FROM bookings b
        JOIN courts c ON b.court_id = c.id
        JOIN users u ON b.user_id = u.id
        ORDER BY b.start_time DESC
        LIMIT 5
    """)
    bookings = cur.fetchall()

    cur.close()
    conn.close()

    return render_template('index.html', courts=courts, bookings=bookings)


@app.route("/users/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if not username or not password:
            return render_template('users/login.html', error="нужно указать имя пользователя и пароль")

        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT id, username, password_hash, role FROM users WHERE username = %s", (username,))
        user = cur.fetchone()
        cur.close()
        conn.close()

        if not user or user['password_hash'] != hash_password(password):
            return render_template('users/login.html', error="Неверный логин или пароль")

        session['user_id'] = user['id']
        session['username'] = user['username']
        session['role'] = user['role']
        return redirect('/')

    return render_template('users/login.html')


@app.route("/users/register", methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')

        if not username or not password or not email:
            return render_template('users/register.html', error="Все поля обязательны для заполнения!")

        conn = get_db()
        cur = conn.cursor()

        cur.execute("SELECT id FROM users WHERE username = %s OR email = %s", (username, email))

        if cur.fetchone():
            cur.close()
            conn.close()
            return render_template('users/register.html', error="Пользователь с таким именем или email уже существует")

        password_hash = hash_password(password)
        cur.execute("""
            INSERT INTO users (username, email, password_hash, role)
            VALUES (%s, %s, %s, 'user')
            RETURNING id
        """, (username, email, password_hash))

        user_id = cur.fetchone()['id']
        conn.commit()
        cur.close()
        conn.close()

        session['user_id'] = user_id
        session['username'] = username
        session['role'] = 'user'
        return redirect('/')

    return render_template('users/register.html')


@app.route("/users/profile")
def profile():
    user_id = session.get('user_id')
    username = session.get('username')

    if not user_id:
        return redirect('/users/login')

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT u.*, up.full_name, up.phone, up.skill_level, up.preferred_time
        FROM users u
        LEFT JOIN user_profiles up ON u.id = up.user_id
        WHERE u.id = %s
    """, (user_id,))
    user = cur.fetchone()

    cur.execute("""
        SELECT b.*, c.name as court_name
        FROM bookings b
        JOIN courts c ON b.court_id = c.id
        WHERE b.user_id = %s
        ORDER BY b.start_time DESC
    """, (user_id,))
    bookings = cur.fetchall()

    cur.close()
    conn.close()

    return render_template('users/profile.html', user=user, bookings=bookings)

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect('/')


@app.route("/users/profile/edit", methods=['GET', 'POST'])
def profile_edit():
    if 'user_id' not in session:
        return redirect('/users/login')

    conn = get_db()
    cur = conn.cursor()

    if request.method == 'POST':
        full_name = request.form.get('full_name')
        phone = request.form.get('phone')
        skill_level = request.form.get('skill_level')
        preferred_time = request.form.get('preferred_time')

        # проверка на наличие профиля
        cur.execute("SELECT 1 FROM user_profiles WHERE user_id = %s", (session['user_id'],))

        if cur.fetchone():
            cur.execute("""
                UPDATE user_profiles 
                SET full_name = %s, phone = %s, skill_level = %s, preferred_time = %s
                WHERE user_id = %s
            """, (full_name, phone, skill_level, preferred_time, session['user_id']))
        else:
            cur.execute("""
                INSERT INTO user_profiles (user_id, full_name, phone, skill_level, preferred_time)
                VALUES (%s, %s, %s, %s, %s)
            """, (session['user_id'], full_name, phone, skill_level, preferred_time))

        conn.commit()
        cur.close()
        conn.close()
        return redirect('/users/profile')

    # получить данные профиля
    cur.execute("""
        SELECT u.*, up.full_name, up.phone, up.skill_level, up.preferred_time
        FROM users u
        LEFT JOIN user_profiles up ON u.id = up.user_id
        WHERE u.id = %s
    """, (session['user_id'],))

    user = cur.fetchone()
    cur.close()
    conn.close()

    return render_template('users/profile_edit.html', user=user)

# корты

@app.route("/court")
def courts():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM courts ORDER BY id")
    courts = cur.fetchall()

    # избранные для текущего юзера
    favorites = []
    if 'user_id' in session:
        cur.execute("SELECT court_id FROM favorites WHERE user_id = %s",
                    (session['user_id'],))
        favorites = [row['court_id'] for row in cur.fetchall()]

    cur.close()
    conn.close()

    return render_template('courts/list.html',
                           courts=courts,
                           favorites=favorites)


@app.route("/favorites")
def favorites():
    if 'user_id' not in session:
        return redirect('/users/login')

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT c.* FROM courts c
        JOIN favorites f ON c.id = f.court_id
        WHERE f.user_id = %s
        ORDER BY c.name
    """, (session['user_id'],))

    favorites = cur.fetchall()
    cur.close()
    conn.close()

    return render_template('courts/favorites.html', favorites=favorites)


@app.route("/favorites/toggle/<int:court_id>")
def favorites_toggle(court_id):
    if 'user_id' not in session:
        return redirect('/users/login')

    conn = get_db()
    cur = conn.cursor()

    # проверка
    cur.execute("SELECT 1 FROM favorites WHERE user_id = %s AND court_id = %s",
                (session['user_id'], court_id))

    if cur.fetchone():
        # удалить из избранного
        cur.execute("DELETE FROM favorites WHERE user_id = %s AND court_id = %s",
                    (session['user_id'], court_id))
    else:
        # добавить в избранные
        cur.execute("INSERT INTO favorites (user_id, court_id) VALUES (%s, %s)",
                    (session['user_id'], court_id))

    conn.commit()
    cur.close()
    conn.close()

    return redirect(request.referrer or '/courts')

@app.route("/court/create", methods=['POST'])
def court_create():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect('/')

    name = request.form.get('name')
    location = request.form.get('location')
    price = request.form.get('price_per_hour')

    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO courts (name, location, price_per_hour)
        VALUES (%s, %s, %s)
    """, (name, location, price))
    conn.commit()
    cur.close()
    conn.close()

    return redirect('/court')


@app.route("/court/edit/<int:court_id>", methods=['GET', 'POST'])
def court_edit(court_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect('/')

    conn = get_db()
    cur = conn.cursor()

    if request.method == 'POST':
        name = request.form.get('name')
        location = request.form.get('location')
        price = request.form.get('price_per_hour')

        cur.execute("""
            UPDATE courts 
            SET name = %s, location = %s, price_per_hour = %s
            WHERE id = %s
        """, (name, location, price, court_id))
        conn.commit()

        cur.close()
        conn.close()
        return redirect('/court')

    cur.execute("SELECT * FROM courts WHERE id = %s", (court_id,))
    court = cur.fetchone()

    cur.close()
    conn.close()

    return render_template('courts/edit.html', court=court)


@app.route("/court/delete/<int:court_id>")
def court_delete(court_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect('/')

    conn = get_db()
    cur = conn.cursor()

    # проверка на наличие брони
    cur.execute("SELECT COUNT(*) as cnt FROM bookings WHERE court_id = %s AND status = 'active'", (court_id,))
    result = cur.fetchone()

    if result['cnt'] > 0:
        cur.close()
        conn.close()
        return "Нельзя удалить корт с активными бронями!", 400

    cur.execute("DELETE FROM courts WHERE id = %s", (court_id,))
    conn.commit()

    cur.close()
    conn.close()
    return redirect('/court')

# брони

@app.route("/booking/owner_list")
def bookings():
    if 'user_id' not in session:
        return redirect('/users/login')

    conn = get_db()
    cur = conn.cursor()

    if session.get('role') == 'admin':
        cur.execute("""
            SELECT b.*, c.name as court_name, u.username
            FROM bookings b
            JOIN courts c ON b.court_id = c.id
            JOIN users u ON b.user_id = u.id
            ORDER BY b.start_time DESC
        """)
    else:
        cur.execute("""
            SELECT b.*, c.name as court_name
            FROM bookings b
            JOIN courts c ON b.court_id = c.id
            WHERE b.user_id = %s
            ORDER BY b.start_time DESC
        """, (session['user_id'],))

    bookings = cur.fetchall()
    cur.close()
    conn.close()

    return render_template('booking/owner_list.html', bookings=bookings)


@app.route("/booking/create", methods=['GET', 'POST'])
def booking_create():
    if 'user_id' not in session:
        return redirect('/users/login')

    conn = get_db()
    cur = conn.cursor()

    if request.method == 'POST':
        court_id = request.form.get('court_id')
        date = request.form.get('date')
        start_time = request.form.get('start_time')
        hours = request.form.get('hours', '1')

        start_datetime = f"{date} {start_time}"

        from datetime import datetime, timedelta
        dt_start = datetime.strptime(start_datetime, '%Y-%m-%d %H:%M')
        dt_end = dt_start + timedelta(hours=int(hours))
        end_datetime = dt_end.strftime('%Y-%m-%d %H:%M')

        cur.execute("""
            SELECT COUNT(*) as cnt FROM bookings 
            WHERE court_id = %s 
            AND status = 'active'
            AND NOT (end_time <= %s OR start_time >= %s)
        """, (court_id, start_datetime, end_datetime))

        if cur.fetchone()['cnt'] > 0:
            cur.execute("SELECT * FROM courts WHERE id = %s", (court_id,))
            court = cur.fetchone()
            cur.close()
            conn.close()
            return render_template('booking/create.html',
                                   court=court,
                                   error="Время занято")

        cur.execute("""
            INSERT INTO bookings (court_id, user_id, start_time, end_time, status)
            VALUES (%s, %s, %s, %s, 'active')
        """, (court_id, session['user_id'], start_datetime, end_datetime))

        conn.commit()
        cur.close()
        conn.close()
        return redirect('/booking/owner_list')

    court_id = request.args.get('court_id')
    if not court_id:
        return redirect('/')

    cur.execute("SELECT * FROM courts WHERE id = %s", (court_id,))
    court = cur.fetchone()
    cur.close()
    conn.close()

    return render_template('booking/create.html', court=court)


@app.route("/booking/cancel/<int:booking_id>")
def booking_cancel(booking_id):
    if 'user_id' not in session:
        return redirect('/users/login')

    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT user_id FROM bookings WHERE id = %s", (booking_id,))
    booking = cur.fetchone()

    if not booking:
        return redirect('/booking/owner_list')

    if booking['user_id'] != session['user_id'] and session.get('role') != 'admin':
        return redirect('/booking/owner_list')

    cur.execute("UPDATE bookings SET status = 'cancelled' WHERE id = %s", (booking_id,))
    conn.commit()
    cur.close()
    conn.close()

    return redirect('/booking/owner_list')


if __name__ == "__main__":
    app.run(debug=True)