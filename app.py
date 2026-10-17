<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hệ Thống Quản Lý - Bản Đồ</title>
    <!-- Leaflet CSS -->
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <!-- Font Awesome -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.7.2/css/all.min.css" />
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Segoe UI', Roboto, sans-serif;
        }
        body {
            background: #eef2f7;
            min-height: 100vh;
            display: flex;
            overflow: hidden;
        }

        /* ===== THANH BÊN TRÁI - ĐÃ LÀM ĐẦY ĐỦ ===== */
        .sidebar {
            width: 260px;
            background: linear-gradient(180deg, #1e3a8a, #1e40af);
            color: white;
            display: flex;
            flex-direction: column;
            box-shadow: 2px 0 10px rgba(0,0,0,0.1);
            z-index: 100;
        }
        .sidebar-header {
            padding: 20px;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }
        .sidebar-title {
            font-size: 18px;
            font-weight: 700;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .sidebar-nav {
            flex: 1;
            padding: 15px 10px;
        }
        .nav-item {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 12px 15px;
            margin-bottom: 5px;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.25s ease;
            text-decoration: none;
            color: #e0e7ff;
        }
        .nav-item:hover, .nav-item.active {
            background: rgba(255,255,255,0.15);
            color: white;
        }
        .nav-item i {
            width: 20px;
            text-align: center;
            font-size: 18px;
        }
        .sidebar-footer {
            padding: 15px;
            border-top: 1px solid rgba(255,255,255,0.1);
        }

        /* ===== KHU VỰC CHÍNH - BÊN PHẢI ===== */
        .main-wrapper {
            flex: 1;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }

        /* Thanh trên cùng */
        .top-navbar {
            background: white;
            padding: 12px 25px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        }
        .top-left-title {
            font-size: 18px;
            font-weight: 600;
            color: #1f2937;
        }
        .top-right-group {
            display: flex;
            align-items: center;
            gap: 20px;
        }
        .realtime-clock {
            font-size: 14px;
            background: #eff6ff;
            color: #1e40af;
            padding: 6px 14px;
            border-radius: 20px;
            font-weight: 500;
        }

        /* Thông báo & Avatar */
        .icon-btn {
            position: relative;
            cursor: pointer;
            font-size: 20px;
            color: #4b5563;
            transition: color 0.2s;
        }
        .icon-btn:hover { color: #1e40af; }
        .badge {
            position: absolute;
            top: -6px;
            right: -6px;
            background: #ef4444;
            color: white;
            font-size: 10px;
            min-width: 16px;
            height: 16px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
        }
        .avatar-box {
            display: flex;
            align-items: center;
            gap: 8px;
            cursor: pointer;
        }
        .avatar {
            width: 38px;
            height: 38px;
            border-radius: 50%;
            background: linear-gradient(135deg, #3b82f6, #1d4ed8);
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
            font-size: 16px;
        }
        .avatar-text {
            font-size: 14px;
            font-weight: 500;
            color: #374151;
        }

        /* Dropdown menu */
        .dropdown {
            position: absolute;
            top: 55px;
            right: 0;
            background: white;
            min-width: 220px;
            border-radius: 10px;
            box-shadow: 0 5px 20px rgba(0,0,0,0.15);
            padding: 8px 0;
            display: none;
            z-index: 999;
        }
        .dropdown.show { display: block; }
        .dropdown-item {
            padding: 12px 20px;
            display: flex;
            align-items: center;
            gap: 10px;
            color: #374151;
            cursor: pointer;
            transition: background 0.2s;
        }
        .dropdown-item:hover { background: #f3f4f6; }
        .dropdown-item.danger { color: #dc2626; }
        .dropdown-wrapper { position: relative; }

        /* Bản đồ */
        .map-container {
            flex: 1;
            position: relative;
        }
        #map {
            width: 100%;
            height: 100%;
        }

        /* ===== CHATBOT ===== */
        .chat-toggle {
            position: fixed;
            bottom: 25px;
            right: 25px;
            width: 60px;
            height: 60px;
            border-radius: 50%;
            background: linear-gradient(135deg, #10b981, #059669);
            color: white;
            border: none;
            font-size: 24px;
            cursor: pointer;
            box-shadow: 0 4px 15px rgba(16,185,129,0.35);
            z-index: 900;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .chat-toggle:hover { transform: scale(1.05); }
        .chat-window {
            position: fixed;
            bottom: 100px;
            right: 25px;
            width: 380px;
            max-height: 520px;
            background: white;
            border-radius: 16px;
            box-shadow: 0 8px 30px rgba(0,0,0,0.18);
            display: none;
            flex-direction: column;
            overflow: hidden;
            z-index: 901;
        }
        .chat-window.open { display: flex; }
        .chat-head {
            background: linear-gradient(135deg, #10b981, #059669);
            color: white;
            padding: 14px 18px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-weight: 600;
        }
        .chat-close {
            background: none;
            border: none;
            color: white;
            font-size: 22px;
            cursor: pointer;
            line-height: 1;
        }
        .chat-body {
            flex: 1;
            padding: 15px;
            overflow-y: auto;
            background: #fafafa;
        }
        .msg {
            margin-bottom: 12px;
            max-width: 82%;
            line-height: 1.4;
        }
        .user-msg {
            margin-left: auto;
            background: #dbeafe;
            padding: 10px 14px;
            border-radius: 18px 18px 4px 18px;
        }
        .bot-msg {
            margin-right: auto;
            background: #e5e7eb;
            padding: 10px 14px;
            border-radius: 18px 18px 18px 4px;
        }
        .suggest-row {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin: 10px 0;
        }
        .suggest-btn {
            background: #eff6ff;
            border: 1px solid #bfdbfe;
            border-radius: 20px;
            padding: 7px 14px;
            font-size: 13px;
            cursor: pointer;
            transition: all 0.2s;
        }
        .suggest-btn:hover {
            background: #dbeafe;
            border-color: #93c5fd;
        }
        .chat-input-area {
            display: flex;
            padding: 12px;
            border-top: 1px solid #eee;
            gap: 8px;
        }
        .chat-input {
            flex: 1;
            padding: 10px 16px;
            border: 1px solid #ddd;
            border-radius: 24px;
            outline: none;
            font-size: 14px;
        }
        .chat-input:focus { border-color: #10b981; }
        .chat-send-btn {
            padding: 10px 20px;
            background: #10b981;
            color: white;
            border: none;
            border-radius: 20px;
            cursor: pointer;
            font-weight: 500;
        }
        .chat-send-btn:hover { background: #059669; }

        /* ===== MODAL ĐĂNG NHẬP - ĐÃ SỬA LỖI ===== */
        .modal-overlay {
            position: fixed;
            inset: 0;
            background: rgba(0,0,0,0.55);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 2000;
            opacity: 0;
            visibility: hidden;
            transition: all 0.3s ease;
        }
        .modal-overlay.show {
            opacity: 1;
            visibility: visible;
        }
        .login-card {
            background: white;
            width: 90%;
            max-width: 420px;
            border-radius: 16px;
            padding: 35px 30px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            transform: translateY(20px);
            transition: transform 0.3s ease;
        }
        .modal-overlay.show .login-card {
            transform: translateY(0);
        }
        .login-card h2 {
            text-align: center;
            margin-bottom: 25px;
            color: #1f2937;
            font-size: 24px;
        }
        .form-group {
            margin-bottom: 20px;
        }
        .form-label {
            display: block;
            margin-bottom: 8px;
            font-weight: 500;
            color: #374151;
        }
        .input-container {
            position: relative;
        }
        .form-field {
            width: 100%;
            padding: 13px 45px 13px 15px;
            border: 1px solid #d1d5db;
            border-radius: 8px;
            font-size: 15px;
            transition: border-color 0.2s, box-shadow 0.2s;
        }
        .form-field:focus {
            outline: none;
            border-color: #3b82f6;
            box-shadow: 0 0 0 3px rgba(59,130,246,0.15);
        }
        .form-field.error-border {
            border-color: #ef4444;
            background: #fef2f2;
        }
        .eye-btn {
            position: absolute;
            right: 12px;
            top: 50%;
            transform: translateY(-50%);
            background: none;
            border: none;
            font-size: 18px;
            color: #6b7280;
            cursor: pointer;
        }
        .eye-btn:hover { color: #374151; }
        .error-msg {
            color: #ef4444;
            font-size: 13px;
            margin-top: 6px;
            display: none;
        }
        .login-submit-btn {
            width: 100%;
            padding: 13px;
            background: linear-gradient(135deg, #1e40af, #3b82f6);
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            margin-top: 5px;
            transition: opacity 0.2s;
        }
        .login-submit-btn:hover { opacity: 0.93; }

        /* Trạng thái hiển thị theo đăng nhập */
        .logged-in .show-guest { display: none !important; }
        :not(.logged-in) .show-user { display: none !important; }
        .guest-login-btn {
            background: none;
            border: none;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 8px;
            color: #4b5563;
            font-size: 14px;
        }
        .guest-login-btn:hover { color: #1e40af; }
    </style>
</head>
<body id="appBody">

    <!-- ===== THANH BÊN TRÁI ===== -->
    <aside class="sidebar">
        <div class="sidebar-header">
            <div class="sidebar-title">
                <i class="fa-solid fa-map-location-dot"></i>
                <span>Bản Đồ Hệ Thống</span>
            </div>
        </div>
        <nav class="sidebar-nav">
            <a class="nav-item active">
                <i class="fa-solid fa-globe"></i>
                <span>Bản đồ chính</span>
            </a>
            <a class="nav-item">
                <i class="fa-solid fa-location-pin"></i>
                <span>Vị trí theo dõi</span>
            </a>
            <a class="nav-item">
                <i class="fa-solid fa-chart-simple"></i>
                <span>Thống kê</span>
            </a>
            <a class="nav-item">
                <i class="fa-solid fa-file-lines"></i>
                <span>Báo cáo</span>
            </a>
            <a class="nav-item">
                <i class="fa-solid fa-gear"></i>
                <span>Cài đặt hệ thống</span>
            </a>
            <a class="nav-item">
                <i class="fa-solid fa-circle-question"></i>
                <span>Trợ giúp</span>
            </a>
        </nav>
        <div class="sidebar-footer">
            <div class="nav-item" style="opacity: 0.8;">
                <i class="fa-solid fa-copyright"></i>
                <span>Phiên bản 2.0</span>
            </div>
        </div>
    </aside>

    <!-- ===== KHU VỰC CHÍNH ===== -->
    <main class="main-wrapper">
        <!-- Thanh trên cùng -->
        <header class="top-navbar">
            <div class="top-left-title">Trung tâm giám sát</div>
            <div class="top-right-group">
                <div class="realtime-clock" id="clock">--:--:--</div>

                <!-- Thông báo -->
                <div class="dropdown-wrapper">
                    <div class="icon-btn" id="notifBtn">
                        <i class="fa-solid fa-bell"></i>
                        <span class="badge">3</span>
                    </div>
                    <div class="dropdown" id="notifDropdown">
                        <div class="dropdown-item"><i class="fa-solid fa-circle-check" style="color:#10b981"></i> Hệ thống cập nhật xong</div>
                        <div class="dropdown-item"><i class="fa-solid fa-map-pin" style="color:#ef4444"></i> Vị trí mới được ghi nhận</div>
                        <div class="dropdown-item"><i class="fa-solid fa-rotate" style="color:#3b82f6"></i> Dữ liệu đã đồng bộ</div>
                    </div>
                </div>

                <!-- Khách → Nút đăng nhập -->
                <div class="dropdown-wrapper show-guest" id="loginTriggerWrap">
                    <button class="guest-login-btn" id="openLoginBtn">
                        <div class="avatar" style="background: #94a3b8; width:34px; height:34px; font-size:14px;">
                            <i class="fa-solid fa-user"></i>
                        </div>
                        <span class="avatar-text">Đăng nhập</span>
                    </button>
                </div>

                <!-- Đã đăng nhập → Avatar + menu -->
                <div class="dropdown-wrapper show-user">
                    <div class="avatar-box" id="userAvatarBtn">
                        <div class="avatar">ND</div>
                        <span class="avatar-text">Người Dùng</span>
                        <i class="fa-solid fa-chevron-down" style="font-size:11px; color:#9ca3af;"></i>
                    </div>
                    <div class="dropdown" id="userDropdown">
                        <div class="dropdown-item"><i class="fa-solid fa-user"></i> Thông tin tài khoản</div>
                        <div class="dropdown-item"><i class="fa-solid fa-gear"></i> Cài đặt</div>
                        <div class="dropdown-item"><i class="fa-solid fa-shield-halved"></i> Bảo mật</div>
                        <div class="dropdown-item danger" id="logoutBtn">
                            <i class="fa-solid fa-right-from-bracket"></i> Đăng xuất
                        </div>
                    </div>
                </div>
            </div>
        </header>

        <!-- Bản đồ -->
        <div class="map-container">
            <div id="map"></div>
        </div>
    </main>

    <!-- ===== CHATBOT ===== -->
    <button class="chat-toggle" id="openChatBtn">
        <i class="fa-solid fa-robot"></i>
    </button>
    <div class="chat-window" id="chatWindow">
        <div class="chat-head">
            <span>Trợ Lý AI</span>
            <button class="chat-close" id="closeChatBtn">&times;</button>
        </div>
        <div class="chat-body" id="chatBody">
            <div class="msg bot-msg">
                Xin chào! Tôi là trợ lý AI của hệ thống. Bạn cần hỗ trợ gì? 😊
                <div class="suggest-row">
                    <button class="suggest-btn" data-text="Bản đồ hiển thị những gì?">Bản đồ hiển thị gì?</button>
                    <button class="suggest-btn" data-text="Làm sao để xem chi tiết vị trí?">Xem chi tiết vị trí?</button>
                    <button class="suggest-btn" data-text="Hệ thống có chức năng gì?">Chức năng hệ thống?</button>
                    <button class="suggest-btn" data-text="Cách đăng xuất như thế nào?">Cách đăng xuất?</button>
                </div>
            </div>
        </div>
        <div class="chat-input-area">
            <input type="text" class="chat-input" id="chatInputField" placeholder="Nhập câu hỏi...">
            <button class="chat-send-btn" id="sendChatBtn">Gửi</button>
        </div>
    </div>

    <!-- ===== MODAL ĐĂNG NHẬP ===== -->
    <div class="modal-overlay" id="loginModalOverlay">
        <div class="login-card">
            <h2>🔐 Đăng Nhập</h2>
            <form id="loginFormMain">
                <div class="form-group">
                    <label class="form-label">Tên đăng nhập</label>
                    <div class="input-container">
                        <input type="text" class="form-field" id="usernameField" placeholder="Nhập tên đăng nhập">
                    </div>
                    <div class="error-msg" id="userError">Vui lòng nhập tên đăng nhập</div>
                </div>
                <div class="form-group">
                    <label class="form-label">Mật khẩu</label>
                    <div class="input-container">
                        <input type="password" class="form-field" id="passwordField" placeholder="Nhập mật khẩu">
                        <button type="button" class="eye-btn" id="togglePasswordBtn">
                            <i class="fa-solid fa-eye"></i>
                        </button>
                    </div>
                    <div class="error-msg" id="passError">Vui lòng nhập mật khẩu</div>
                </div>
                <button type="submit" class="login-submit-btn">Đăng Nhập</button>
            </form>
        </div>
    </div>

    <!-- Thư viện -->
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script>
        // ========== 1. BẢN ĐỒ - KHỞI TẠO ĐÚNG CÁCH ==========
        const map = L.map('map').setView([21.0285, 105.8542], 13);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; OpenStreetMap contributors'
        }).addTo(map);
        L.marker([21.0285, 105.8542]).addTo(map)
            .bindPopup('📍 Hà Nội, Việt Nam')
            .openPopup();

        // ========== 2. ĐỒNG HỒ THỜI GIAN THỰC ==========
        function refreshClock() {
            const now = new Date();
            document.getElementById('clock').textContent = now.toLocaleTimeString('vi-VN');
        }
        refreshClock();
        setInterval(refreshClock, 1000);

        // ========== 3. DROPDOWN THÔNG BÁO & TÀI KHOẢN ==========
        const notifBtn = document.getElementById('notifBtn');
        const notifDropdown = document.getElementById('notifDropdown');
        const userAvatarBtn = document.getElementById('userAvatarBtn');
        const userDropdown = document.getElementById('userDropdown');

        function closeAllDropdowns() {
            notifDropdown.classList.remove('show');
            userDropdown.classList.remove('show');
        }

        notifBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            notifDropdown.classList.toggle('show');
            userDropdown.classList.remove('show');
        });

        userAvatarBtn?.addEventListener('click', (e) => {
            e.stopPropagation();
            userDropdown.classList.toggle('show');
            notifDropdown.classList.remove('show');
        });

        document.addEventListener('click', closeAllDropdowns);
        [notifDropdown, userDropdown].forEach(d => {
            d.addEventListener('click', e => e.stopPropagation());
        });

        // ========== 4. CHATBOT ==========
        const openChatBtn = document.getElementById('openChatBtn');
        const closeChatBtn = document.getElementById('closeChatBtn');
        const chatWindow = document.getElementById('chatWindow');
        const chatBody = document.getElementById('chatBody');
        const chatInputField = document.getElementById('chatInputField');
        const sendChatBtn = document.getElementById('sendChatBtn');

        const answersDB = {
            'Bản đồ hiển thị những gì?': '🗺️ Bản đồ hiển thị khu vực trung tâm Hà Nội, bạn có thể phóng to/thu nhỏ, di chuyển xem mọi vị trí. Dữ liệu lấy từ OpenStreetMap.',
            'Làm sao để xem chi tiết vị trí?': '👆 Hãy nhấp chuột vào biểu tượng đánh dấu trên bản đồ, khung thông tin chi tiết sẽ hiển thị ngay.',
            'Hệ thống có chức năng gì?': '✅ Quản lý bản đồ, theo dõi vị trí, xem thông báo, tra cứu báo cáo, trò chuyện với trợ lý AI, quản lý tài khoản & đăng xuất.',
            'Cách đăng xuất như thế nào?': '👉 Nhấp vào tên/avatar ở góc trên bên phải → chọn "Đăng xuất" trong danh sách hiện ra.'
        };

        function addMessage(text, isUser) {
            const div = document.createElement('div');
            div.className = `msg ${isUser ? 'user-msg' : 'bot-msg'}`;
            div.textContent = text;
            chatBody.appendChild(div);
            chatBody.scrollTop = chatBody.scrollHeight;
        }

        function processMessage(text) {
            if (!text.trim()) return;
            addMessage(text, true);
            setTimeout(() => {
                let reply = '🤔 Tôi chưa rõ câu hỏi này. Bạn vui lòng chọn gợi ý hoặc đặt câu hỏi rõ hơn nhé!';
                for (let q in answersDB) {
                    if (text.trim() === q || text.includes(q.slice(0, 8))) {
                        reply = answersDB[q];
                        break;
                    }
                }
                addMessage(reply, false);
            }, 600);
            chatInputField.value = '';
        }

        openChatBtn.addEventListener('click', () => chatWindow.classList.add('open'));
        closeChatBtn.addEventListener('click', () => chatWindow.classList.remove('open'));
        sendChatBtn.addEventListener('click', () => processMessage(chatInputField.value));
        chatInputField.addEventListener('keydown', e => e.key === 'Enter' && processMessage(chatInputField.value));

        // Nút gợi ý
        document.addEventListener('click', e => {
            if (e.target.classList.contains('suggest-btn')) {
                processMessage(e.target.dataset.text);
            }
        });

        // ========== 5. ĐĂNG NHẬP - VALIDATION + HIỆN/ẨN MẬT KHẨU ==========
        const loginModalOverlay = document.getElementById('loginModalOverlay');
        const openLoginBtn = document.getElementById('openLoginBtn');
        const loginFormMain = document.getElementById('loginFormMain');
        const usernameField = document.getElementById('usernameField');
        const passwordField = document.getElementById('passwordField');
        const togglePasswordBtn = document.getElementById('togglePasswordBtn');
        const userError = document.getElementById('userError');
        const passError = document.getElementById('passError');
        const logoutBtn = document.getElementById('logoutBtn');
        const appBody = document.getElementById('appBody');

        // Mở form đăng nhập
        openLoginBtn.addEventListener('click', () => {
            loginModalOverlay.classList.add('show');
            usernameField.value = '';
            passwordField.value = '';
            userError.style.display = 'none';
            passError.style.display = 'none';
            usernameField.classList.remove('error-border');
            passwordField.classList.remove('error-border');
        });

        // Đóng khi nhấp ra ngoài
        loginModalOverlay.addEventListener('click', e => {
            if (e.target === loginModalOverlay) {
                loginModalOverlay.classList.remove('show');
            }
        });

        // Hiện/ẩn mật khẩu
        togglePasswordBtn.addEventListener('click', () => {
            const isText = passwordField.type === 'text';
            passwordField.type = isText ? 'password' : 'text';
            togglePasswordBtn.innerHTML = isText
                ? '<i class="fa-solid fa-eye"></i>'
                : '<i class="fa-solid fa-eye-slash"></i>';
        });

        // Xử lý submit form
        loginFormMain.addEventListener('submit', e => {
            e.preventDefault();
            let ok = true;
            userError.style.display = 'none';
            passError.style.display = 'none';
            usernameField.classList.remove('error-border');
            passwordField.classList.remove('error-border');

            if (!usernameField.value.trim()) {
                userError.style.display = 'block';
                usernameField.classList.add('error-border');
                ok = false;
            }
            if (!passwordField.value) {
                passError.style.display = 'block';
                passwordField.classList.add('error-border');
                ok = false;
            }

            if (ok) {
                appBody.classList.add('logged-in');
                loginModalOverlay.classList.remove('show');
            }
        });

        // ========== 6. ĐĂNG XUẤT ==========
        logoutBtn.addEventListener('click', () => {
            appBody.classList.remove('logged-in');
            closeAllDropdowns();
        });
    </script>
</body>
</html>
