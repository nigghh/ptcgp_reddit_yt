# PokePoke Overseas Info Aggregator

ゲームアプリ「ポケポケ」に関する海外情報をまとめて、日本のポケポケファン向けにYoutube動画を作成するプロジェクトです。

## プロジェクト概要

1. **Redditから話題の投稿を取得**
   - [r/PTCGP](https://www.reddit.com/r/PTCGP/) から人気のスレッドやコメントを収集。
2. **翻訳**
   - 英語の投稿やコメントを日本語に翻訳（OpenAI APIや他の翻訳APIを利用予定）。
3. **音声合成 (TTS)**
   - 翻訳結果をOpenAIのTTSや他のTTSを使って読み上げ。
   - 会話形式のため、複数の声を用意してキャラクター性を演出。
4. **字幕画像の生成**
   - 音声に合わせて表示させる字幕を画像化。
5. **動画生成 (FFmpeg)**
   - TTSで生成した音声と字幕画像、背景素材を組み合わせて動画を出力。

この流れを自動化・半自動化して運用し、最終的にはYoutubeチャンネルでの収益化を目指します。

## フォルダ構成
my_pokepoke_project/
├── README.md
├── requirements.txt  # 使用するライブラリの記載（pipで管理する場合）
├── main.py       # 全体の実行の流れをコントロールするメインスクリプト
├── fetch_data.py # Redditから情報を取得するスクリプト
├── translate.py  # 翻訳処理を行うスクリプト
├── tts.py        # 音声合成処理を行うスクリプト
├── subtitle.py   # 字幕用画像を生成するスクリプト
└── video_maker.py# ffmpegを使って動画にまとめるスクリプト
├── data/
│   ├── raw/          # 取得した生データを保存
│   ├── processed/    # 翻訳後や字幕生成後など、加工後データを保存
│   └── videos/       # 生成した動画を保存
└── tests/
    └── test_main.py  # テストコード置き場(必要に応じて複数ファイルに分割)


## 必要な環境・インストール方法

- Python 3.12以上を推奨
- condaの仮想環境を利用してのセットアップを推奨します。

```bash
# 仮想環境を作成する例
conda activate youtube_env

# ライブラリのインストール
pip install -r requirements.txt

# 実行
python src/main.py
