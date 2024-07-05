import logging
from functools import partial, partialmethod
from logging.handlers import WatchedFileHandler
from datetime import datetime
from os import makedirs
import coloredlogs


class MyLogger(logging.Logger):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @classmethod
    def addLevel(cls, name, lvl, style):
        setattr(cls, name.lower(), partialmethod(cls._anyLog, lvl))
        logging.addLevelName(lvl, name)
        coloredlogs.DEFAULT_LEVEL_STYLES.update({name: style})

    def _anyLog(self, level, message, *args, **kwargs):
        if self.isEnabledFor(level):
            self._log(level, message, args, **kwargs)

    def __call__(self, message, *args, **kwargs):
        if self.isEnabledFor(logging.INFO):
            self._log(logging.INFO, message, args, **kwargs)


# formatting the colorlogger
fmt = "[ %(asctime)s %(name)s (%(filename)s) %(lineno)d %(funcName)s() %(levelname)s ] %(message)s"
coloredlogs.DEFAULT_FIELD_STYLES = {'asctime': {'color': 100}, 'lineno': {'color': 'magenta'}, 'levelname': {'bold': True, 'color': 'black'}, 'filename': {'color': 25}, 'name': {'color': 'blue'}, 'funcname': {'color': 'cyan'}}
coloredlogs.DEFAULT_LEVEL_STYLES = {'critical': {'bold': True, 'color': 'red'}, 'debug': {'bold': True, 'color': 'black'}, 'error': {'color': 'red'}, 'info': {'color': 'green'}, 'notice': {'color': 'magenta'}, 'spam': {'color': 'green', 'faint': True}, 'success': {'bold': True, 'color': 'green'}, 'verbose': {'color': 'blue'}, 'warning': {'color': 'yellow'}}

logging.setLoggerClass(MyLogger)
baselogger: MyLogger = logging.getLogger("main")
baselogger.addLevel("Event", 25, {"color": "white"})
baselogger.addLevel("Highlight", 51, {"color": "magenta", "bold": True})


def init(args=None):
    """
    Initializes the logger

    Usage:

    from utils import mylogger

    baselogger = mylogger.init(args)

    client.logger = baselogger #optional

    :param args: argparse arguments
    :return: the root logger
    """
    if args and args.logfile: #if you need a text file
        FORMAT = "[{asctime}][{name}][{filename}][{lineno:4}][{funcName}][{levelname}] {message}"
        formatter = logging.Formatter(FORMAT, style="{")  # this is for default logger
        filename = f"./logs/bot_log_{datetime.now().strftime('%m-%d-%H-%M-%S')}.txt"
        makedirs(r"./logs", exist_ok=True)
        with open(filename, "w", encoding="utf-8") as _:
            pass
        fl = WatchedFileHandler(filename, encoding="utf-8") #not for windows but if i ever switch to linux
        fl.setFormatter(formatter)
        fl.setLevel(logging.DEBUG)
        fl.addFilter(lambda rec: rec.levelno == 25)
        baselogger.addHandler(fl)

    baselogger.setLevel(logging.DEBUG)  # base is debug, so the file handler could catch debug msgs too
    if args and args.debug:
        coloredlogs.install(level=logging.DEBUG, logger=baselogger, fmt=fmt)
    else:
        coloredlogs.install(level=logging.INFO, logger=baselogger, fmt=fmt)
    return baselogger
