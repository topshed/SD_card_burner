import psutil
import subprocess
from guizero import App, warn, PushButton, Waffle, Box, Text, Combo, Picture, yesno, info, error, Window
import threading
import os
import logging
import logzero
from logzero import logger
import time

TEST_MODE = True
logzero.logfile("/home/pi/SD_card_burner/burn.log")
formatter = logging.Formatter('%(name)s - %(asctime)-15s - %(levelname)s: %(message)s')
logzero.formatter(formatter)
logger.info("App started")
to_be_burned = "/home/pi/2018-11-13-raspbian-stretch-lite.img"

def image_map(name):
    """ Returns the path to an img based on the name argument -
        usisually from the selected combo box
    """
    if name == "Stretch Full":
        image_file = "/home/pi/2018-11-13-raspbian-stretch-lite.img"
    elif name == "Stretch Empty":
        image_file = "/home/pi/2018-11-13-raspbian-stretch-lite.img"
    elif name == "Stretch Lite":
        image_file ="/home/pi/2018-11-13-raspbian-stretch-lite.img"
    return(image_file)

stretch_full_info = """
Stretch Full:
This image includes the desktop and recommended software based on Debian Stretch
"""
stretch_empty_info = """
Stretch Empty:
This image includes the desktop but only has a few additional software applications installed.
Based on Debian Stretch
"""
stretch_lite_info = """
Stretch Lite:
A minimal image with no desktop (command line only).
Based on Debian Stretch
"""
def execute(cmd):
    """ Runs a given system command passed in as the cmd argument
        yields stderr as it is updated so the progress of a long command
        can be handled and processed, in this case to provide a status
        update
    """
    global pid
    popen = subprocess.Popen(cmd, stderr=subprocess.PIPE, universal_newlines=True)
    pid = popen.pid
    print(pid)
    for stdout_line in iter(popen.stderr.readline, ""):
        yield stdout_line
    popen.stderr.close()
    return_code = popen.wait()
    #if return_code:
       # raise subprocess.CalledProcessError(return_code, cmd)


def start():
    """ Function called when start buton is pressed
        It checks that a card has been inserted by looking for
        auto-mounted /dev/sda partitions
    """
    found_sd = False
    for p in psutil.disk_partitions():
        if p.device == "/dev/sda2" and p.mountpoint == "/media/pi/rootfs":
            logger.info("Found SD card - looks like Raspbian")
            found_sd = True
        elif p.device == "/dev/sda1" and p.mountpoint == "/media/pi/boot":
            logger.info("Found SD card- looks like Raspbian")
            found_sd = True
        elif p.device == "/dev/sda1" and p.fstype == "vfat":
            logger.info("Found SD card - looks like NOOBs")
            found_sd = True

    if found_sd:
        instructions.enable()
        image_selecter.enable()
        button_burn.enable() # do this now becuase users might want to go with the default
        text_start.disable()
        button_start.disable()
        info("Success!", "SD card detected. Please choose your operating system and then press 'Burn'")
    else:
        error("Uh oh!", "No SD card detected - please remove it and try again")


def selection(choice):
    """ Sets the text for the selected  text guizero object
        Also sets the global to_be_burned variable to be the
        selected img file by calling image_map
    """
    global to_be_burned
    to_be_burned = image_map(choice)

def dd_run():
    """ Runs the dd command to burn the img file
        Also updates the progress text (%) and the
        status waffle object.
        Launches an info window when the process is
        completed and resets progress and status
    """
    global to_be_burned

    progress.value = "0"
    progress.show()
    total_size = os.path.getsize(to_be_burned)
    st = time.time()
    if TEST_MODE:
        target = "/tmp/cac"
    else:
        target = "/dev/sda"
    for path in execute(["sudo","dd", "if="+to_be_burned, "of="+target, "status=progress"]):
        dd_value = path.split(" ")[0].rstrip()
        if dd_value != "" and  dd_value[-2] != "+":
            how_far = round( ( int(path.split(" ")[0].rstrip()) / int(total_size) ) *100, 1 )
            elapsed = time.time() - st
            remaining = ((100/how_far) - 1) * elapsed
            if how_far > 10:
                if remaining > 60:
                    progress.value = str(how_far) + "% - " + str(round(remaining/60,1)) + " mins left"
                else:
                    progress.value = str(how_far) + "% - " + str(int(remaining)) + " secs left"
            else:
                progress.value = str(how_far) + "% - calculating time left"
            i = int(how_far)//10
            if i > 0:
                status.set_pixel(i-1,0,"#8cc04b")

    info("Process complete", "Please remove your SD card - thanks!")
    logger.info("burn completed")
    button_start.enable()
    button_burn.disable()
    text_start.enable()
    button_abort.disable()
    help_button.enable()
    progress.value = ""
    status.set_all("black")

