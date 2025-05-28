# class Ticker
Ticker class provides interfaces for making periodical function calls

### Args
- hz: int - wanted updates per second, Hz

### tick
Updates timer and sleeps until needed update speed. Blocks thread

### check
Updates timer and returns if delay has gone or not. Useful for non-blocking check, for ex. in camera frames processing