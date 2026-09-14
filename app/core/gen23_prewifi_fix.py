from __future__ import annotations
from PySide6.QtCore import QObject, QTimer, Signal

#TODO vad klassen behöver: serial device

def rc4_ksa(S, key):
    for i in range(256):
        S[i] = i

    j = 0
    for i in range(256):
        j = (j + S[i] + key[i % len(key)]) & 0xFF
        S[i], S[j] = S[j], S[i]


def rc4_prga(S, length):
    out = [0] * length
    i = j = 0

    for k in range(length):
        i = (i + 1) & 0xFF
        j = (j + S[i]) & 0xFF
        S[i], S[j] = S[j], S[i]
        out[k] = S[(S[i] + S[j]) & 0xFF]

    return out


def string_to_bytes(s):
    return [ord(c) for c in s]


def byte_to_hex(b):
    return format(b, '02x')


def mac_to_skey(mac, key = "h6CX\t\t:<*{Y"):
    S = [0] * 256
    key_bytes = string_to_bytes(key)
    rc4_ksa(S, key_bytes)

    stream = rc4_prga(S, 256)
    mac_bytes = string_to_bytes(mac)

    result = ""
    for i in range(len(mac_bytes)):
        result += byte_to_hex(stream[i] ^ mac_bytes[i])

    extra_char = result[len(mac_bytes) >> 1]
    result += extra_char

    return result



def reset_network_cmd(mac: str):
    skey = mac_to_skey(mac)
    return f"SetWifi reset_network skey {skey}"

def getversion_cmd():
    return "GetVerion"



class Gen23WiFiFixer():

    gen23_wifiReset = Signal(str, list[str]) #serial(mac), [available wifi network ssid:s]
    gen23_fwResetRequired = Signal() # triggers page showing fw reset progress
    gen23_fwResetFinished = Signal(bool) # sucessfull or not TODO

    def __init__(self, parent: QObject | None = None) -> None:
        print("förfann")

