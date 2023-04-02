FROM python:3.11.2

# lambda web adapterをインストール
COPY --from=public.ecr.aws/awsguru/aws-lambda-adapter:0.5.0 /lambda-adapter /opt/extensions/lambda-adapter

# 環境変数を定義
ENV TZ Asia/Tokyo
ENV LANG ja_JP.UTF-8
ENV LANGUAGE ja_JP:ja
ENV LC_ALL ja_JP.UTF-8

# flaskアプリを丸ごとコピーし、pythonライブラリをインストール
WORKDIR /ai_creator_for_3dcg_back_end
COPY . .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

ENV PORT=5050
EXPOSE 5050

CMD ["python", "main.py"]