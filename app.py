"""
app.py  ──  AI 智慧羽球教練（正式上線版）
資料庫：Supabase PostgreSQL（免費雲端）
部署平台：Render.com（免費方案）
安全強化：密碼雜湊、環境變數、CSRF、速率限制、IDOR 防護
"""

import os
import re
import uuid

from flask import (
    Flask, render_template, request, redirect,
    url_for, session, g, flash, send_from_directory,
    jsonify, after_this_request, abort
)
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv

# 影片辨識模組（已移除 cv2.imshow / pyttsx3，可在伺服器執行）
from Long_Video import Long
from LongBackHand_Video import LongBackHand
from Short_Video import Short
from BackHandFlick_Video import BackHandFlick
from ForeHandFlick_Video import ForeHandFlick

# ─── 環境變數 ─────────────────────────────────────────────────────────────────
load_dotenv()   # 本機開發時讀取 .env；Render 上從環境變數面板讀取

# ─── Flask 初始化 ─────────────────────────────────────────────────────────────
app = Flask(__name__)

# [Security] SECRET_KEY 必須從環境變數讀取
_secret = os.environ.get('SECRET_KEY')
if not _secret:
    raise RuntimeError(
        "❌ 環境變數 SECRET_KEY 未設定！\n"
        "請執行：python -c \"import secrets; print(secrets.token_hex(32))\" 取得一組金鑰並設定。"
    )
app.config['SECRET_KEY'] = _secret

# [Security] CSRF 保護
csrf = CSRFProtect(app)

# [Security] 速率限制
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["300 per day", "60 per hour"],
    storage_uri="memory://"
)

# ─── 資料庫（Supabase PostgreSQL）────────────────────────────────────────────
DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    raise RuntimeError("❌ 環境變數 DATABASE_URL 未設定！請在 Render 或 .env 中設定 Supabase 連線字串。")

# Supabase/Render 有時回傳 postgres:// 前綴，SQLAlchemy 需要 postgresql://
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = os.environ.get('SQLALCHEMY_ECHO', 'false').lower() == 'true'
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,          # 自動偵測斷線並重連
    'pool_recycle': 280,            # Supabase 免費版 300 秒 idle 斷線，提前回收
    # 'connect_args': {'sslmode': 'require'},   # Supabase 強制 SSL
    'connect_args': {
        'sslmode': 'require',
        'options': '-c timezone=Asia/Taipei',
    },
    # Transaction mode pooler 需要關閉 prepared statements
    'execution_options': {'no_parameters': True},
}

db = SQLAlchemy(app)

# ─── 檔案上傳設定 ─────────────────────────────────────────────────────────────
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'wmv', 'flv', 'mkv', 'ogg', 'avc', 'avchd', 'mjpg', 'mpg', 'mpeg'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# [Security] 限制上傳大小（500 MB）
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024

def allowed_file(filename: str) -> bool:
    _, ext = os.path.splitext(filename)
    return ext[1:].lower() in ALLOWED_EXTENSIONS

# ─── 資料模型 ─────────────────────────────────────────────────────────────────
class User(db.Model):
    __tablename__ = 'user'
    id       = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(100), unique=True, nullable=False, index=True)
    password = db.Column(db.String(255), nullable=False)   # 儲存雜湊值

    def set_password(self, raw: str):
        """[Security] PBKDF2-SHA256 雜湊後儲存"""
        self.password = generate_password_hash(raw)

    def check_password(self, raw: str) -> bool:
        return check_password_hash(self.password, raw)

class Player(db.Model):
    __tablename__ = 'player'
    id                = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id           = db.Column(db.Integer, db.ForeignKey('user.id'))
    name              = db.Column(db.String(100))
    shot              = db.Column(db.String(100))
    training_progress = db.Column(db.Integer)
    complete_progress = db.Column(db.Integer)
    percentage        = db.Column(db.Float)
    date              = db.Column(db.TIMESTAMP, nullable=True, default=None)
    user              = relationship('User', backref='players')

# 自動建立資料表（首次啟動時）
with app.app_context():
    db.create_all()

