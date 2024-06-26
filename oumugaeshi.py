﻿# オウム返しプログラム oumugaeshi.py Ver. 1.3.1(W) by JA1XPM & Microsoft Copilot 2024.05.27
# DTR コントロール版
# プラットフォーム:windows11, python3
# 仕様:無線機のオーディオ入出力に接続し、送信は指定したCOMポートのDTR、VOX、Signalinkの自動送信を利用
# リグはUSBのオーディオとDTR SENDが使えるものなら超簡単(IC-9700だと、USB SEND->USB(A)DTR選択、モードをDATAにする)
# 使い方: python oumugaeshi.py [COMn]
# COMポートを指定しない場合は COMポート制御をしない(送受信切替はSignalink等のVOX系制御に依存する)
# オーディオ入出力デバイスを数字で指定する
# 終了は ctrl+c
#
# Ver1.3 IDを送出機能追加。音声ファイル再生終了後にid.wavがあれば再生、無ければ再生しないようにした。
# Ver1.3.1 録音したファイルの後ろにある無音時間(デフォルトで3秒)をカットするようにした。


import pyaudio
import wave
import audioop
import time
from datetime import datetime
import serial  # pySerialをインポート
import sys  # sysをインポート

# 音声デバイスの一覧表示と選択
def select_audio_device(device_type):
    print(f"Available {device_type} devices:")
    for i in range(p.get_device_count()):
        device_info = p.get_device_info_by_index(i)
        if (device_type == 'input' and device_info['maxInputChannels'] > 0) or \
           (device_type == 'output' and device_info['maxOutputChannels'] > 0):
            print(i, device_info['name'])
    device = int(input(f"Please enter the number of the {device_type} device: "))
    return device

# COMポートの設定
com_port = sys.argv[1] if len(sys.argv) > 1 else None  # 起動パラメータでCOMポートを指定
if com_port:
    ser = serial.Serial(com_port)  # COMポートを開く
    ser.setDTR(False)  # DTRを強制OFFにする
else:
    print("COMポートが指定されなかったので、DTR制御をしません.")

p = pyaudio.PyAudio()

# 音声入力デバイスの選択
input_device = select_audio_device('input')

# 音声出力デバイスの選択
output_device = select_audio_device('output')

# 録音のパラメータ
chunk = 1024  # データ読み取り単位
format = pyaudio.paInt16  # データフォーマット
channels = 1  # モノラル
rate = 15000  # サンプリングレートを15KHzに変更
record_seconds = 30  # 録音時間（秒）
silence_threshold = 500  # 無音と判断する閾値
silence_duration = 3  # 無音が続く時間（秒）を定義
filename = "temp.wav"  # 受信音声ファイル名
filename2 = "record.wav" # 送信音声ファイル名

try:
    while True:  # メイン処理をループ
        stream = p.open(format=format,
                        channels=channels,
                        rate=rate,
                        input=True,
                        output=False,
                        input_device_index=input_device,
                        frames_per_buffer=chunk)

        print(datetime.now().strftime('%Y%m%d,%H:%M:%S'), " 音声の入力を待っています...")  # 時刻を先に表示
        frames = []
        while True:  # 音声入力を検知するまで無限ループ
            data = stream.read(chunk)
            rms = audioop.rms(data, 2)  # 音量の計算
            if rms > silence_threshold:  # 音量が閾値を超えたら録音開始
                print(datetime.now().strftime('%Y%m%d,%H:%M:%S'), " 録音を開始します...")  # 時刻を先に表示
                frames.append(data)
                break

        silence_counter = 0  # 無音時間のカウンタ
        for i in range(0, int(rate / chunk * (record_seconds-1))):
            data = stream.read(chunk)
            rms = audioop.rms(data, 2)  # 音量の計算
            if rms < silence_threshold:
                silence_counter += 1  # 無音時間をカウント
            else:
                silence_counter = 0  # 音がある場合はカウンタをリセット
            if silence_counter > silence_duration * rate / chunk:  # 無音時間が指定時間を超えたら録音停止
                print(datetime.now().strftime('%Y%m%d,%H:%M:%S'), " 録音終了（無音検出）")  # 時刻を先に表示
                break
            frames.append(data)

        print(datetime.now().strftime('%Y%m%d,%H:%M:%S'), " 録音終了")  # 時刻を先に表示

        stream.stop_stream()
        stream.close()

        wf = wave.open(filename, 'wb')
        wf.setnchannels(channels)
        wf.setsampwidth(p.get_sample_size(format))
        wf.setframerate(rate)
        wf.writeframes(b''.join(frames))
        wf.close()

        # 無音時間のカット
        # wavファイルを読み込む
        wav = wave.open(filename, 'r')

        # wavファイルの情報を取得
        framerate = wav.getframerate()
        nframes = wav.getnframes()
        duration = nframes / float(framerate)

        # 最後の無音時間秒分のフレーム数を計算
        last_seconds = int(framerate * silence_duration)

        # 最後の無音時間秒分のデータを除いたデータを新しいwavファイルとして書き出す
        wav_out = wave.open(filename2, 'w')
        wav_out.setparams(wav.getparams())
        wav_out.writeframes(wav.readframes(nframes - last_seconds))
        wav_out.close()
        wav.close()

        print(datetime.now().strftime('%Y%m%d,%H:%M:%S'), " 録音した音声を再生します...")  # 時刻を先に表示
        if com_port:
            ser.setDTR(True)  # DTRをONにする

        # 音声ファイルの再生
        wf = wave.open(filename2, 'rb')

        p = pyaudio.PyAudio()

        stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),
                        channels=wf.getnchannels(),
                        rate=wf.getframerate(),
                        output=True,
                        output_device_index=output_device)

        data = wf.readframes(chunk)

        while data != b'':
            stream.write(data)
            data = wf.readframes(chunk)

        # 音声の再生が完全に終了するのを待つ
        time.sleep(0.5)

        stream.stop_stream()
        stream.close()

        p.terminate()

        # id.wav の再生
        try:
            wf_id = wave.open("id.wav", 'rb')
            stream_id = p.open(format=p.get_format_from_width(wf_id.getsampwidth()),
                               channels=wf_id.getnchannels(),
                               rate=wf_id.getframerate(),
                               output=True,
                               output_device_index=output_device)

            data_id = wf_id.readframes(chunk)

            while data_id != b'':
                stream_id.write(data_id)
                data_id = wf_id.readframes(chunk)

            # 音声の再生が完全に終了するのを待つ
            time.sleep(0.5)

            stream_id.stop_stream()
            stream_id.close()

            wf_id.close()
        except FileNotFoundError:
            print("Error: id.wav not found.")
        except Exception as e:
            print("Error:", e)

        if com_port:
            ser.setDTR(False)  # DTRをOFFにする

except KeyboardInterrupt:
    # Ctrl+Cが押されたときの処理
    print(datetime.now().strftime('%Y%m%d,%H:%M:%S'), " プログラムを終了します...")
    if com_port:
        ser.setDTR(False)  # DTRをOFFにする
        ser.close()  # COMポートを閉じる

