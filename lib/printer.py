class Printer:
    def __init__(self):
        self.text = ""

    def reprint(self, text):
        empty = ""
        for c in self.text:
            empty += " "
        print(empty, end="\r")
        print(text, end="\r")
        self.text = text

    def print(self, text):
        self.reprint(text + "\n")