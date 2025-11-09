# src/video_maker.py

import os
import subprocess

def create_video(audio_files, image_files, output_path="data/videos/final_output.mp4"):
    """
    FFmpegを使って音声と画像を連結し、動画を生成する簡易サンプル。
    実際には、それぞれの音声ファイルの長さに合わせて画像を切り替えるなどの
    工夫が必要になる。

    ここでは例として単純に1枚目の画像を全体に表示、全オーディオを連結する。
    """

    # まず、全てのオーディオを連結する（concat demuxerを使う場合の例）
    concat_list_file = "temp_concat.txt"
    with open(concat_list_file, "w", encoding="utf-8") as f:
        for af in audio_files:
            f.write(f"file '{os.path.abspath(af)}'\n")

    # 連結された音声ファイルを作成
    temp_audio = "temp_audio.mp3"
    cmd_concat_audio = [
        "ffmpeg",
        "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", concat_list_file,
        "-c", "copy",
        temp_audio
    ]
    print("[VideoMaker] Concatenating audio files...")
    subprocess.run(cmd_concat_audio, check=True)

    # 静止画(とりあえず1枚目だけ使用)をもとに動画を作成
    if not image_files:
        raise ValueError("No subtitle images provided.")

    first_image = image_files[0]
    # 連結音声の長さ分ループさせる例（一定秒数表示）
    # -shortest オプションで音声より短い場合に終了
    cmd_make_video = [
        "ffmpeg",
        "-y",
        "-loop", "1",
        "-i", first_image,
        "-i", temp_audio,
        "-shortest",
        "-c:v", "libx264",
        "-c:a", "aac",
        "-pix_fmt", "yuv420p",
        output_path
    ]
    print("[VideoMaker] Creating final video with FFmpeg...")
    subprocess.run(cmd_make_video, check=True)

    # 後始末
    os.remove(concat_list_file)
    os.remove(temp_audio)

    print(f"[VideoMaker] Final video created: {output_path}")
    return output_path
