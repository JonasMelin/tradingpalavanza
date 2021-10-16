import enum, datetime, pytz, sys

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

        if logType == LogType.Register:
            self._registerToMongo(data)
        else:
            self._logText(logType, data)

    def _logText(self, logType: LogType, text: str):

        print(f"{datetime.datetime.now(pytz.timezone('Europe/Stockholm'))} - {text}")
        sys.stdout.flush()

        if logType == LogType.Audit:
            self._logToFile(auditLogPath, text)
            self._logToFile(traceLogPath, text)
        if logType == LogType.Trace:
            self._logToFile(traceLogPath, text)

    def _logToFile(self, path: str, text: str):
        try:
            with open(path, "a") as file_object:
                file_object.write(text + "\n")
        except Exception as ex:
            if not self.errorMessgeFilePrinted:
                print(f"Could not log to {path}, {ex}")
                sys.stdout.flush()
                self.errorMessgeFilePrinted = True


    def _registerToMongo(self, data: map):

        self._logText(LogType.Audit, "Register to Db: " + str(data))


if __name__ == "__main__":
    l = Log()
    l.log(LogType.Audit, "auditLog")
    l.log(LogType.Trace, "traceLog")
    l.log(LogType.Register, {"column": "data"})
