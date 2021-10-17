import enum, datetime, pytz, sys

tradeRegisterPath = "/logs/tradingPalRegistertLog.txt"
auditLogPath = "/logs/tradingPalAuditLog.txt"
traceLogPath = "/logs/traingPalTraceLog.txt"

class LogType(enum.Enum):
    Trace = 1
    Audit = 2
    Register = 3

class Log:

    def __init__(self):
        self.errorMessgeFilePrinted = False

    def log(self, logType: LogType, data):

        typeChar = '?'
        text = str(data)

        if logType == LogType.Register:
            typeChar = 'R'
            self._logToFile(tradeRegisterPath, text)
            self._logToFile(auditLogPath, text)
            self._logToFile(traceLogPath, text)
        if logType == LogType.Audit:
            typeChar = 'A'
            self._logToFile(auditLogPath, text)
            self._logToFile(traceLogPath, text)
        if logType == LogType.Trace:
            typeChar = 'T'
            self._logToFile(traceLogPath, text)

        print(f"{datetime.datetime.now(pytz.timezone('Europe/Stockholm'))} - ({typeChar}) {text}")
        sys.stdout.flush()

    def _logToFile(self, path: str, text: str):
        try:
            with open(path, "a") as file_object:
                file_object.write(text + "\n")
        except Exception as ex:
            if not self.errorMessgeFilePrinted:
                print(f"Could not log to {path}, {ex}")
                sys.stdout.flush()
                self.errorMessgeFilePrinted = True

if __name__ == "__main__":
    l = Log()
    l.log(LogType.Audit, "auditLog")
    l.log(LogType.Trace, "traceLog")
    l.log(LogType.Register, {"column": "data"})
