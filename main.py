from KeyboardMonitor import keyboard_monitor, KeyboardMonitor


class Status:
    MACRO1 = 0x01
    MACRO2 = 0x02
    status = 0x00


def macro1(km: KeyboardMonitor):
    print("macro1 called")


def macro2(km: KeyboardMonitor):
    print("macro2 called")


@keyboard_monitor.register("1")
def switch_macro1(km: KeyboardMonitor):
    if Status.status == Status.MACRO1:
        return
    Status.status = Status.MACRO1
    print("switch to macro-1")
    keyboard_monitor.unregister("ctrl+b")
    keyboard_monitor.register("ctrl+a")(macro1)


@keyboard_monitor.register("2")
def switch_macro2(km: KeyboardMonitor):
    if Status.status == Status.MACRO2:
        return
    Status.status = Status.MACRO2
    print("switch to macro-2")
    keyboard_monitor.unregister("ctrl+a")
    keyboard_monitor.register("ctrl+b")(macro2)


keyboard_monitor.terminal_display_key = True

if __name__ == "__main__":
    keyboard_monitor.run()
    keyboard_monitor.stop()
