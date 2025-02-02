from KeyboardMonitor import keyboard_monitor, KeyboardMonitor



@keyboard_monitor.register("ctrl+t")
def ctrl_t(km: KeyboardMonitor):
    print("ctrl+t")

@keyboard_monitor.register("ctrl+alt+t")
def ctrl_alt_t(km: KeyboardMonitor):
    print("ctrl+alt+t")


keyboard_monitor.terminal_display_key = True

if __name__ == "__main__":
    keyboard_monitor.run()
    keyboard_monitor.stop()