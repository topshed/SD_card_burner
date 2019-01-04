import psutil
import subprocess
from guizero import App, warn, PushButton, Slider, Waffle, Box,Text, Combo,CheckBox, yesno, info, error, MenuBar
import threading
import os
import logging

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
    if return_code: 
        raise subprocess.CalledProcessError(return_code, cmd)


def start():
    """ Function called when start buton is pressed
        It checks that a card has been inserted by looking for
        auto-mounted /dev/sda partitions
    """
    for p in psutil.disk_partitions():
        if p.device == "/dev/sda2" and p.mountpoint == "/media/pi/rootfs":
            # print("Found Pi OS")
            selected.enable()
            selected.text_color="#c51a4a"
            instructions.enable()
            image_selecter.enable()
            button_burn.enable() # do this now becuase users might want to go with the default
            text_start.disable()
            button_start.disable()
            
            
def selection(choice):
    """ Sets the text for the selected  text guizero object
        Also sets the global to_be_burned variable to be the
        selected img file by calling image_map
    """
    global to_be_burned
    selected.value = choice + " selected"    
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
    
    for path in execute(["sudo","dd", "if="+to_be_burned, "of=/dev/sda", "status=progress"]): 
        #print(path.split(" ")[0])
        dd_value = path.split(" ")[0].rstrip()
        if dd_value != "" and  dd_value[-2] != "+":
            how_far = round( ( int(path.split(" ")[0].rstrip()) / int(total_size) ) *100, 1 )
            progress.value = str(how_far) + "%"
            i = int(how_far)//10
            if i > 0:
                status.set_pixel(i-1,0,"#8cc04b")

    info("Process complete", "Please remove your SD card - thanks!")
    button_start.enable()
    button_burn.disable()
    text_start.enable()
    button_abort.disable()
    progress.hide()
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
        progress.hide()
        status.set_all("black")

        
    
def burn():
    """ Starts the buring process after getting confirmation
        from the user, first by umounting any partitions
        then launching dd_run as a seperate thread to avoid blocking the gui (and
        thereby preventing status updates from being shown)
    """
    selected.disable()
    button_start.disable()
    instructions.disable()
    image_selecter.disable()
    button_burn.disable()
    button_abort.enable()
    print("unmounting SD card")
    subprocess.Popen("sudo umount /dev/sda2", shell=True)
    subprocess.Popen("sudo umount /dev/sda2", shell=True)
    go_ahead = yesno("Warning!", "This will erase everything on the SD card - are you sure?")
    if go_ahead == True:
        print("STarting...")
        t = threading.Thread(target=dd_run)
        t.start()

 
    else:
        print("Aborting")
        #text_start.enable()
    
    
app = App(title="SD Card Burner",layout="grid",height=400, width=800, bg="#c51a4a")

text_start = Text(app, text= "Please insert your SD card into the slot and then press'start'",size=22, color='white', grid=[1,1,9,1])

button_start = PushButton(app, command=start,grid=[2,3,1,1], text = "START", width = 10, height = 10, image="/home/pi/SD_card_burner/images/start-button.png")

instructions = Text(app, text= "Choose an image for your SD card",enabled=False, grid=[1,4,5,1],color="white", size=20)
image_selecter = Combo(app, options=["Stretch Empty","Stretch Full", "Stretch Lite"],enabled =False, command=selection, grid=[3,5], selected="Stretch Empty")
image_selecter.text_color="white"
image_selecter.text_size=18
selected = Text(app,grid=[0,4],enabled=False, color='white')
button_burn = PushButton(app, command= burn,grid=[3,3], enabled=False, text="Burn SD card", image="/home/pi/SD_card_burner/images/burn.png")
progress = Text(app,grid=[5,7],visible=True, color="#8cc04b", size=18)
button_abort = PushButton(app, command= abort,grid=[5,3], enabled=False, text="Abort", image="/home/pi/SD_card_burner/images/cancel.png")
status = Waffle(app, width=10, height=1, grid=[0,7,6,1], dim=30, color='black')

app.display()
