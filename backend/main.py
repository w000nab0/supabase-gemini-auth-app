# FastAPIのメインクラスをインポートするよ
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from typing import Union
import os # 環境変数を読み込むために必要
from supabase import create_client, Client # Supabaseクライアントをインポート
from pydantic import BaseModel
import google.generativeai as genai
from fastapi.responses import Response


SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
SUPABASE_JWT_SECRET: str = os.environ.get("SUPABASE_JWT_SECRET")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if not SUPABASE_URL or not SUPABASE_KEY or not SUPABASE_SERVICE_ROLE_KEY or not SUPABASE_JWT_SECRET:
    print("WARNING: One or more Supabase environment variables are missing!")



# Supabaseクライアントを初期化するよ
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None
supabase_admin: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY) if SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY else None


if not GEMINI_API_KEY:
    print("WARNING: Gemini API Key is missing!")

# Gemini APIクライアントを設定するよ
genai.configure(api_key=GEMINI_API_KEY)
gemini_model = None


# FastAPIのアプリケーションインスタンスを作成するよ
# これがWebアプリの本体になるイメージね！
app = FastAPI()

print("DEBUG: Before adding CORS middleware") # ★★★ 追加 ★★★

# CORS設定を追加するよ
# 許可するオリジン（フロントエンドのURL）を指定するよ
origins = [
    "http://localhost:3000", # 君のフロントエンドが動いているURLだよ！
    "https://supabase-gemini-auth-app.vercel.app", # ★ VercelにデプロイしたあなたのフロントエンドURL
    "https://supabase-gemini-auth-app.onrender.com" # ★ 自身のAPIも許可 (一部のリダイレクトなどで必要になる場合がある)
    # "http://localhost", # もし必要なら追加
    # "http://localhost:8080", # 他のポートもあれば追加
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins, # 許可するオリジンを指定
    allow_credentials=True, # クッキーや認証情報（Authorizationヘッダーなど）を許可
    allow_methods=["GET", "POST", "OPTIONS"], # ★必要なメソッドのみに絞る
    allow_headers=["Content-Type", "Authorization"], # ★必要なヘッダーのみに絞る
    # allow_methods=["*"], # ワイルドカードを一時的に解除
    # allow_headers=["*"], # ワイルドカードを一時的に解除
)

print("DEBUG: After adding CORS middleware") # ★★★ 追加 ★★★


    
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login") 


# ★★★ 明示的にHEADメソッドをハンドリングするエンドポイントを追加 ★★★
# これは通常不要だが、Renderのヘルスチェック問題に対応するため
@app.head("/")
async def head_root():
    # HEADリクエストはボディを返さないので、ステータスコード200でOK
    return Response(status_code=status.HTTP_200_OK)

# ルートURL（"/"）にGETリクエストが来たときに実行される関数を定義するよ
@app.get("/")
async def read_root():
    # 辞書形式でデータを返すと、FastAPIが自動でJSONに変換してくれるんだ
    return {"message": "Hello, Supabase Auth App!"}

# テスト用に別のエンドポイントも作ってみよう！
@app.get("/items/{item_id}")
async def read_item(item_id: int, q: Union[str, None] = None):
    # item_idはパスパラメータ、qはクエリパラメータだよ
    return {"item_id": item_id, "q": q}


class UserCreate(BaseModel):
    email: str
    password: str
    name: str  # 追加
    age: int   # 追加

class UserLogin(BaseModel):
    email: str
    password: str

