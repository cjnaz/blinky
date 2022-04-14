#!/usr/bin/env python3
"""blinky - A threaded multiple LED driver for Raspberry Pi

Commands to a LED blinky instance are passed thru a queue to the thread managing
the given LED.  One thread and queue per LED.  Command list structure:

cmd[0]: Period in milliseconds for each bit.
cmd[1]: Bitstream string - First bit is on the left, 1=On, 0=Off.  EG "1000"
cmd[2]: Repeat count - Number of times to repeat the bitstream.  -1 will repeat forever.
cmd[3]: Options flag (optional)
            blinky.CMD_SAVE:     Save prior command for later restore.  
            blinky.CMD_RESTORE:  Restore prior command.  (fields 0-2 are ignored)
                The restore stack is 1 deep.  Once saved, a command may be restored more than once.
            blinky.CMD_EXIT:     Execute current command and exit the thread

Examples:
    Set up a blinky instance (pio = pigpio handle)
        BlueLED_q    = queue.Queue()
        BlueLED_inst = blinky.blinky("Blue", pio, BlueLED_GPIO, BlueLED_q, debug=True)
        BlueLED_th   = BlueLED_inst.run()

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

pigpio, RPi.GPIO, and gpiozero driver libraries are supported.
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
#   Add support for BOARD pin numbering (currently only support BCM).
#   Add PWM fading controls, as with gpiozero.PWMLED()
#   
#==========================================================

import time
import sys
from threading import Thread


# Configs / Constants
CMD_SAVE        = 1
CMD_RESTORE     = 2
CMD_EXIT        = -99
DRIVER_RPIGPIO  = -1
DRIVER_GPIOZERO = -2


class blinky:

    def __init__(self, name, driver, gpio_num, queue, debug=False):
        self.name = name
        self.driver = driver
        self.gpio_num = gpio_num
        self.queue = queue
        self.name = name
        self.debug = debug

        if type(self.driver) is not int:    # Using pigpio.  driver will be a pigpio.pi server handle
            import pigpio
            driver.set_mode(self.gpio_num, pigpio.OUTPUT)
            driver.write(self.gpio_num, 0)
        elif self.driver == DRIVER_RPIGPIO:
            import RPi.GPIO as GPIO
            self.GPIO_instance = GPIO
            self.GPIO_instance.setwarnings(False)
            self.GPIO_instance.setmode(GPIO.BCM)
            self.GPIO_instance.setup(gpio_num, GPIO.OUT, initial=GPIO.LOW)
        elif self.driver == DRIVER_GPIOZERO:
            import gpiozero
            self.gpiozero_instance = gpiozero.OutputDevice(self.gpio_num, active_high=True, initial_value=False)
        else:
            print (f"Unknown driver mode.  Aborting.")
            sys.exit()


    def run(self):
        self.this_thread = Thread(target=self.blinky, daemon=True)
        self.this_thread.start()
        if self.debug:
            print (f"blinky thread {self.name} on GPIO {self.gpio_num:>2} created.")
        return self.this_thread


    def blinky(self):
        cmd = None
        cmd_save = None
        do_exit = False
        while True:
            try:
                cmd_prior = cmd
                cmd = self.queue.get()
                if self.debug:
                    print (f"{self.name} command:  <{cmd}>")

                if len(cmd) == 4:
                    if cmd[3] == CMD_SAVE:
                        if self.debug:
                            print (f"Saving prior blinky command for {self.name}.")
                        cmd_save = cmd_prior
                    elif cmd[3] == CMD_RESTORE:
                        if self.debug:
                            print (f"Restoring prior blinky command for {self.name}.")
                        if cmd_save != None:
                            cmd = cmd_save
                        else:
                            print (f"Attempted command restore with no prior save for {self.name}:  <{cmd}>.  Skipped.")
                            continue
                    elif cmd[3] == CMD_EXIT:
                        do_exit = True
                    else:
                        print (f"Invalid save/restore command received for {self.name}:  <{cmd}>.  Skipped.")
                        continue
                if len(cmd) == 3  or  len(cmd) == 4:
                    period    = float(cmd[0]) / 1000
                    bitstream = list(cmd[1])
                    rptcnt    = int(cmd[2])
                else:
                    print (f"Invalid command received for {self.name}:  <{cmd}>.  Skipped.")
                    continue
                
                if self.debug:
                    print (f"  Period {period}s, bitstream {bitstream}, repeat {rptcnt}")

                while True:
                    if not self.queue.empty():
                        break
                    for bit in bitstream:
                        if not self.queue.empty():
                            break
                        if type(self.driver) is not int:                    # pigpio mode
                            self.driver.write(self.gpio_num, int(bit))
                        elif self.driver == DRIVER_RPIGPIO:
                            self.GPIO_instance.output(self.gpio_num, int(bit))
                        else:                                               # gpiozero mode
                            self.gpiozero_instance.on()  if int(bit)  else self.gpiozero_instance.off()
                        time.sleep(period)
                    if do_exit:
                        if self.debug:
                            print (f"Blinky {self.name} thread exiting")
                        if self.driver == DRIVER_GPIOZERO:
                            self.gpiozero_instance.close()
                        sys.exit()                                          # Exit this thread
                    if rptcnt > 0:
                        rptcnt -= 1
                        if rptcnt == 0:
                            break
            except Exception as e:
                print (f"blinky error while processing command <{cmd}>.  Command aborted.\n  {e}")