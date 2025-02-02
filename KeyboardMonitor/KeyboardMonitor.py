import string
import keyboard
import threading
import atexit

from typing import Any, Callable, Dict, List, Optional, Tuple, TypeVar, Union


T = TypeVar("T")

REFL_FNC_TYPE = Callable[["KeyboardMonitor"], Any]
DICT_FNC_MAP = Dict[int, REFL_FNC_TYPE]


def RTLAST(args: Tuple[Any, Optional[str]]) -> Any:
    return args[-1]


class CALLBACK_REFLECTOR:
    """回调函数注册器
    注册的回调函数为全局回调函数, 即不同的实例共享回调函数
    通过注册回调函数, 可以在按下对应按键后根据返回值(str)执行对应的函数集

    Functions:
        get(name: str, default: Optional[T] = None) -> Union[List[REFL_FNC_TYPE], Optional[T]]
            获取注册的回调函数

        register(name: str) -> Callable[[REFL_FNC_TYPE], None]
            注册新的回调函数

        unregister(name: str) -> None
            解除回调函数
    """

    reflectors: Dict[str, List[REFL_FNC_TYPE]] = dict()

    @classmethod
    def get(
        cls, name: str, default: Optional[T] = None
    ) -> Union[List[REFL_FNC_TYPE], Optional[T]]:
        return cls.reflectors.get(name, default)

    @classmethod
    def register(cls, name: str) -> Callable[[REFL_FNC_TYPE], None]:
        def wrapper(fnc: REFL_FNC_TYPE) -> None:
            if name in cls.reflectors:
                cls.reflectors[name].append(fnc)
            else:
                cls.reflectors[name] = [fnc]
            return None

        return wrapper

    @classmethod
    def unregister(cls, name: str) -> None:
        if name in cls.reflectors:
            del cls.reflectors[name]


KEY_REFLECTOR: Dict[str, DICT_FNC_MAP] = {"ctrl+c": {0: lambda km: km.stop()}}
SHIFT_REFLECTOR: Dict[str, str] = {
    ",": "<",
    ".": ">",
    "/": "?",
    ";": ":",
    "'": '"',
    "[": "{",
    "]": "}",
    "\\": "|",
    "1": "!",
    "2": "@",
    "3": "#",
    "4": "$",
    "5": "%",
    "6": "^",
    "7": "&",
    "8": "*",
    "9": "(",
    "0": ")",
    "-": "_",
    "=": "+",
    "`": "~",
}

SHIFT_REFLECTOR.update({v.upper(): v for v in string.ascii_lowercase})
SHIFT_REFLECTOR.update({v: k for k, v in SHIFT_REFLECTOR.items()})


class Key:
    def __init__(self, key: str) -> None:
        self.key: str = key
        self.shift: str = SHIFT_REFLECTOR.get(key, key)

    def __eq__(self, value: Union[object, str, "Key"]) -> bool:
        if isinstance(value, Key):
            value = value.key
        return self.key == value or self.shift == value


