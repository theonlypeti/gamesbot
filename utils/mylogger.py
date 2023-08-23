import logging
from datetime import datetime
from os import makedirs
import coloredlogs

baselogger = logging.getLogger("Base")

# formatting the colorlogger
fmt = "[ %(asctime)s %(filename)s %(lineno)d %(funcName)s %(levelname)s ] %(message)s"
coloredlogs.DEFAULT_FIELD_STYLES = {'asctime': {'color': 'green'}, 'lineno': {'color': 'magenta'},
                                    'levelname': {'bold': True, 'color': 'black'}, 'filename': {'color': 'blue'},
                                    'funcname': {'color': 'cyan'}}
coloredlogs.DEFAULT_LEVEL_STYLES = {'critical': {'bold': True, 'color': 'red'},
                                    'debug': {'bold': True, 'color': 'black'}, 'error': {'color': 'red'},
                                    'info': {'color': 'green'}, 'notice': {'color': 'magenta'},
                                    'spam': {'color': 'green', 'faint': True},
                                    'success': {'bold': True, 'color': 'green'}, 'verbose': {'color': 'blue'},
                                    'warning': {'color': 'yellow'}}


def init(args):
    if args.logfile:  # if you need a text file
        FORMAT = "[{asctime}][{filename}][{lineno:4}][{funcName}][{levelname}] {message}"
        formatter = logging.Formatter(FORMAT, style="{")  # this is for default logger
        filename = f"./logs/bot_log_{datetime.now().strftime('%m-%d-%H-%M-%S')}.txt"
        makedirs(r"./logs", exist_ok=True)
        with open(filename, "w") as f:
            pass
        fl = logging.FileHandler(filename)
        fl.setFormatter(formatter)
        fl.setLevel(logging.DEBUG)
        # fl.addFilter(lambda rec: rec.levelno <= 10) #if u only wanna filter debugs
        baselogger.addHandler(fl)

    baselogger.setLevel(logging.DEBUG)  # base is debug, so the file handler could catch debug msgs too
    if args.debug:
        coloredlogs.install(level=logging.DEBUG, logger=baselogger, fmt=fmt)
    else:
        coloredlogs.install(level=logging.INFO, logger=baselogger, fmt=fmt)
