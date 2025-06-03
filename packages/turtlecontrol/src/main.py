from miniros import ROSClient
from miniros.util import datatypes
from miniros.util.decorators import decorators
import keyboard

class TurtleControlClient(ROSClient):
    def update_pos(self, x, z, rot):
        data = datatypes.Movement(
            datatypes.Vector(x, 0, z),
            datatypes.Vector(0, rot, 0)
        )
        self.anon("turtlesim", "moveto", datatypes.Movement.encode(data))

    @decorators.parsedata(datatypes.Vector, 1)
    def on_turtlesim_pos(self, data):
        pass

client = TurtleControlClient("turtlecontrol")

t = client.run()

keyboard.on_release(lambda e: client.update_pos(0, 0, 0))

keyboard.on_press_key("Left", lambda e: client.update_pos(0, -5, 0))
keyboard.on_press_key("Right", lambda e: client.update_pos(0, 5, 0))
keyboard.on_press_key("Up", lambda e: client.update_pos(5, 0, 0))
keyboard.on_press_key("Down", lambda e: client.update_pos(-5, 0, 0))

keyboard.on_press_key("e", lambda e: client.update_pos(0, 0, 5))
keyboard.on_press_key("q", lambda e: client.update_pos(0, 0, -5))

print("Arrows for controlling movement, q/e for rotation")

t.join()