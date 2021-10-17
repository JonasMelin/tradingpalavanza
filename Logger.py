import enum, datetime, pytz, sys

tradeRegisterPath = "/logs/tradingPalRegistertLog.txt"
auditLogPath = "/logs/tradingPalAuditLog.txt"
traceLogPath = "/logs/tradingPalTraceLog.txt"

class LogType(enum.Enum):
    Trace = 1
    Audit = 2
    Register = 3

class Log:

    def __init__(self):
        self.errorMessgeFilePrinted = False
        self.lastHash = 0

    def log(self, logType: LogType, data):

        if logType == LogType.Register:
            typeChar = 'R'
        elif logType == logType.Audit:
            typeChar = 'A'
        else:
            typeChar = 'T'

        textNoDate = f"({typeChar}) {str(data)}"
        newHash = hash(textNoDate)
        text = f"{datetime.datetime.now(pytz.timezone('Europe/Stockholm'))} - {textNoDate}"
        if newHash == self.lastHash and logType == logType.Trace: # If trace log, only log one if log is identical to prior
            return

        print(text)
        sys.stdout.flush()

        if logType == LogType.Register:
            self._logToFile(tradeRegisterPath, text)
            self._logToFile(auditLogPath, text)
            self._logToFile(traceLogPath, text)
        if logType == LogType.Audit:
            self._logToFile(auditLogPath, text)
            self._logToFile(traceLogPath, text)
        if logType == LogType.Trace:
            self._logToFile(traceLogPath, text)

        self.lastHash = newHash

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
    l.log(LogType.Audit, "auditLog") # All audits shall appear
    l.log(LogType.Audit, "auditLog")
    l.log(LogType.Trace, "traceLog") # Only one trace should appear
    l.log(LogType.Trace, "traceLog")
    l.log(LogType.Register, {"column": "data"}) # All registers shall appear
    l.log(LogType.Register, {"column": "data"})
