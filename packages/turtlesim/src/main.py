import turtle
import miniros
from miniros.util.decorators import decorators
from miniros.util import datatypes
import time

X = 0
Z = 0
R = 0

class TurtleClient(miniros.ROSClient):
    def __init__(self, ip = "localhost", port = 3000):
        super().__init__("tsm", ip, port)

    @decorators.parsedata(datatypes.Dict, 1)
    def on_scl(self, data: dict, from_node: str):
        turtle.color(data["pen"], data["fill"])

    @decorators.parsedata(datatypes.Movement, 1)
    def on_mvt(self, data: datatypes.Movement, from_node: str):
        global X, Z, R

        X = data.pos.x
        Z = data.pos.z
        R = data.ang.y

client = TurtleClient()

print("Running")

t = client.run()
post = client.topic("pos")

x = 0
while True:
    time.sleep(0.005)
    turtle.forward(X)
    turtle.right(R)

    if x % 5 == 0:
        p = turtle.pos()
        post.post(
            datatypes.Vector.encode(
                datatypes.Vector(p[0], 0, p[1])
            )
        )