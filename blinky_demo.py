#!/usr/bin/env python3
"""blinky_demo - A threaded multiple LED driver for Raspberry Pi
"""

__version__ = "V0.2 220413"

#==========================================================
#
#  Chris Nelson, Copyright 2022
#
# 220413 V0.2  Added RPi.GPIO and gpiozero driver support
# 220108 V0.1  Added graceful termination (exit command)
# 211227 V0    New
#
# Changes pending
#   
#==========================================================

import argparse
import time
import signal
import queue
import sys
import blinky

# Configs / Constants
BlueLED_GPIO   = 4
RedLED_GPIO    = 17
YellowLED_GPIO = 20


def cleanup():
    global BlueLED_q, RedLED_q, YellowLED_q
    global BlueLED_th, RedLED_th, YellowLED_th
    print ("\nCleaning up")
    RedLED_q.put    ([0, "0", 1, blinky.CMD_EXIT])
    YellowLED_q.put ([0, "0", 1, blinky.CMD_EXIT])
    BlueLED_q.put   ([0, 0,   0, blinky.CMD_RESTORE])
    time.sleep(1.5)
    BlueLED_q.put   ([0, "0", 1, blinky.CMD_EXIT])   # Off solid (no blink)

    BlueLED_th.join()
    RedLED_th.join()
    YellowLED_th.join()

    if args.driver == 'pigpio':
        driver.stop()



def keyboardInterruptHandler(signal, frame):
    cleanup()
    sys.exit(0)
signal.signal(signal.SIGINT, keyboardInterruptHandler)



if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__ + __version__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('-d', '--driver', choices=['pigpio', 'RPi.GPIO', 'gpiozero'], default='RPi.GPIO',
                        help=f"Select which driver mode to use (default = RPi.GPIO).")
    parser.add_argument('-s', '--server', default='localhost',
                        help=f"If using the pigpio driver mode, what server (default localhost)?")
    parser.add_argument('-p', '--port', default=8888,
                        help=f"If using the pigpio driver mode, what port (default 8888)?")
    parser.add_argument('-v', '--verbose', action="store_true",
                        help=f"Enable debug logging for blinky commands.")
    args = parser.parse_args()

    verbose = True  if args.verbose == True  else False

    if args.driver == 'pigpio':
        import pigpio
        driver = pigpio.pi(args.server, args.port)
        if not driver.connected:
            print (f"Failed to connect to pigpio host:port <{args.server}:{args.port}>.  Aborting. ")
            sys.exit()
    elif args.driver == 'RPi.GPIO':
        driver = blinky.DRIVER_RPIGPIO
    elif args.driver == 'gpiozero':
        driver = blinky.DRIVER_GPIOZERO
    else:
        print (f"Unknown driver mode <{args.driver}>.  Aborting.")

    # Instantiate the "status" LED threads
    BlueLED_q      = queue.Queue()
    BlueLED_inst   = blinky.blinky("Blue", driver, BlueLED_GPIO, BlueLED_q, debug=verbose)
    BlueLED_th     = BlueLED_inst.run()

    RedLED_q       = queue.Queue()
    RedLED_inst    = blinky.blinky("Red", driver, RedLED_GPIO, RedLED_q, debug=verbose)
    RedLED_th      = RedLED_inst.run()

    YellowLED_q    = queue.Queue()
    YellowLED_inst = blinky.blinky("Yellow", driver, YellowLED_GPIO, YellowLED_q, debug=verbose)
    YellowLED_th   = YellowLED_inst.run()


    # Saving and restoring a blink pattern
    BlueLED_q.put ([200, "10", 2])                          # 800ms x2 blinks (2 blinks with on and off times = 200ms)
    time.sleep (3)
    BlueLED_q.put ([50, "10000000", 8, blinky.CMD_SAVE])    # A 50ms blink over 400ms, repeated 8 times, while saving above 1s blinks
    time.sleep (3)
    BlueLED_q.put ([0,0,0, blinky.CMD_RESTORE])             # Re-execute the prior saved 1s x2 blinks
    time.sleep (3)
    BlueLED_q.put ([0,0,0, blinky.CMD_RESTORE])             # Re-execute the prior saved 1s x2 blinks again
    time.sleep (3)

    # Running 3 LEDs concurrently
    BlueLED_q.put   ([500, "10", -1])
    RedLED_q.put    ([500, "10", 3])
    YellowLED_q.put ([500, "10", -1])
    time.sleep(5)

    # Interrupt and replace blink patterns on all 3 LEDs
    BlueLED_q.put   ([150, "1000", -1])                     # New commands are accepted after each respective 
    RedLED_q.put    ([50, "10", 10])                        # prior bit time - 500ms as set above.
    YellowLED_q.put ([50, "1010000000", 10])
    time.sleep(2)

    BlueLED_q.put   ([500, "10", -1])
    RedLED_q.put    ([0, "1", 1])                           # On solid (no blink).
    YellowLED_q.put ([500, "01", -1])
    time.sleep(.5)

    print ("Hit Ctrl-C to exit")
    while 1:
        pass

    # cleanup()
    # sys.exit()


