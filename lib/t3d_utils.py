class T3DUtils:
    def parse_name(line):
        return line[line.find("Name=") + 5 : -1].replace('"', "")

    def parse_class(line):
        class_idx = line.find("Class=")
        class_name = ""
        if class_idx != -1:
            class_name = (
                line[class_idx : line.find("Name=")]
                .replace("Class=/Script/Engine.", "")
                .strip()
            )

        return class_name

    def parse_vector(line, name):
        if name != "":
            line = line.replace(f"{name}=", "")

        split = line.replace("(", "").replace(")", "").split(",")

        ret = []  # x, y, z

        for part in split:
            value = float(part.split("=")[1])
            ret.append(value)

        return ret

    def parse_mesh_path(line):
        ret = line[line.find('"') :].replace('"', "").replace("'", "") + ".psk"
        return ret.replace("/Game", "StaticMeshes\\")
