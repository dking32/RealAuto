import keyboard  # using module keyboard
pressed = False
while True:  # making a loop
    try:  # used try so that if user pressed other than the given key error will not be shown
        if keyboard.is_pressed(' '):  # if key ' ' is pressed
            if not pressed: 
                print(f"You pressed space, pressed is {pressed}")
            pressed = True
        else:
            pressed = False
    except:
        break  # if user pressed a key other than the given key the loop will break