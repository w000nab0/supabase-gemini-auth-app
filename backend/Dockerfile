# Pythonの公式イメージを使うよ。これでPythonの実行環境が手に入る！
FROM python:3.9-slim-buster

# 作業ディレクトリを /app に設定するよ。
# これから置くファイルは全部ここに入るイメージね。
WORKDIR /app

# requirements.txt を /app にコピーするよ。
# これがないと、必要なライブラリがインストールできないからね。
COPY requirements.txt .

# requirements.txt に書かれたライブラリをインストールするよ。
# --no-cache-dir はキャッシュを使わないオプションで、イメージサイズを小さくするのに役立つよ。
RUN pip install --no-cache-dir -r requirements.txt

# 現在のディレクトリのすべてのファイルを /app にコピーするよ。
# これで、main.py とかもコンテナの中に入るよ。
COPY . .

# アプリケーションがリッスンするポートを公開するよ。
# 今回は8000番ポートを使う予定だよ。
EXPOSE 8000

# コンテナが起動したときに実行するコマンドを設定するよ。
# UvicornっていうASGIサーバーを使って、main.pyのFastAPIアプリを動かすんだ。
# --host 0.0.0.0 は、コンテナ外からのアクセスを許可するための設定だよ。
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]