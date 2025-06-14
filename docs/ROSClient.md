# ROSClient
Base client for MiniROS

### Args
- name: str - UNIQUE name of the node. 3 symbols
- ip: str - MiniROS server IP address
- port: int - MiniROS server port

### run
Runs thread with mainloop. Returns started thread

### topic
Creates new topic and returns Topic class interface
- field: str - field name
- datatype: Datatype - type of data (subclass of miniros.datatypes.Datatype). 
Only your-client-side (use miniros.decorators.parsedata(Datatype) on other client)

### anon
Sends anon message to specified client on specified field
- node: str - node name
- field: str - field name
- data: bytearray - encoded data to send