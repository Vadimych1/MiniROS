import turtle
import miniros
from miniros.util.decorators import decorators
from miniros.util import datatypes
from miniros.util.util import Ticker

X = 0
Z = 0
R = 0

class TurtleClient(miniros.ROSClient):
    def __init__(self, ip = "localhost", port = 3000):
        super().__init__("turtlesim", ip, port)

    @decorators.parsedata(datatypes.Dict, 1)
    def on_setcolor(self, data: dict, from_node: str):
        turtle.color(data["pen"], data["fill"])

    @decorators.parsedata(datatypes.Movement, 1)
    def on_move(self, data: datatypes.Movement, from_node: str):
        global X, Z, R

        X = data.pos.x
        Z = data.pos.z
        R = data.ang.y

client = TurtleClient()

print("Running")

t = client.run()
post = client.topic("pos", datatypes.Vector)
rott = client.topic("rot", datatypes.Float)

x = 0
ticker = Ticker(200)
while True:
    turtle.forward(X)
    turtle.right(R)

    if x % 5 == 0:
        p = turtle.pos()
        r = turtle.heading()
        
        post.post(datatypes.Vector(p[0], 0, p[1]))
        rott.post(r)

    x += 1
