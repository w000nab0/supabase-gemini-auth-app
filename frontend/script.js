// HTML要素への参照を取得するよ
const authSection = document.getElementById('auth-section');
const chatSection = document.getElementById('chat-section');
const signupForm = document.getElementById('signup-form');
const signupNameInput = document.getElementById('signup-name');
const signupAgeInput = document.getElementById('signup-age');
const loginForm = document.getElementById('login-form');
const logoutButton = document.getElementById('logout-button');
const authMessage = document.getElementById('auth-message');
const chatOutput = document.getElementById('chat-output');
const chatForm = document.getElementById('chat-form');
const chatMessage = document.getElementById('chat-message');
const chatInput = document.getElementById('chat-input');

// APIのベースURLを設定するよ
// バックエンドがDockerコンテナ内で動いているから、localhost:8000 を使うよ
const API_BASE_URL = 'http://localhost:8000';

// ユーザーのセッション（アクセストークンなど）を保存する変数
let accessToken = localStorage.getItem('supabase_access_token'); // ★★★ 修正箇所1 ★★★
let userId = null; // 必要であれば後でアクセストークンからデコードして取得することも可能

// =========================================================================
// ユーティリティ関数
// =========================================================================

// メッセージを表示する関数
function showMessage(element, message, isError = false) {
    element.textContent = message;
    element.className = isError ? 'message error' : 'message success';
    setTimeout(() => {
        element.textContent = '';
        element.className = 'message';
    }, 5000); // 5秒後にメッセージを消すよ
}

// 認証済みかどうかに応じて表示を切り替える関数
function updateUI() {
    if (accessToken) {
        // ログイン済みの場合
        authSection.style.display = 'none'; // 認証フォームを隠す
        chatSection.style.display = 'block'; // チャットセクションを表示する
        logoutButton.style.display = 'block'; // ログアウトボタンを表示する
    } else {
        // 未ログインの場合
        authSection.style.display = 'block'; // 認証フォームを表示する
        chatSection.style.display = 'none'; // チャットセクションを隠す
        logoutButton.style.display = 'none'; // ログアウトボタンを隠す
    }
}

// チャットメッセージを画面に追加する関数
function addChatMessage(sender, text) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message ${sender}`; // senderは'user'か'ai'
    messageDiv.textContent = text;
    chatOutput.appendChild(messageDiv);
    // スクロールを一番下まで持っていくよ
    chatOutput.scrollTop = chatOutput.scrollHeight;
}

// =========================================================================
// イベントリスナー（フォーム送信時の処理）
// =========================================================================

// 新規登録フォームの送信処理
signupForm.addEventListener('submit', async (e) => {
    e.preventDefault(); // ページの再読み込みを防ぐよ

    const email = document.getElementById('signup-email').value;
    const password = document.getElementById('signup-password').value;
    const name = signupNameInput.value; // 新しく追加した入力欄の値を取得
    const age = parseInt(signupAgeInput.value, 10); // 数値に変換

    try {
        const response = await fetch(`${API_BASE_URL}/auth/signup`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ email, password, name, age }),
        });

        const data = await response.json();

        if (response.ok) { // HTTPステータスコードが200番台なら成功
            showMessage(authMessage, data.message + ' ログインしてください。', false);
            // 登録成功後、自動でログインフォームのフィールドに情報を入力する（任意）
            document.getElementById('login-email').value = email;
            document.getElementById('login-password').value = password;
        } else { // エラーレスポンスの場合
            showMessage(authMessage, data.detail || '登録に失敗しました。', true);
        }
    } catch (error) {
        showMessage(authMessage, 'ネットワークエラー: ' + error.message, true);
    }
});

// ログインフォームの送信処理
loginForm.addEventListener('submit', async (e) => {
    e.preventDefault(); // ページの再読み込みを防ぐよ

    const email = document.getElementById('login-email').value;
    const password = document.getElementById('login-password').value;

    try {
        const response = await fetch(`${API_BASE_URL}/auth/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ email, password }),
        });

        const data = await response.json();

        if (response.ok) { // HTTPステータスコードが200番台なら成功
            accessToken = data.access_token; // アクセストークンを保存する
            console.log('ログイン成功！取得したトークン:', accessToken);
            localStorage.setItem('supabase_access_token', data.access_token);
            console.log('localStorageにトークンを保存しました。');
            const storedToken = localStorage.getItem('supabase_access_token');
            console.log('localStorageから読み込んだトークン:', storedToken);
            if (!storedToken) {
                console.error('ERROR: localStorageにトークンが保存されていないようです！');
            }
        
            // ユーザーIDはaccess_tokenからデコードして取得することもできるけど、
            // 今回はシンプルにSupabaseのログインレスポンスから取得できるならそこから取得する
            // (今回はレスポンスに直接user_idがないので、省略。必要なら後で追加できるよ)
            showMessage(authMessage, data.message, false);
            updateUI(); // UIを更新してチャット画面を表示する
            addChatMessage('ai', 'AIチャットへようこそ！何か質問はありますか？'); // ログイン後の初回メッセージ
        } else { // エラーレスポンスの場合
            showMessage(authMessage, data.detail || 'ログインに失敗しました。', true);
        }
    } catch (error) {
        showMessage(authMessage, 'ネットワークエラー: ' + error.message, true);
    }
});

// ログアウトボタンのクリック処理
logoutButton.addEventListener('click', () => {
    accessToken = null; // アクセストークンをクリアする
    localStorage.removeItem('supabase_access_token');
    userId = null; // ユーザーIDもクリアする
    showMessage(authMessage, 'ログアウトしました。', false);
    // チャット履歴をクリアする（任意）
    chatOutput.innerHTML = '';
    updateUI(); // UIを更新して認証画面に戻る
});

// チャットフォームの送信処理 (Gemini APIの呼び出し)
chatForm.addEventListener('submit', async (e) => {
    e.preventDefault(); // ページの再読み込みを防ぐよ

    const prompt = document.getElementById('chat-input').value;
    if (!prompt) return; // 入力がない場合は何もしない

    addChatMessage('user', prompt); // ユーザーのメッセージをチャット画面に追加
    document.getElementById('chat-input').value = ''; // 入力フィールドをクリア

    try {
        console.log('メッセージ送信時のaccessToken:', accessToken);
        // アクセストークンがない場合はエラー
        if (!accessToken) { // ★★★ 修正箇所4 (認証チェックの強化) ★★★
            showMessage(chatMessage, '認証されていません。ログインしてください。', true);
            updateUI(); // 認証画面に戻す
            return;
        }
        const response = await fetch(`${API_BASE_URL}/generate_text`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${accessToken}`
                // 認証が必要なAPIなら、ここにAuthorizationヘッダーを追加するよ
                // 'Authorization': `Bearer ${accessToken}`
            },
            body: JSON.stringify({ prompt }),
        });

        const data = await response.json();

        if (response.ok) {
            addChatMessage('ai', data.generated_text); // Geminiの応答をチャット画面に追加
            showMessage(chatMessage, 'テキストを生成しました。', false);
        } else {
            showMessage(chatMessage, data.detail || 'AIの応答取得に失敗しました。', true);
            // 401 Unauthorized の場合はログアウト処理
            if (response.status === 401) { // ★★★ 修正箇所6: 認証エラー時の自動ログアウト ★★★
                showMessage(chatMessage, 'セッションの期限が切れました。再ログインしてください。', true);
                logoutButton.click(); // ログアウト処理を実行
            }
        }
    } catch (error) {
        showMessage(chatMessage, 'ネットワークエラー: ' + error.message, true);
    }
});

// ページ読み込み時にUIを初期化する
updateUI();