# ユーザー登録のエンドポイント
@app.post("/auth/signup")
async def signup_user(user: UserCreate):
    try:
        # Supabaseのauth.sign_upメソッドを使ってユーザーを登録するよ
        # passwordは必須。emailはemailに、passwordはpasswordに渡すよ
        # data={"email_confirm": True} は、認証メールの確認をスキップする設定。
        # 本番環境ではメール認証を有効にするのが一般的だけど、今回は開発をスムーズにするためにスキップするよ。
        response = supabase.auth.sign_up({
            "email": user.email,
            "password": user.password
        })

        if response.user: # ユーザーがちゃんと作成されたか確認
            user_id = response.user.id # 認証後のユーザーIDを取得するよ
        
             # ↓↓ ここから追加 ↓↓
            # profilesテーブルにユーザーのメタデータを保存
            data, count = supabase_admin.table("profiles").insert({
                "user_id": user_id,
                "name": user.name,
                "age": user.age
            }).execute()

            if data:
                return {"message": "User registered successfully and profile created", "user_id": user_id}
            else:
                # プロフィール作成に失敗した場合は、ユーザー認証もロールバックするか考慮が必要
                # 今はシンプルにエラーを返す
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create user profile.")
            # ↑↑ ここまで修正 ↑↑

        else:
            # エラーレスポンスがあればそれを返す
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=response.json())

    except Exception as e:
        # Supabaseからのエラーやその他の例外をキャッチしてHTTPExceptionとして返すよ
        # エラーメッセージはユーザーに分かりやすくするよう調整できるといいね
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

# ユーザーログインのエンドポイント
@app.post("/auth/login")
async def login_user(user: UserLogin):
    try:
        # Supabaseのauth.sign_in_with_passwordメソッドを使ってログインするよ
        response = supabase.auth.sign_in_with_password({
            "email": user.email,
            "password": user.password
        })

        if response.user and response.session: # ユーザーとセッションがちゃんと返されたか確認
            return {"message": "User logged in successfully", "access_token": response.session.access_token}
        else:
            # エラーレスポンスがあればそれを返す
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=response.json())

    except Exception as e:
        import traceback # 追加
        traceback.print_exc() # 追加
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


# JWT認証のための依存性注入 (Dependency Injection)
async def get_current_user_id(token: str = Depends(oauth2_scheme)):
    """
    AuthorizationヘッダーからJWTを抽出し、Supabaseで検証してuser_idを返す
    """
    # Authorizationヘッダーがなければ、OAuth2PasswordBearerが自動的に401を返すので、
    # ここで is not None のチェックは不要になる (tokenは必ず文字列かNoneになる)
    
    try:
        # Supabaseクライアントを使ってJWTを検証する
        user_response = supabase.auth.get_user(token) # このtokenはOAuth2PasswordBearerが抽出したもの
        
        if user_response and user_response.user:
            return user_response.user.id
        else:
            # トークンが無効またはユーザーが見つからない場合
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error validating token: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    

# Geminiに送るメッセージのデータモデルを定義するよ
class GeminiPrompt(BaseModel):
    prompt: str

# Gemini APIクライアントを設定するよ
genai.configure(api_key=GEMINI_API_KEY)
# モデルが存在するか確認してから初期化するよ
try:
    gemini_model = genai.GenerativeModel('gemini-2.0-flash-lite')
except Exception as e:
    print(f"Error initializing Gemini model: {e}")
    #gemini_model = None # 初期化に失敗したらNoneにする


# Geminiにテキストを生成させるエンドポイントを追加するよ
@app.post("/generate_text")
async def generate_text(prompt_data: GeminiPrompt, current_user_id: str = Depends(get_current_user_id)):
    if not gemini_model:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Gemini model not initialized.")
    try:
        # Geminiモデルにプロンプトを送信して応答を生成するよ
        response = gemini_model.generate_content(prompt_data.prompt)
        
        # 応答からテキストを抽出するよ
        # response.text が存在しない場合や空の場合に備えてNoneチェックを入れる
        generated_text = response.text if hasattr(response, 'text') else ""

        # ユーザーIDと生成されたテキストをログに出力（デバッグ用）
        print(f"User {current_user_id} generated text: {generated_text[:50]}...") # 最初の50文字だけ表示

        return {"generated_text": generated_text}
    except Exception as e:
        # Gemini APIからのエラーをキャッチして返すよ
        print(f"Error calling Gemini API: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to generate text from Gemini: {e}")