class KeyboardMonitor(threading.Thread):
    """基于多线程的键盘监控器
    注册的按键映射为全局按键映射, 即不同的实例共享按键映射
    通过注册按键映射, 可以在按下对应按键后执行对应的函数集
    此类为单例模式/多例模式, 此包提供了一个全局的键盘监控器实例`keyboard_monitor`

    Functions:
        add(new_key: str, fnc: REFL_FNC_TYPE, _id: Optional[int] = None) -> None
            添加新的按键映射

        register(refl_str: str, _id: Optional[int] = None) -> Callable[[REFL_FNC_TYPE], REFL_FNC_TYPE]
            注册新的按键映射

        unregister(key: Optional[str] = None, fnc: Optional[REFL_FNC_TYPE] = None, _id: Optional[int] = None) -> None
            解除按键映射

        get_total_monitor_num() -> int
            获取当前监控器实例的数量

        run() -> None
            开始监控

        stop() -> None
            停止监控

    """

    total_monitor: List["KeyboardMonitor"] = list()

    def __init__(self) -> None:
        super().__init__()
        self.total_monitor.append(self)
        self.function_threads: List[threading.Thread] = list()
        self.cur_pressed_key: List[Key] = list()
        self.__stop = False
        self.terminal_display_key: bool = False

    def callback(self, res: Optional[str]) -> None:
        if res is None:
            return
        fncs: Optional[List[REFL_FNC_TYPE]] = CALLBACK_REFLECTOR.get(res, None)
        if fncs is None:
            return
        for f in fncs:
            f(self)

    def _solve(self, key: keyboard.KeyboardEvent) -> Any:
        def run_funcs(functions: DICT_FNC_MAP) -> None:
            for f in functions.values():
                res: Any = f(self)
                self.callback(res=res)

        name: Optional[str] = key.name
        name = name if name is not None else "None"
        mkey: Key = Key(name)

        if key.event_type == keyboard.KEY_DOWN and mkey not in self.cur_pressed_key:
            self.cur_pressed_key.append(mkey)
            keys: str = "+".join(k.key for k in self.cur_pressed_key)
            fncs: Optional[DICT_FNC_MAP] = KEY_REFLECTOR.get(keys, None)

            if self.terminal_display_key:
                print(keys)
            if fncs is None:
                return

            t = threading.Thread(target=run_funcs, args=(fncs,))
            self.function_threads.append(t)
            t.start()

        elif key.event_type == keyboard.KEY_UP:
            idx: int = len(self.cur_pressed_key) - 1
            while idx >= 0:
                if self.cur_pressed_key[idx] == mkey:
                    self.cur_pressed_key.pop(idx)
                idx -= 1

    def add(self, new_key: str, fnc: REFL_FNC_TYPE, _id: Optional[int] = None) -> None:
        if new_key in KEY_REFLECTOR:
            if _id is None:
                _id = 0 if not (ks := KEY_REFLECTOR[new_key].keys()) else max(ks) + 1
            KEY_REFLECTOR[new_key][_id] = fnc
        else:
            if _id is None:
                _id = 0
            KEY_REFLECTOR[new_key] = {_id: fnc}

    def register(
        self, refl_str: str, _id: Optional[int] = None
    ) -> Callable[[REFL_FNC_TYPE], REFL_FNC_TYPE]:
        def wrapper(fnc: REFL_FNC_TYPE) -> REFL_FNC_TYPE:
            nonlocal _id
            self.add(new_key=refl_str, fnc=fnc, _id=_id)
            return fnc

        return wrapper

    def _unregister_given_key(
        self, key: str, fnc: Optional[REFL_FNC_TYPE] = None, _id: Optional[int] = None
    ) -> None:
        if fnc is None and _id is None:  # fnc为None时删除映射
            del KEY_REFLECTOR[key]
        elif fnc is not None:  # id为None时删除所有fnc
            delete_keys: List[int] = []
            for k, v in KEY_REFLECTOR[key].items():
                if v == fnc:
                    delete_keys.append(k)
            for k in delete_keys:
                del KEY_REFLECTOR[key][k]

        elif _id is not None:
            del KEY_REFLECTOR[key][_id]

    def _unregister_ungiven_key(
        self,
        fnc: Optional[REFL_FNC_TYPE] = None,
        _id: Optional[int] = None,
    ) -> None:
        # 解除fnc的所有映射
        for k, v in KEY_REFLECTOR.items():
            delete_ids: List[int] = []
            for _id, f in v.items():
                if f == fnc:
                    delete_ids.append(_id)
            for _id in delete_ids:
                del KEY_REFLECTOR[k][_id]

    def unregister(
        self,
        key: Optional[str] = None,
        fnc: Optional[REFL_FNC_TYPE] = None,
        _id: Optional[int] = None,
    ) -> None:
        """
        解除按键映射


        Warning:
            key和fnc不能同时为None
            _id和fnc不能同时给出

        给出key时:
            - _id不为None时, 删除_id对应的fnc
            - fnc不为None时, 删除所有fnc
        未给出key时:
            - fnc不为None时, 删除所有fnc
            - _id不为None时, 删除_id对应的fnc

        Args:
            key (Optional[str], optional): 按键映射. 默认为NoneNone.
            fnc (Optional[REFL_FNC_TYPE], optional): 映射函数. 默认为NoneNone.
            _id (Optional[int], optional): 映射id. 默认为None.

        Raises:
            ValueError: key and fnc cannot be None at the same time
            ValueError: _id and fnc cannot be given at the same time
        """
        if not (key or fnc):
            raise ValueError("key and fnc cannot be None at the same time")
        if _id and fnc:
            raise ValueError("_id and fnc cannot be given at the same time")
        if key is not None:
            self._unregister_given_key(key=key, fnc=fnc, _id=_id)
        else:
            self._unregister_ungiven_key(fnc=fnc, _id=_id)

    @classmethod
    def get_total_monitor_num(cls) -> int:
        return len(cls.total_monitor)

    def run(self) -> None:
        while not self.__stop:
            key: keyboard.KeyboardEvent = keyboard.read_event()
            self._solve(key=key)

    def stop(self) -> None:
        self.__stop = True
        for t in self.function_threads:
            t.join()


@atexit.register
def final() -> None:
    global KeyboardMonitor
    for km in KeyboardMonitor.total_monitor:
        km.stop()


keyboard_monitor: KeyboardMonitor = KeyboardMonitor()
