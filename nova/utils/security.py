import sys
import time
import traceback


class Security:

    def __init__(self):
        self.terminal = sys.stdout

    def exit_all_orders(self):
        pass

    def flush(self):
        # this flush method is needed for python 3 compatibility.
        # this handles the flush command by doing nothing.
        # you might want to specify some extra behavior here.
        pass




class Test (Security):

    def __init__(self):
        Security.__init__(self)

    def loop (self):
        a = 0
        # while True:
        #     print('Hello')
        #     if a == 3 :
        #     time.sleep(1)
        #     a += 1
        print('Hello')

        # This line opens a log file
        with open("log.txt", "w") as log:
            try:
                # some code
                # Below line will print any print to log file as well.
                x = 'a' + 0
                print("Creating DB Connection", file=log)
            except Exception:
                traceback.print_exc(file=log)


tes = Test()

tes.loop()
