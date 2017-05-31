import threading
import time


def main():
    global flag
    while flag:
        print "Hello!"
        time.sleep(2)
    print "Goodbye!"
def update():
    global flag
    flag = False

if __name__ == "__main__":
    flag = True
    m = threading.Thread(target=main)
    m.start()
    u = threading.Thread(target=update)
    time.sleep(2)
    u.start()
