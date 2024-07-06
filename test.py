import configparser
import collections
collections.Callable = collections.abc.Callable
import time

if __name__ == "__main__":
    # cp = configparser.RawConfigParser(strict = False)
    # tirePath = "C:\\Program Files (x86)\\Steam\\steamapps\\common\\assettocorsa\\content\\cars\\cky_bmw_m3_touring\\data\\tyres.ini"
    # cp.read(tirePath, encoding="utf8")
    # print(cp)

    s = time.time()
    lc = 0
    while True:
        if time.time() - s >= 1:
            print("sdfsdf")
            s = time.time()
            lc += 1 
        if lc > 10:
            break
