class Utils:
    def time_convert(sec):
        mins = sec // 60
        sec = sec % 60
        hours = mins // 60
        mins = mins % 60
        return "{0}:{1}:{2}".format(
            int(hours), str(int(mins)).rjust(2, "0"), str(int(sec)).rjust(2, "0")
        )

    def divide_chunks(l, n):
        for i in range(0, len(l), n):
            yield l[i : i + n]
