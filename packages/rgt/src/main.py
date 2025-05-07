from blockplotlib.blockplotlib import RectangleBlock, Arrow, Node
import blockplotlib
from miniros import ROSClient

class RGTClient(ROSClient):
    def __init__(self, ip = "localhost", port = 3000):
        super().__init__("rgt", ip, port)

        self.client.on_rosstat = self.on_rosstat

    def on_rosstat(_, val: dict):
        nds = {}
        objects = []

        c = 0
        for node in val.keys():
            n = RectangleBlock((c * 30, (c // 4) * 30), node)

            objects.append(n)

            nds[node] = {"node": n, "fields": {}}

            q = 0
            for field in val[node]["fields"].keys():
                f = Node((c * 30 + 10, (c // 4) * 30 - 12 + q * 6), field)
                arr = Arrow(n, f, "e")

                objects.append(arr)
                objects.append(f)

                nds[node]["fields"][field] = f

                q += 1

            c += 1

        for node in val.keys():
            for field in val[node]["fields"].keys():
                for sub in val[node]["fields"][field]["subscribers"]:
                    arr = Arrow(nds[node]["fields"][field], nds[sub]["node"], "e")
                    objects.append(arr)

        blockplotlib.place_patches(objects)
        blockplotlib.show()
            

cl = RGTClient()
t = cl.run()

cl.client.rosstat()

while True:
    try:
        d = input("q/u > ")

        if d == "q":
            quit()

        if d == "u":
            cl.client.rosstat()
    except:
        pass