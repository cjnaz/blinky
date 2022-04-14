# blinky - A threaded multiple LED driver for Raspberry Pi

blinky provides background process LED flashing operations for multiple LEDs.  blinky is supported on popular driver
libraries RPi.GPIO, pigpio, and gpiozero.  Usage is simple, with full demo code provided.

` `  
## Usage (blinky_demo.py)
```
$ ./blinky_demo.py -h
usage: blinky_demo.py [-h] [-d {pigpio,RPi.GPIO,gpiozero}] [-s SERVER] [-p PORT] [-v]

blinky_demo - A threaded multiple LED driver for Raspberry Pi
V0.2 220413

optional arguments:
  -h, --help            show this help message and exit
  -d {pigpio,RPi.GPIO,gpiozero}, --driver {pigpio,RPi.GPIO,gpiozero}
                        Select which driver mode to use (default = RPi.GPIO).
  -s SERVER, --server SERVER
                        If using the pigpio driver mode, what server (default localhost)?
  -p PORT, --port PORT  If using the pigpio driver mode, what port (default 8888)?
  -v, --verbose         Enable debug logging for blinky commands.
```


` `  
## Example output (blinky_demo.py, with --verbose)
```
pi@RPi2:/mnt/share/dev/pi/dev/blinky $ ./blinky_demo.py -d pigpio -s rpi3.lan -v
blinky thread Blue on GPIO  4 created.
blinky thread Red on GPIO 17 created.
blinky thread Yellow on GPIO 20 created.
Blue command:  <[200, '10', 2]>
  Period 0.2s, bitstream ['1', '0'], repeat 2
Blue command:  <[50, '10000000', 8, 1]>
Saving prior blinky command for Blue.
  Period 0.05s, bitstream ['1', '0', '0', '0', '0', '0', '0', '0'], repeat 8
Blue command:  <[0, 0, 0, 2]>
Restoring prior blinky command for Blue.
  Period 0.2s, bitstream ['1', '0'], repeat 2
Blue command:  <[0, 0, 0, 2]>
Restoring prior blinky command for Blue.
  Period 0.2s, bitstream ['1', '0'], repeat 2
Yellow command:  <[500, '10', -1]>
Blue command:  <[500, '10', -1]>
  Period 0.5s, bitstream ['1', '0'], repeat -1
Red command:  <[500, '10', 3]>
  Period 0.5s, bitstream ['1', '0'], repeat -1
  Period 0.5s, bitstream ['1', '0'], repeat 3
Red command:  <[50, '10', 10]>
  Period 0.05s, bitstream ['1', '0'], repeat 10
Yellow command:  <[50, '1010000000', 10]>
  Period 0.05s, bitstream ['1', '0', '1', '0', '0', '0', '0', '0', '0', '0'], repeat 10
Blue command:  <[150, '1000', -1]>
  Period 0.15s, bitstream ['1', '0', '0', '0'], repeat -1
Red command:  <[0, '1', 1]>
  Period 0.0s, bitstream ['1'], repeat 1
Yellow command:  <[500, '01', -1]>
  Period 0.5s, bitstream ['0', '1'], repeat -1
Blue command:  <[500, '10', -1]>
  Period 0.5s, bitstream ['1', '0'], repeat -1
Hit Ctrl-C to exit
^C
Cleaning up
Red command:  <[0, '0', 1, -99]>
  Period 0.0s, bitstream ['0'], repeat 1
Blinky Red thread exiting
Yellow command:  <[0, '0', 1, -99]>
  Period 0.0s, bitstream ['0'], repeat 1
Blinky Yellow thread exiting
Blue command:  <[0, '0', 1, -99]>
  Period 0.0s, bitstream ['0'], repeat 1
Blinky Blue thread exiting

```

` `  
## Setup notes
- Developed on Raspbian GNU/Linux 11 (bullseye) and Python 3.9.2.
- Place the files in a directory on your pi.
- To run the demo, adjust blinky_demo.py for which GPIOs you have LEDs connected to.
- Run the demo!
- blinky (and blinky_demo.py) works on 3 popular driver libraries:  pigpio, RPi.GPIO, and gpiozero

