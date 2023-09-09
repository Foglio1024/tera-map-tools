import os

class Printer:
    def __clear_line(self):
        w = os.get_terminal_size().columns
        empty = ""
        for i in range(w):
            empty += " "
        print(empty, end="\r")

    def reprint(self, text):
        self.__clear_line()
        print(text, end="\r")

    def print(self, text):
        self.reprint(str(text) + "\n")