# ─── 請求前後處理 ─────────────────────────────────────────────────────────────
@app.before_request
def load_user():
    g.user = None
    if 'username' in session:
        user = User.query.filter_by(username=session['username']).first()
        if user:
            g.user = user

@app.after_request
def add_security_headers(response):
    """[Security] HTTP 安全標頭"""
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    return response

# ─── 輔助裝飾器與函式 ─────────────────────────────────────────────────────────
def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            return redirect(url_for('login'))
        return view(*args, **kwargs)
    return wrapped

def get_player_or_403(player_id: int) -> Player:
    """[Security] 取得 Player 並驗證屬於目前登入用戶（防 IDOR）"""
    player = Player.query.get_or_404(player_id)
    if player.user_id != g.user.id:
        abort(403)
    return player

# ─── 路由：公開頁面 ───────────────────────────────────────────────────────────
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/menu')
def menu():
    return render_template('menu.html')

@app.route('/explanation')
def explanation():
    return render_template('explanation.html')

@app.route('/explanation_video')
def explanation_video():
    return render_template('explanation_video.html')

# ─── 路由：帳號管理 ───────────────────────────────────────────────────────────
@app.route('/register', methods=['GET', 'POST'])
@limiter.limit('10 per minute')
def register():
    if request.method == 'POST':
        username   = request.form.get('username', '').strip()
        password   = request.form.get('password', '')
        repassword = request.form.get('repassword', '')

        if not username or not password:
            flash('帳號與密碼不得為空', 'danger')
            return render_template('register.html')
        if password != repassword:
            flash('兩次密碼不一致', 'danger')
            return render_template('register.html')
        if User.query.filter_by(username=username).first():
            flash('帳號已被使用', 'danger')
            return render_template('register.html')

        u = User(username=username, password='')
        u.set_password(password)          # [Security] 雜湊後存入
        db.session.add(u)
        db.session.commit()
        flash('註冊成功，請登入', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
@limiter.limit('10 per minute')           # [Security] 防暴力破解
def login():
    if request.method == 'POST':
        session.clear()
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            g.user = user
            session['username'] = username
            return redirect(url_for('schedule'))
        flash('帳號或密碼錯誤', 'danger')   # [Security] 不區分帳號/密碼
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ─── 路由：進度表 ─────────────────────────────────────────────────────────────
@app.route('/schedule', methods=['GET', 'POST'])
@login_required
def schedule():
    players = Player.query.filter_by(user_id=g.user.id).all()

    if request.method == 'POST':
        selected_id = request.form.get('selected_id')

        if selected_id:
            player = get_player_or_403(int(selected_id))   # [Security] IDOR 防護
            action = request.form.get('action')
            if action == 'update':
                try:
                    tp = int(request.form.get('training_progress', '0'))
                    cp = int(request.form.get('complete_progress', '0'))
                    date = request.form.get('date')
                    if not date:
                        flash('日期為必填項目', 'danger')
                        return redirect(url_for('schedule'))
                    player.name              = request.form.get('name')
                    player.shot              = request.form.get('shot')
                    player.training_progress = tp
                    player.complete_progress = cp
                    player.percentage        = round((cp / tp) * 100, 2) if tp else 0
                    player.date              = date
                    db.session.commit()
                except (ValueError, ZeroDivisionError) as e:
                    flash(f'資料格式錯誤：{e}', 'danger')
            elif action == 'delete':
                db.session.delete(player)
                db.session.commit()
        else:
            try:
                tp   = int(request.form.get('training_progress', '0'))
                cp   = int(request.form.get('complete_progress', '0'))
                date = request.form.get('date')
                if not date:
                    flash('日期為必填項目', 'danger')
                    return redirect(url_for('schedule'))
                p = Player(
                    user_id=g.user.id,
                    name=request.form.get('name'),
                    shot=request.form.get('shot'),
                    training_progress=tp,
                    complete_progress=cp,
                    percentage=round((cp / tp) * 100, 2) if tp else 0,
                    date=date,
                )
                db.session.add(p)
                db.session.commit()
            except (ValueError, ZeroDivisionError) as e:
                flash(f'資料格式錯誤：{e}', 'danger')

        return redirect(url_for('schedule'))
    return render_template('schedule.html', players=players)

@app.route('/view/<int:selected_id>')
@login_required
def view(selected_id):
    player = get_player_or_403(selected_id)
    return render_template('view.html', player=player)

@app.route('/add')
@login_required
def add():
    return render_template('add.html')

@app.route('/edit/<int:selected_id>')
@login_required
def edit(selected_id):
    player = get_player_or_403(selected_id)
    return render_template('edit.html', player=player)

@app.route('/delete/<int:selected_id>')
@login_required
def delete(selected_id):
    player = get_player_or_403(selected_id)
    return render_template('delete.html', player=player)

@app.route('/delete_selected', methods=['POST'])
@login_required
def delete_selected():
    selected_ids = request.json.get('selectedIds', [])
    if not selected_ids:
        return jsonify({'message': '沒有選擇要刪除的項目'}), 400
    deleted = 0
    for sid in selected_ids:
        try:
            player = Player.query.get(int(sid))
            if player and player.user_id == g.user.id:   # [Security] 只刪自己的
                db.session.delete(player)
                deleted += 1
        except (ValueError, TypeError):
            continue
    db.session.commit()
    return jsonify({'message': f'已刪除 {deleted} 筆資料'})

# ─── 路由：影片辨識 ───────────────────────────────────────────────────────────
@app.route('/choose')
@login_required                           # [Security] 原本缺少登入驗證
def choose():
    return render_template('start.html')

@app.route('/video')
@login_required                           # [Security] 原本缺少登入驗證
def video():
    return render_template('train.html')

TRAIN_DISPATCH = {
    '正手長球': Long, '反手長球': LongBackHand,
    '正手小球': Short, '反手小球': Short,
    '正手挑球': ForeHandFlick, '反手挑球': BackHandFlick,
}

@app.route('/train', methods=['POST'])
@login_required
def train():
    file = request.files.get('file')
    if not file or not allowed_file(file.filename):
        flash('請上傳允許格式的影片檔案', 'danger')
        return redirect(url_for('video'))

    filename  = secure_filename(file.filename)
    unique    = f"{uuid.uuid4().hex}_{filename}"            # [Security] UUID 前綴
    save_path = os.path.join(app.config['UPLOAD_FOLDER'], unique)
    file.save(save_path)                                    # [Security] 存到 UPLOAD_FOLDER

    training_option = request.form.get('training_option', '')
    fn = TRAIN_DISPATCH.get(training_option)
    if not fn:
        flash('不支援的訓練項目', 'danger')
        return redirect(url_for('video'))

    result = fn(save_path)                                  # 無頭處理，回傳 dict
    flash(f"辨識完成！動作次數：{result.get('count', 0)} 次", 'success')
    return redirect(url_for('video'))

# ─── 路由：即時辨識（僅限本機，雲端停用）─────────────────────────────────────
@app.route('/realtime')
@login_required
def realtime():
    # 即時辨識需要本機攝影機，在雲端伺服器上無法使用
    # 若需要此功能，請在本機執行 Long.py / ForeShort.py 等腳本
    flash('即時辨識功能需在本機環境使用，請直接執行對應的 .py 腳本', 'info')
    return render_template('realtime.html', cloud_mode=True)

# ─── 錯誤處理 ─────────────────────────────────────────────────────────────────
@app.errorhandler(403)
def forbidden(e):
    return render_template('errors/403.html'), 403

@app.errorhandler(404)
def not_found(e):
    return render_template('errors/404.html'), 404

@app.errorhandler(413)
def too_large(e):
    flash('上傳檔案過大（上限 500 MB）', 'danger')
    return redirect(url_for('video'))

@app.errorhandler(429)
def ratelimit_handler(e):
    flash('操作太頻繁，請稍後再試', 'warning')
    return redirect(url_for('login')), 429

# ─── 啟動 ─────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    # [Security] 正式上線使用 gunicorn，此處僅供本機測試
    debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(host='127.0.0.1', port=5000, debug=debug)
