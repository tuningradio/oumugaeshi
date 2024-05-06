# オウム返しプログラム oumugaeshi.py Ver. 1.0(W) by JA1XPM & Microsoft Copilot 2024.05.03
# DTR コントロール版
# プラットフォーム:windows11, python3
# 仕様:無線機のオーディオ入出力に接続し、送信は指定したCOMポートのDTR、VOX、Signalinkの自動送信を利用
# リグはUSBのオーディオ、DTR/RTS SENDが使えるものなら超簡単(IC-9700だと、USB SEND->USB(A)DTR選択、モードをDATAにする)
# 使い方: python oumugaeshi.py [COMn]
# COMポートを指定しない場合は COM1 を強制選択
# オーディオ入出力デバイスを数字で指定する
# 終了は ctrl+c

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
com_port = sys.argv[1] if len(sys.argv) > 1 else 'COM1'  # 起動パラメータでCOMポートを指定
ser = serial.Serial(com_port)  # COMポートを開く
ser.setDTR(False)  # DTRを強制OFFにする

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
filename = "record.wav"  # 音声ファイル名

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

        print(datetime.now().strftime('%Y%m%d,%H:%M:%S'), " 録音した音声を再生します...")  # 時刻を先に表示
        ser.setDTR(True)  # DTRをONにする

        # 音声ファイルの再生
        wf = wave.open(filename, 'rb')

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

        ser.setDTR(False)  # DTRをOFFにする
except KeyboardInterrupt:
    # Ctrl+Cが押されたときの処理
    print(datetime.now().strftime('%Y%m%d,%H:%M:%S'), " プログラムを終了します...")
    ser.setDTR(False)  # DTRをOFFにする
    ser.close()  # COMポートを閉じる