` `  
## blinky interface

First, create an message queue, blinky instance, and thread for each LED you wish to control, EG:

    BlueLED_q    = queue.Queue()
    BlueLED_inst = blinky.blinky("Blue", pio, BlueLED_GPIO, BlueLED_q, debug=True)
    BlueLED_th   = BlueLED_inst.run()
        
The LED is controlled through messages (in list form) sent through the related queue, EG:

    BlueLED_q.put ([500, "10", 2])      # 1s x2 blinks (2 blinks with on and off times = 500ms)

Command list structure:

    cmd[0]: Period in milliseconds for each bit.
    cmd[1]: Bitstream string - First bit is on the left, 1=On, 0=Off.  EG "1000"
    cmd[2]: Repeat count - Number of times to repeat the bitstream.  -1 will repeat forever.
    cmd[3]: Options flag (optional)
        blinky.CMD_SAVE:     Save prior command for later restore.  
        blinky.CMD_RESTORE:  Restore prior command.  (fields 0-2 are ignored)
            The restore stack is 1 deep.  Once saved, a command may be restored more than once.
        blinky.CMD_EXIT:     Execute current command and exit the thread

Command Examples:

    Produce the bit stream <100010001000> with a period of 50ms for each bit:
        BlueLED_q.put ([50, "1000", 3])       # Conclude with the LED off.

    Save a blink pattern, apply a new one, then restore the prior one:
        BlueLED_q.put ([500, "10", 2])                          # 1s x2 blinks (2 blinks with on and off times = 500ms)
        time.sleep (3)
        BlueLED_q.put ([50, "10000000", 2, blinky.CMD_SAVE])    # A 50ms blink over 400ms, repeated 2 times, while saving above 1s blinks
        time.sleep (3)
        BlueLED_q.put ([0,"0",0, blinky.CMD_RESTORE])           # Re-execute the prior saved 1s x2 blinks
        time.sleep (3)
        BlueLED_q.put ([0,"0",0, blinky.CMD_RESTORE])           # Re-execute the prior saved 1s x2 blinks again
        time.sleep (3)
    
    Terminate gracefully
        BlueLED_q.put ([0, "0", 1, blinky.CMD_EXIT])            # Off solid (no blink)
        BlueLED_th.join()

## Additional usage notes

- Multiple LED threads are not tightly synchronous.  Scheduling is based on the system and Python scheduling using the time.sleep() function.  There may be noticeable timing drift.
- You should call the respective RPi.GPIO / pigpio / gpiozero cleanup functions before exiting your code.  
    - RPi.GPIO:  RPi.GPIO.cleanup() is NOT called in the thread exit command as this will cleanup/release all GPIOs, not just the current GPIO.
    - pigpio:  Has no pin close() function.  Presumably you can just reprogram the pin function later in your code, as needed.  Remember to to a pigpio.stop() at the end of your script or eventually you will run out of pigpio server connections.
    - gpiozero:  close() IS called.  Only the selected pin is released.
- A command that is executing (such as blinking an LED indefinitely) will be interrupted if a new command is sent through the queue.  At the end of every bit-time the message queue is checked for a new message, and then immediately acted on.  Insert time.sleep() calls if you want to allow sufficient time for the prior command to complete before processing the new command.
- When issuing a CMD_EXIT on a blinky thread, the command carrying the exit may be delayed up to a full bit-time of the previously issued command.  It's best to .join() the thread before exiting your code.
- The CMD_SAVE and CMD_RESTORE options can be useful for interrupting a current blink sequence and executing a higher priority blink sequence, then restoring the prior one when the higher priority operation is complete.  Note that the save/restore stack is one deep, and that the last saved command may be repeatedly restored even after other blinky commands have been issued.

` `  
## Known issues and potential enhancements:
- Add support for BOARD pin numbering (currently only supports BCM).
- Add PWM fading controls, as with gpiozero.PWMLED()


` `  
## Version history
- 220413 V0.2  Added RPi.GPIO and gpiozero driver support
- 220108 V0.1  Added graceful termination (exit command)
- 211227 V0    New
