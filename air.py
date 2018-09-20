#! usr/bin/env python3
import os, sys
from module.daikin_controller import Daikin_Controller
os.chdir(sys.path[0])
controller = Daikin_Controller('192.168.1.168')
controller.update_log()
controller.update_panda_frame()
controller.set_temp()
print(controller)