def abort():
    """ Kills a running dd process after offering a warning
        Reads the global pid variable and then finds the child processes
        (which get created because we run with sudo). Then kills them all
    """
    global pid
    check_abort = yesno("Warning!", "Stopping this process may leave your SD card in an unusable state. Are you sure you want to stop burning your SD card?")
    if check_abort:
        parent = psutil.Process(pid)
        for child in parent.children(recursive=True):
            k = subprocess.Popen(["sudo","kill", "-9", str(child.pid)])
        k = subprocess.Popen(["sudo","kill", "-9", str(pid)])
        button_start.enable()
        button_burn.disable()
        text_start.enable()
        button_abort.disable()
        help_button.enable()
        progress.value=""
        status.set_all("black")
        logger.info("Burn aborted")

def help_close():
    help_window.hide()

def help_show():
    help_window.show()


def burn():
    """ Starts the buring process after getting confirmation
        from the user, first by umounting any partitions
        then launching dd_run as a seperate thread to avoid blocking the gui (and
        thereby preventing status updates from being shown)
    """

    global to_be_burned
    button_start.disable()
    instructions.disable()
    image_selecter.disable()
    help_button.disable()
    button_burn.disable()
    button_abort.enable()
    print("unmounting SD card")
    if not TEST_MODE:
        subprocess.Popen("sudo umount /dev/sda2", shell=True)
        subprocess.Popen("sudo umount /dev/sda1", shell=True)
    go_ahead = yesno("Warning!", "This will erase everything on the SD card - are you sure?")
    if go_ahead == True:
        logger.info("Starting burn " + to_be_burned)
        t = threading.Thread(target=dd_run)
        t.start()


    else:
        logger.info("Chicken")
        button_start.enable()
        #text_start.enable()

def stop_close():
    error("Error", "Please do not try to close this window")

def stop_min():
    app.show()

app = App(title="SD Card Burner",layout="grid",height=400, width=800, bg="#c51a4a")
app.tk.attributes("-fullscreen",True)
app.repeat(10000,stop_min)

box_start = Box(app, grid = [0,1], width = 790, height = 30)
text_start = Text(box_start, text= "Please insert your SD card into the slot and then press 'start'",size=21, color='white')
box_pad1 = Box(app, grid = [0,2], width = 790, height = 10)
box_buttons = Box(app, grid = [0,3], width = 790, height = 100,layout= 'grid')
#box_buttons.set_border(2,'black')
button_start = PushButton(box_buttons, grid=[0,0], command=start, text = "START", image="/home/pi/SD_card_burner/images/start-button.png")
box_space1= Box(box_buttons, grid=[1,0], width = 100, height = 100)
button_burn = PushButton(box_buttons,  grid=[2,0], command= burn, enabled=False, text="Burn SD card", image="/home/pi/SD_card_burner/images/burn.png")
box_space2= Box(box_buttons, grid=[3,0], width = 100, height = 100)
button_abort = PushButton(box_buttons, grid=[4,0], command= abort, enabled=False, text="Abort", image="/home/pi/SD_card_burner/images/cancel.png")

box_progress = Box(app, grid = [0,4], width = 500, height = 160, layout='grid')
#box_progress.set_border(2,'black')
instructions = Text(box_progress, text= "Choose an image for your SD card",enabled=False, grid=[0,0,2,1],color="white", size=20)
image_selecter = Combo(box_progress, options=["Stretch Empty","Stretch Full", "Stretch Lite"],enabled =False, command=selection, grid=[0,1], selected="Stretch Empty")
image_selecter.text_color="white"
image_selecter.text_size=18
help_button = PushButton(box_progress, grid=[1,1],command=help_show, text="Need help choosing?")
help_button.text_color="white"
help_button.size=16

help_window = Window(app, height=350, width=700, title="Help", bg="#c51a4a")
help_window.hide()
help_text1=Text(help_window, text=stretch_full_info)
help_text1.size=12
help_text1.text_color="white"
help_text2=Text(help_window, text=stretch_empty_info)
help_text2.size=12
help_text2.text_color="white"
help_text3=Text(help_window, text=stretch_lite_info)
help_text3.size=12
help_text3.text_color="white"
button_help_close = PushButton(help_window, command=help_close, text="Close")

progress = Text(box_progress,visible=True, color="#8cc04b", size=18, grid = [0,2,2,1])
status = Waffle(box_progress, width=10, height=1, grid=[0,3,2,1], dim=30, color='black')

logo_box_outer = Box(app, grid=[0,5], width = 790, height = 120, layout='grid')
#logo_box_outer.set_border(2,'black')
logo_box_inner1 = Box(logo_box_outer, grid=[1,0], width = 550, height = 100)
#logo_box_inner1.set_border(2,'black')
#logo_box_inner2 = Box(logo_box_outer, grid=[1,0], width = 200, height = 100)
#logo_box_inner2.set_border(2,'black')
logo = Picture(logo_box_outer, grid=[0,0], image="/home/pi/SD_card_burner/images/Powered-by-Raspberry-Pi-Logo_Solid-Black-Screen.png")
app.on_close(stop_close)
app.display()
